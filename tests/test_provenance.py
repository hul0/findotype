"""Unit tests for data provenance, metadata tracking, and metrics."""

import tempfile
import unittest
from pathlib import Path

from findotype.services.ontology_service import Findotype


class TestProvenance(unittest.TestCase):
    """Test suite for provenance and metadata."""

    @classmethod
    def setUpClass(cls):
        cls.fixture_path = Path(__file__).parent / "fixtures" / "sample_doid.json"
        cls.temp_db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        cls.db_path = Path(cls.temp_db_file.name)

        cls.engine = Findotype(db_path=cls.db_path)
        cls.engine.import_doid(cls.fixture_path, include_obsolete=False)

    @classmethod
    def tearDownClass(cls):
        cls.engine.close()
        if cls.db_path.exists():
            cls.db_path.unlink()
            for extra in [f"{cls.db_path}-wal", f"{cls.db_path}-shm"]:
                if Path(extra).exists():
                    Path(extra).unlink()

    def test_provenance_record(self):
        prov = self.engine.get_provenance()
        self.assertIsNotNone(prov)
        self.assertEqual(prov.dataset_name, "Disease Ontology")
        self.assertEqual(prov.dataset_version, "2026-07-31")
        self.assertEqual(len(prov.source_sha256), 64)  # Valid SHA-256
        self.assertEqual(prov.schema_version, "1.0.0")
        self.assertIn("T", prov.imported_at)  # ISO timestamp
        self.assertGreater(prov.stats["entities_count"], 0)

    def test_metadata_record(self):
        meta = self.engine.get_metadata()
        self.assertEqual(meta.title, "Human Disease Ontology Test")
        self.assertIn("sample test graph", meta.description)
        self.assertEqual(meta.license, "https://creativecommons.org/publicdomain/zero/1.0/")
        self.assertEqual(meta.root_term, "DOID:4")

    def test_database_stats(self):
        stats = self.engine.get_stats()
        self.assertGreater(stats.total_entities, 0)
        self.assertEqual(stats.total_diseases, 5)
        self.assertGreater(stats.total_synonyms, 0)
        self.assertGreater(stats.total_definitions, 0)
        self.assertGreater(stats.total_xrefs, 0)
        self.assertGreater(stats.total_relationships, 0)
        self.assertIn("DOID", stats.entity_namespaces)
        self.assertIn("CHEBI", stats.entity_namespaces)
        self.assertIn("is_a", stats.top_predicates)


if __name__ == "__main__":
    unittest.main()
