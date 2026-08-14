"""Unit tests for FTS5 full-text search and multi-tiered search ranking."""

import tempfile
import unittest
from pathlib import Path

from findotype.models.search import SearchMatchType
from findotype.services.ontology_service import Findotype


class TestSearch(unittest.TestCase):
    """Test suite for search engine."""

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

    def test_search_by_exact_id(self):
        results = self.engine.search_diseases("DOID:0001816")
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0].id, "DOID:0001816")
        self.assertEqual(results[0].match_type, SearchMatchType.EXACT_ID)

    def test_search_by_numeric_id(self):
        results = self.engine.search_diseases("399")
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0].id, "DOID:399")

    def test_search_by_alt_id(self):
        results = self.engine.search_diseases("DOID:267")
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0].id, "DOID:0001816")
        self.assertEqual(results[0].match_type, SearchMatchType.ALT_ID)

    def test_search_by_exact_name(self):
        results = self.engine.search_diseases("angiosarcoma")
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0].id, "DOID:0001816")
        self.assertEqual(results[0].match_type, SearchMatchType.EXACT_NAME)

    def test_search_by_prefix_name(self):
        results = self.engine.search_diseases("angio")
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0].id, "DOID:0001816")
        self.assertIn(results[0].match_type, (SearchMatchType.PREFIX_NAME, SearchMatchType.FTS_RANKED))

    def test_search_by_synonym(self):
        # "hemangiosarcoma" is a synonym for DOID:0001816
        results = self.engine.search_diseases("hemangiosarcoma")
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0].id, "DOID:0001816")
        self.assertEqual(results[0].match_type, SearchMatchType.SYNONYM)

    def test_search_by_definition_term(self):
        # "Mycobacterium" is in definition of tuberculosis (DOID:399)
        results = self.engine.search_diseases("Mycobacterium")
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0].id, "DOID:399")
        self.assertEqual(results[0].match_type, SearchMatchType.FTS_RANKED)

    def test_empty_search(self):
        results = self.engine.search_diseases("")
        self.assertEqual(results, [])


if __name__ == "__main__":
    unittest.main()
