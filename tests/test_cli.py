"""Unit tests for the Findotype CLI interface."""

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from findotype.cli.main import main


class TestCLI(unittest.TestCase):
    """Test suite for command line tools."""

    @classmethod
    def setUpClass(cls):
        cls.fixture_path = str(Path(__file__).parent / "fixtures" / "sample_doid.json")
        cls.temp_db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        cls.db_path = cls.temp_db_file.name

    @classmethod
    def tearDownClass(cls):
        p = Path(cls.db_path)
        if p.exists():
            p.unlink()
            for extra in [f"{p}-wal", f"{p}-shm"]:
                if Path(extra).exists():
                    Path(extra).unlink()

    def test_cli_validate(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            ret = main(["validate", self.fixture_path, "--json"])
        self.assertEqual(ret, 0)
        data = json.loads(buf.getvalue())
        self.assertTrue(data["valid"])

    def test_cli_import(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            ret = main(["import", self.fixture_path, "--db", self.db_path, "--json"])
        self.assertEqual(ret, 0)
        data = json.loads(buf.getvalue())
        self.assertEqual(data["status"], "success")
        self.assertGreater(data["entities_count"], 0)

    def test_cli_stats(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            ret = main(["stats", "--db", self.db_path, "--json"])
        self.assertEqual(ret, 0)
        data = json.loads(buf.getvalue())
        self.assertEqual(data["provenance"]["dataset_name"], "Disease Ontology")
        self.assertGreater(data["counts"]["diseases"], 0)

    def test_cli_search(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            ret = main(["search", "tuberculosis", "--db", self.db_path, "--json"])
        self.assertEqual(ret, 0)
        data = json.loads(buf.getvalue())
        self.assertGreater(len(data), 0)
        self.assertEqual(data[0]["id"], "DOID:399")

    def test_cli_inspect(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            ret = main(["inspect", "DOID:0001816", "--db", self.db_path, "--json"])
        self.assertEqual(ret, 0)
        data = json.loads(buf.getvalue())
        self.assertEqual(data["id"], "DOID:0001816")
        self.assertEqual(data["name"], "angiosarcoma")
        self.assertGreater(len(data["synonyms"]), 0)
        self.assertGreater(len(data["parents"]), 0)


if __name__ == "__main__":
    unittest.main()
