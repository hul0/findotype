import json
import logging
import threading
import urllib.parse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional

from findotype.config import DEFAULT_DB_PATH
from findotype.server.openapi import get_openapi_spec
from findotype.services.ontology_service import Findotype

logger = logging.getLogger("findotype.server")
_thread_local = threading.local()

# Swagger UI HTML Template referencing standard CDN distribution
SWAGGER_UI_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Findotype REST API — Swagger UI</title>
  <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css">
  <style>
    body { margin: 0; background: #fafafa; }
    .swagger-ui .topbar { background-color: #09090b; }
    .swagger-ui .topbar .download-url-wrapper .select-label select { border: 1px solid #27272a; }
  </style>
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
  <script>
    window.onload = function() {
      window.ui = SwaggerUIBundle({
        url: "/openapi.json",
        dom_id: '#swagger-ui',
        deepLinking: true,
        presets: [
          SwaggerUIBundle.presets.apis,
          SwaggerUIBundle.SwaggerUIStandalonePreset
        ],
        layout: "BaseLayout"
      });
    };
  </script>
</body>
</html>
"""


class FindotypeRequestHandler(BaseHTTPRequestHandler):
    """Handles HTTP requests for Web UI, OpenAPI documentation, and REST endpoints."""

    db_path: Path = DEFAULT_DB_PATH

    @classmethod
    def get_engine(cls) -> Findotype:
        """Get or initialize the thread-local Findotype engine instance."""
        if not hasattr(_thread_local, "engine") or _thread_local.engine is None:
            _thread_local.engine = Findotype(db_path=cls.db_path)
        return _thread_local.engine

    def _send_json(self, data: Any, status: int = HTTPStatus.OK) -> None:
        """Send JSON response with proper headers."""
        payload = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(payload)

    def _send_html(self, html: str, status: int = HTTPStatus.OK) -> None:
        """Send HTML response."""
        payload = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_OPTIONS(self) -> None:
        """Handle CORS pre-flight requests."""
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        """Handle GET requests."""
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path.rstrip("/")
        query_params = urllib.parse.parse_qs(parsed_url.query)

        # 1. Web Application UI
        if path in ("", "/"):
            template_path = Path(__file__).parent / "templates" / "index.html"
            if template_path.exists():
                with open(template_path, "r", encoding="utf-8") as f:
                    html_content = f.read()
                self._send_html(html_content)
            else:
                self._send_html("<h1>Findotype Server Running</h1>")
            return

        # 2. Swagger UI & OpenAPI spec
        if path in ("/docs", "/swagger"):
            self._send_html(SWAGGER_UI_HTML)
            return

        if path == "/openapi.json":
            self._send_json(get_openapi_spec())
            return

        engine = self.get_engine()

        # 3. REST API Endpoints
        if path == "/api/stats":
            stats = engine.get_stats()
            kb_meta = engine.get_knowledge_base_metadata()
            datasets = engine.get_datasets()
            data = {
                "knowledge_base": {
                    "name": kb_meta.name,
                    "schema_version": kb_meta.schema_version,
                },
                "datasets": [
                    {
                        "name": d.dataset_name,
                        "version": d.dataset_version,
                        "release_date": d.release_date,
                        "license": d.license,
                        "root_term": d.root_term,
                        "source_uri": d.source_uri,
                        "source_sha256": d.source_sha256,
                        "imported_at": d.imported_at,
                    }
                    for d in datasets
                ],
                "counts": {
                    "entities": stats.total_entities,
                    "diseases": stats.total_diseases,
                    "synonyms": stats.total_synonyms,
                    "definitions": stats.total_definitions,
                    "cross_references": stats.total_xrefs,
                    "relationships": stats.total_relationships,
                    "subsets": stats.total_subsets,
                    "alt_ids": stats.total_alt_ids,
                },
                "namespaces": stats.entity_namespaces,
                "top_predicates": stats.top_predicates,
                "top_xref_databases": stats.top_xref_databases,
            }
            self._send_json(data)
            return

        if path == "/api/search":
            q = query_params.get("q", [""])[0].strip()
            if not q:
                self._send_json({"error": "Missing query parameter 'q'"}, status=HTTPStatus.BAD_REQUEST)
                return
            limit = int(query_params.get("limit", [20])[0])
            results = engine.search_diseases(q, limit=limit)
            data = [
                {
                    "id": r.id,
                    "name": r.name,
                    "match_type": r.match_type.value,
                    "matched_text": r.matched_text,
                    "rank_score": r.rank_score,
                    "definition": r.definition,
                }
                for r in results
            ]
            self._send_json(data)
            return

        if path == "/api/match":
            symptoms = query_params.get("symptoms", [""])[0].strip()
            limit = int(query_params.get("limit", [10])[0])
            extracted = engine.extract_symptoms(symptoms)
            results = engine.match_phenotypes(symptoms, limit=limit)
            disclaimer = (
                "Phenotype overlap scores indicate ontology symptom concordance, "
                "NOT clinical diagnostic probability or medical diagnosis. "
                "Consult a qualified healthcare professional."
            )
            data = {
                "query": symptoms,
                "disclaimer": disclaimer,
                "extracted_phenotypes": [
                    {
                        "term_id": s.matched_term_id,
                        "term_name": s.matched_term_name,
                        "raw_text": s.raw_query_text,
                        "information_content": s.information_content,
                    }
                    for s in extracted
                ],
                "candidate_diseases": [
                    {
                        "disease_id": r.disease_id,
                        "disease_name": r.disease_name,
                        "score": r.score,
                        "query_coverage_pct": r.query_coverage_pct,
                        "matched_count": r.matched_count,
                        "total_query_count": r.total_query_count,
                        "matched_phenotypes": [
                            {"id": p.id, "name": p.name, "ic": p.ic, "source": p.source}
                            for p in r.matched_phenotypes
                        ],
                        "unmatched_phenotypes": [
                            {"id": p.id, "name": p.name, "ic": p.ic}
                            for p in r.unmatched_phenotypes
                        ],
                        "definition": r.disease_definition,
                    }
                    for r in results
                ],
            }
            self._send_json(data)
            return

        # /api/diseases/{id} and subpaths
        if path.startswith("/api/diseases/"):
            subpath = path[len("/api/diseases/"):]
            parts = subpath.split("/")
            disease_id = urllib.parse.unquote(parts[0])

            if len(parts) == 1:
                # Full disease details
                disease = engine.get_disease(disease_id)
                if not disease:
                    self._send_json({"error": f"Disease not found: {disease_id}"}, status=HTTPStatus.NOT_FOUND)
                    return

                parents = engine.get_parents(disease.id)
                children = engine.get_children(disease.id)
                relationships = engine.get_relationships(disease.id)

                data = {
                    "id": disease.id,
                    "name": disease.name,
                    "uri": disease.uri,
                    "namespace": disease.namespace,
                    "is_obsolete": disease.is_obsolete,
                    "definition": {
                        "text": disease.definition.definition if disease.definition else None,
                        "sources": disease.definition.sources if disease.definition else [],
                    },
                    "synonyms": [
                        {"synonym": s.synonym, "scope": s.scope, "type": s.synonym_type}
                        for s in disease.synonyms
                    ],
                    "cross_references": [
                        {"db": x.db, "accession": x.accession, "full": x.full_reference}
                        for x in disease.cross_references
                    ],
                    "subsets": [s.name for s in disease.subsets],
                    "parents": [
                        {"id": p.id, "name": p.name, "predicate": p.predicate_id, "predicate_label": p.predicate_label, "depth": p.depth}
                        for p in parents
                    ],
                    "children": [
                        {"id": c.id, "name": c.name, "predicate": c.predicate_id, "predicate_label": c.predicate_label, "depth": c.depth}
                        for c in children
                    ],
                    "relationships": [
                        {
                            "subject_id": r.subject_id,
                            "subject_name": r.subject_name,
                            "predicate_id": r.predicate_id,
                            "predicate_label": r.predicate_label,
                            "object_id": r.object_id,
                            "object_name": r.object_name,
                        }
                        for r in relationships
                    ],
                }
                self._send_json(data)
                return

            if len(parts) == 2:
                action = parts[1]
                if action == "parents":
                    nodes = engine.get_parents(disease_id)
                elif action == "children":
                    nodes = engine.get_children(disease_id)
                elif action == "ancestors":
                    max_depth = int(query_params.get("max_depth", [50])[0])
                    nodes = engine.get_ancestors(disease_id, max_depth=max_depth)
                elif action == "descendants":
                    max_depth = int(query_params.get("max_depth", [50])[0])
                    nodes = engine.get_descendants(disease_id, max_depth=max_depth)
                elif action == "relationships":
                    rels = engine.get_relationships(disease_id)
                    self._send_json([
                        {
                            "subject_id": r.subject_id,
                            "subject_name": r.subject_name,
                            "predicate_id": r.predicate_id,
                            "predicate_label": r.predicate_label,
                            "object_id": r.object_id,
                            "object_name": r.object_name,
                        }
                        for r in rels
                    ])
                    return
                else:
                    self._send_json({"error": f"Unknown endpoint action: {action}"}, status=HTTPStatus.NOT_FOUND)
                    return

                self._send_json([
                    {
                        "id": n.id,
                        "name": n.name,
                        "predicate": n.predicate_id,
                        "predicate_label": n.predicate_label,
                        "depth": n.depth,
                    }
                    for n in nodes
                ])
                return

        # 404 Not Found fallback
        self._send_json({"error": f"Path not found: {path}"}, status=HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        """Handle POST requests (e.g. /api/match with JSON body)."""
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path.rstrip("/")

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
        try:
            payload = json.loads(body) if body else {}
        except Exception:
            self._send_json({"error": "Invalid JSON body"}, status=HTTPStatus.BAD_REQUEST)
            return

        engine = self.get_engine()

        if path == "/api/match":
            symptoms = payload.get("symptoms", "")
            limit = int(payload.get("limit", 10))
            if not symptoms:
                self._send_json({"error": "Missing 'symptoms' in JSON body"}, status=HTTPStatus.BAD_REQUEST)
                return

            extracted = engine.extract_symptoms(symptoms)
            results = engine.match_phenotypes(symptoms, limit=limit)
            disclaimer = (
                "Phenotype overlap scores indicate ontology symptom concordance, "
                "NOT clinical diagnostic probability or medical diagnosis. "
                "Consult a qualified healthcare professional."
            )
            data = {
                "query": symptoms if isinstance(symptoms, str) else ", ".join(symptoms),
                "disclaimer": disclaimer,
                "extracted_phenotypes": [
                    {
                        "term_id": s.matched_term_id,
                        "term_name": s.matched_term_name,
                        "raw_text": s.raw_query_text,
                        "information_content": s.information_content,
                    }
                    for s in extracted
                ],
                "candidate_diseases": [
                    {
                        "disease_id": r.disease_id,
                        "disease_name": r.disease_name,
                        "score": r.score,
                        "query_coverage_pct": r.query_coverage_pct,
                        "matched_count": r.matched_count,
                        "total_query_count": r.total_query_count,
                        "matched_phenotypes": [
                            {"id": p.id, "name": p.name, "ic": p.ic, "source": p.source}
                            for p in r.matched_phenotypes
                        ],
                        "unmatched_phenotypes": [
                            {"id": p.id, "name": p.name, "ic": p.ic}
                            for p in r.unmatched_phenotypes
                        ],
                        "definition": r.disease_definition,
                    }
                    for r in results
                ],
            }
            self._send_json(data)
            return

        self._send_json({"error": f"Path not found: {path}"}, status=HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args: Any) -> None:
        """Custom clean logging format."""
        logger.debug("%s - - [%s] %s", self.address_string(), self.log_date_time_string(), format % args)


def run_server(
    host: str = "127.0.0.1",
    port: int = 8000,
    db_path: Path = DEFAULT_DB_PATH,
) -> None:
    """Start the Findotype HTTP server."""
    FindotypeRequestHandler.db_path = db_path
    server_address = (host, port)
    ThreadingHTTPServer.allow_reuse_address = True
    httpd = ThreadingHTTPServer(server_address, FindotypeRequestHandler)
    print(f"\n{'='*70}")
    print(f"Findotype Server Started")
    print(f"{'='*70}")
    print(f"Web Interface:   http://{host}:{port}/")
    print(f"Swagger UI Docs: http://{host}:{port}/docs")
    print(f"OpenAPI Schema:  http://{host}:{port}/openapi.json")
    print(f"Database:        {db_path.resolve()}")
    print(f"{'='*70}")
    print("Press Ctrl+C to terminate server.\n")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Findotype server...")
    finally:
        httpd.server_close()
