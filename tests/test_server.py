"""Unit and integration tests for the Findotype HTTP server, OpenAPI schema, and Swagger UI."""

import json
import tempfile
import threading
import time
import unittest
import urllib.parse
import urllib.request
from http import HTTPStatus
from http.server import ThreadingHTTPServer
from pathlib import Path

from findotype.server.app import FindotypeRequestHandler
from findotype.server.openapi import get_openapi_spec
from findotype.services.ontology_service import Findotype


class TestServer(unittest.TestCase):
    """Test suite for HTTP server, OpenAPI, and REST endpoints."""

    @classmethod
    def setUpClass(cls):
        cls.fixture_path = Path(__file__).parent / "fixtures" / "sample_doid.json"
        cls.temp_db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        cls.db_path = Path(cls.temp_db_file.name)

        # Ingest test fixture
        engine = Findotype(db_path=cls.db_path)
        engine.import_doid(cls.fixture_path, include_obsolete=False)
        engine.close()

        # Start server in background thread on ephemeral port
        FindotypeRequestHandler.db_path = cls.db_path
        FindotypeRequestHandler._engine = None
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), FindotypeRequestHandler)
        cls.port = cls.httpd.server_address[1]
        cls.base_url = f"http://127.0.0.1:{cls.port}"

        cls.server_thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.server_thread.start()
        time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        if cls.db_path.exists():
            cls.db_path.unlink()
            for extra in [f"{cls.db_path}-wal", f"{cls.db_path}-shm"]:
                if Path(extra).exists():
                    Path(extra).unlink()

    def _get(self, path: str):
        url = f"{self.base_url}{path}"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as resp:
            status = resp.status
            content_type = resp.headers.get("Content-Type", "")
            body = resp.read().decode("utf-8")
            return status, content_type, body

    def _post(self, path: str, json_data: dict):
        url = f"{self.base_url}{path}"
        payload = json.dumps(json_data).encode("utf-8")
        req = urllib.request.Request(
            url, data=payload, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as resp:
            status = resp.status
            content_type = resp.headers.get("Content-Type", "")
            body = resp.read().decode("utf-8")
            return status, content_type, body

    def test_openapi_spec(self):
        spec = get_openapi_spec()
        self.assertEqual(spec["openapi"], "3.0.3")
        self.assertIn("/api/search", spec["paths"])
        self.assertIn("/api/match", spec["paths"])
        self.assertIn("/api/stats", spec["paths"])
        self.assertIn("/api/diseases/{id}", spec["paths"])

    def test_get_openapi_endpoint(self):
        status, ctype, body = self._get("/openapi.json")
        self.assertEqual(status, HTTPStatus.OK)
        self.assertIn("application/json", ctype)
        data = json.loads(body)
        self.assertEqual(data["info"]["title"], "Findotype API")

    def test_get_swagger_ui(self):
        status, ctype, body = self._get("/docs")
        self.assertEqual(status, HTTPStatus.OK)
        self.assertIn("text/html", ctype)
        self.assertIn("SwaggerUIBundle", body)

    def test_get_web_ui(self):
        status, ctype, body = self._get("/")
        self.assertEqual(status, HTTPStatus.OK)
        self.assertIn("text/html", ctype)
        self.assertIn("Findotype", body)
        self.assertIn("Clinical Symptom & Phenotype Explorer", body)

    def test_api_stats(self):
        status, ctype, body = self._get("/api/stats")
        self.assertEqual(status, HTTPStatus.OK)
        data = json.loads(body)
        self.assertEqual(data["knowledge_base"]["name"], "Findotype Biomedical Knowledge Base")
        self.assertGreater(data["counts"]["entities"], 0)

    def test_api_search(self):
        status, ctype, body = self._get("/api/search?q=tuberculosis")
        self.assertEqual(status, HTTPStatus.OK)
        data = json.loads(body)
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)
        self.assertEqual(data[0]["id"], "DOID:399")

    def test_api_disease_detail(self):
        status, ctype, body = self._get("/api/diseases/DOID:0001816")
        self.assertEqual(status, HTTPStatus.OK)
        data = json.loads(body)
        self.assertEqual(data["id"], "DOID:0001816")
        self.assertEqual(data["name"], "angiosarcoma")
        self.assertIsInstance(data["synonyms"], list)
        self.assertIsInstance(data["cross_references"], list)

    def test_api_hierarchy_endpoints(self):
        status, _, body = self._get("/api/diseases/DOID:0001816/parents")
        self.assertEqual(status, HTTPStatus.OK)
        parents = json.loads(body)
        self.assertIsInstance(parents, list)

        status, _, body = self._get("/api/diseases/DOID:0001816/ancestors")
        self.assertEqual(status, HTTPStatus.OK)
        ancestors = json.loads(body)
        self.assertIsInstance(ancestors, list)

    def test_api_match_get_and_post(self):
        # GET match
        status, _, body = self._get("/api/match?symptoms=fever")
        self.assertEqual(status, HTTPStatus.OK)
        data = json.loads(body)
        self.assertIn("extracted_phenotypes", data)
        self.assertIn("candidate_diseases", data)

        # POST match
        status, _, body = self._post("/api/match", {"symptoms": "fever, cough", "limit": 5})
        self.assertEqual(status, HTTPStatus.OK)
        data = json.loads(body)
        self.assertIn("extracted_phenotypes", data)
        self.assertIn("candidate_diseases", data)


if __name__ == "__main__":
    unittest.main()
