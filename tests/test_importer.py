"""Unit tests for Disease Ontology transactional importer."""

import tempfile
import unittest
from pathlib import Path

from findotype.db.connection import get_connection
from findotype.importers.doid import DiseaseOntologyImporter


class TestImporter(unittest.TestCase):
    """Test suite for dataset importer and transactional idempotency."""

    def setUp(self):
        self.fixture_path = Path(__file__).parent / "fixtures" / "sample_doid.json"
        self.temp_db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = Path(self.temp_db_file.name)

    def tearDown(self):
        if self.db_path.exists():
            self.db_path.unlink()
            for extra in [f"{self.db_path}-wal", f"{self.db_path}-shm"]:
                if Path(extra).exists():
                    Path(extra).unlink()

    def test_import_basic(self):
        importer = DiseaseOntologyImporter()
        stats = importer.import_dataset(
            file_path=self.fixture_path,
            db_path=self.db_path,
            include_obsolete=False,
        )

        self.assertGreater(stats.entities_count, 0)
        self.assertEqual(stats.diseases_count, 5)  # 5 DOID nodes (1 obsolete skipped)
        self.assertEqual(stats.obsolete_skipped, 1)
        self.assertGreater(stats.synonyms_count, 0)
        self.assertGreater(stats.xrefs_count, 0)
        self.assertGreater(stats.relationships_count, 0)

        # Check DB contents
        conn = get_connection(self.db_path)
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM entities WHERE id = 'DOID:0001816';")
        self.assertEqual(cur.fetchone()[0], 1)

        # Check definition
        cur.execute("SELECT definition FROM definitions WHERE entity_id = 'DOID:0001816';")
        self.assertIn("vascular cancer", cur.fetchone()[0])

        # Check relationships
        cur.execute(
            """
            SELECT predicate_label, object_id
            FROM relationships
            WHERE subject_id = 'DOID:0001816';
            """
        )
        rels = {row[0]: row[1] for row in cur.fetchall()}
        self.assertIn("is_a", rels)
        self.assertEqual(rels["is_a"], "DOID:175")
        self.assertIn("has substance added", rels)
        self.assertEqual(rels["has substance added"], "CHEBI:15365")

        conn.close()

    def test_import_idempotency(self):
        """Test that importing the same dataset twice produces identical clean counts without duplication."""
        importer = DiseaseOntologyImporter()
        stats1 = importer.import_dataset(
            file_path=self.fixture_path,
            db_path=self.db_path,
            include_obsolete=False,
        )
        stats2 = importer.import_dataset(
            file_path=self.fixture_path,
            db_path=self.db_path,
            include_obsolete=False,
        )

        self.assertEqual(stats1.entities_count, stats2.entities_count)
        self.assertEqual(stats1.synonyms_count, stats2.synonyms_count)
        self.assertEqual(stats1.relationships_count, stats2.relationships_count)

        conn = get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM entities;")
        self.assertEqual(cur.fetchone()[0], stats1.entities_count)
        conn.close()

    def test_import_with_obsolete(self):
        importer = DiseaseOntologyImporter()
        stats = importer.import_dataset(
            file_path=self.fixture_path,
            db_path=self.db_path,
            include_obsolete=True,
        )
        self.assertEqual(stats.obsolete_skipped, 0)
        self.assertEqual(stats.diseases_count, 6)


if __name__ == "__main__":
    unittest.main()
