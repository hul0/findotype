"""Unit tests for disease repository queries and graph traversal."""

import tempfile
import unittest
from pathlib import Path

from findotype.services.ontology_service import Findotype


class TestRepository(unittest.TestCase):
    """Test suite for repository queries."""

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

    def test_get_disease_by_id(self):
        d = self.engine.get_disease("DOID:0001816")
        self.assertIsNotNone(d)
        self.assertEqual(d.id, "DOID:0001816")
        self.assertEqual(d.name, "angiosarcoma")
        self.assertIsNotNone(d.definition)
        self.assertIn("vascular cancer", d.definition.definition)
        self.assertEqual(len(d.synonyms), 2)
        self.assertIn("hemangiosarcoma", [s.synonym for s in d.synonyms])
        self.assertIn("DO_cancer_slim", [s.name for s in d.subsets])
        self.assertIn("DOID:267", d.alt_ids)

    def test_alt_id_resolution(self):
        """Test resolving an old/merged DOID to its canonical term."""
        d = self.engine.get_disease("DOID:267")
        self.assertIsNotNone(d)
        self.assertEqual(d.id, "DOID:0001816")
        self.assertEqual(d.name, "angiosarcoma")

    def test_get_disease_by_name(self):
        d = self.engine.get_disease_by_name("angiosarcoma")
        self.assertIsNotNone(d)
        self.assertEqual(d.id, "DOID:0001816")

        d_case = self.engine.get_disease_by_name("TuBerCuLoSiS")
        self.assertIsNotNone(d_case)
        self.assertEqual(d_case.id, "DOID:399")

    def test_get_definition(self):
        df = self.engine.get_definition("DOID:399")
        self.assertIsNotNone(df)
        self.assertIn("Mycobacterium tuberculosis", df.definition)
        self.assertGreater(len(df.sources), 0)

    def test_get_synonyms(self):
        syns = self.engine.get_synonyms("DOID:399")
        syn_names = [s.synonym for s in syns]
        self.assertIn("TB", syn_names)
        self.assertIn("consumption", syn_names)

    def test_get_cross_references(self):
        xrefs = self.engine.get_cross_references("DOID:0001816")
        self.assertGreater(len(xrefs), 0)
        dbs = {x.db for x in xrefs}
        self.assertIn("MESH", dbs)
        self.assertIn("NCI", dbs)

        mesh_only = self.engine.get_cross_references("DOID:0001816", db="MESH")
        self.assertEqual(len(mesh_only), 1)
        self.assertEqual(mesh_only[0].accession, "D006394")

    def test_parents_and_children(self):
        # DOID:0001816 (angiosarcoma) is_a DOID:175 (vascular cancer)
        parents = self.engine.get_parents("DOID:0001816")
        self.assertEqual(len(parents), 1)
        self.assertEqual(parents[0].id, "DOID:175")
        self.assertEqual(parents[0].name, "vascular cancer")

        # DOID:175 should have child DOID:0001816
        children = self.engine.get_children("DOID:175")
        self.assertEqual(len(children), 1)
        self.assertEqual(children[0].id, "DOID:0001816")

    def test_recursive_ancestors_and_descendants(self):
        # Hierarchy: DOID:0001816 -> DOID:175 -> DOID:162 -> DOID:4
        ancestors = self.engine.get_ancestors("DOID:0001816")
        anc_ids = [a.id for a in ancestors]
        self.assertEqual(anc_ids, ["DOID:175", "DOID:162", "DOID:4"])
        self.assertEqual(ancestors[0].depth, 1)
        self.assertEqual(ancestors[1].depth, 2)
        self.assertEqual(ancestors[2].depth, 3)

        # Descendants of DOID:4 (root disease)
        descendants = self.engine.get_descendants("DOID:4")
        desc_ids = [d.id for d in descendants]
        self.assertIn("DOID:162", desc_ids)
        self.assertIn("DOID:175", desc_ids)
        self.assertIn("DOID:0001816", desc_ids)
        self.assertIn("DOID:399", desc_ids)

    def test_relationships(self):
        # Outgoing relationship to CHEBI:15365
        rels = self.engine.get_relationships("DOID:0001816")
        self.assertGreater(len(rels), 0)
        rel_labels = [r.predicate_label for r in rels]
        self.assertIn("is_a", rel_labels)
        self.assertIn("has substance added", rel_labels)


if __name__ == "__main__":
    unittest.main()
