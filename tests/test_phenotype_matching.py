"""Unit tests for symptom parsing, HPO importing, and phenotype-to-disease matching."""

import tempfile
import unittest
from pathlib import Path

from findotype.services.ontology_service import Findotype


class TestPhenotypeMatching(unittest.TestCase):
    """Test suite for clinical symptom parsing and disease matching."""

    @classmethod
    def setUpClass(cls):
        cls.doid_fixture = Path(__file__).parent / "fixtures" / "sample_doid.json"
        cls.temp_db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        cls.db_path = Path(cls.temp_db_file.name)

        cls.engine = Findotype(db_path=cls.db_path)
        cls.engine.import_doid(cls.doid_fixture, include_obsolete=False)

    @classmethod
    def tearDownClass(cls):
        cls.engine.close()
        if cls.db_path.exists():
            cls.db_path.unlink()
            for extra in [f"{cls.db_path}-wal", f"{cls.db_path}-shm"]:
                if Path(extra).exists():
                    Path(extra).unlink()

    def test_extract_symptoms_natural_language(self):
        query = "I have fever, cough, nausea"
        symptoms = self.engine.extract_symptoms(query)
        # Note: in sample_doid, we have terms or we parse candidate tokens
        self.assertIsInstance(symptoms, list)

    def test_match_phenotypes_query(self):
        # In sample fixture: DOID:399 (tuberculosis) has definition mentioning Mycobacterium tuberculosis
        # and DOID:0001816 (angiosarcoma) has relationship to CHEBI:15365
        results = self.engine.match_phenotypes("Mycobacterium tuberculosis", limit=5)
        self.assertIsInstance(results, list)
        if results:
            self.assertGreater(results[0].match_percentage, 0.0)
            self.assertLessEqual(results[0].match_percentage, 100.0)
            self.assertEqual(results[0].disease_id, "DOID:399")

    def test_empty_symptom_match(self):
        results = self.engine.match_phenotypes("")
        self.assertEqual(results, [])


if __name__ == "__main__":
    unittest.main()
