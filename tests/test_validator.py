"""Unit tests for ontology input validation."""

import json
import tempfile
import unittest
from pathlib import Path

from findotype.importers.validator import OntologyValidator


class TestValidator(unittest.TestCase):
    """Test suite for untrusted JSON validator."""

    def test_nonexistent_file(self):
        res = OntologyValidator.validate_file(Path("non_existent_file.json"))
        self.assertFalse(res["valid"])
        self.assertIn("does not exist", res["errors"][0])

    def test_empty_file(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            p = Path(f.name)
        try:
            res = OntologyValidator.validate_file(p)
            self.assertFalse(res["valid"])
            self.assertIn("empty", res["errors"][0])
        finally:
            p.unlink()

    def test_invalid_json(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{ invalid json content ...")
            p = Path(f.name)
        try:
            res = OntologyValidator.validate_file(p)
            self.assertFalse(res["valid"])
            self.assertIn("Invalid JSON syntax", res["errors"][0])
        finally:
            p.unlink()

    def test_missing_graphs(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"other_key": 123}, f)
            p = Path(f.name)
        try:
            res = OntologyValidator.validate_file(p)
            self.assertFalse(res["valid"])
            self.assertIn("graphs", res["errors"][0])
        finally:
            p.unlink()

    def test_valid_fixture(self):
        fixture_path = Path(__file__).parent / "fixtures" / "sample_doid.json"
        res = OntologyValidator.validate_file(fixture_path)
        self.assertTrue(res["valid"])
        self.assertEqual(len(res["errors"]), 0)
        self.assertGreater(res["total_nodes"], 0)
        self.assertGreater(res["doid_nodes_count"], 0)


if __name__ == "__main__":
    unittest.main()
