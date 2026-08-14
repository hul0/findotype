"""Unit tests for ontology data normalization logic."""

import unittest
from findotype.ontology.normalizer import (
    normalize_synonym_scope,
    parse_alt_ids,
    parse_cross_reference,
    parse_definition,
    parse_subsets,
    parse_synonyms,
)


class TestNormalizer(unittest.TestCase):
    """Test suite for ontology normalizers."""

    def test_normalize_synonym_scope(self):
        self.assertEqual(normalize_synonym_scope("hasExactSynonym"), "EXACT")
        self.assertEqual(normalize_synonym_scope("hasNarrowSynonym"), "NARROW")
        self.assertEqual(normalize_synonym_scope("hasBroadSynonym"), "BROAD")
        self.assertEqual(normalize_synonym_scope("hasRelatedSynonym"), "RELATED")
        self.assertEqual(normalize_synonym_scope("unknown_predicate"), "RELATED")

    def test_parse_cross_reference(self):
        xref = parse_cross_reference("MESH:D006394")
        self.assertIsNotNone(xref)
        self.assertEqual(xref.db, "MESH")
        self.assertEqual(xref.accession, "D006394")
        self.assertEqual(xref.full_reference, "MESH:D006394")

        xref_dict = parse_cross_reference({"val": "ICD10CM:A15"})
        self.assertIsNotNone(xref_dict)
        self.assertEqual(xref_dict.db, "ICD10CM")
        self.assertEqual(xref_dict.accession, "A15")

        self.assertIsNone(parse_cross_reference(""))
        self.assertIsNone(parse_cross_reference(None))

    def test_parse_definition(self):
        raw_def = {
            "val": "A vascular cancer...",
            "xrefs": ["PUBMED:23327728", "url:https://en.wikipedia.org/wiki/Angiosarcoma"],
        }
        parsed = parse_definition(raw_def)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.definition, "A vascular cancer...")
        self.assertEqual(len(parsed.sources), 2)
        self.assertIn("PUBMED:23327728", parsed.sources)

        # String definition
        parsed_str = parse_definition("Simple string definition")
        self.assertIsNotNone(parsed_str)
        self.assertEqual(parsed_str.definition, "Simple string definition")
        self.assertEqual(parsed_str.sources, [])

        self.assertIsNone(parse_definition(None))
        self.assertIsNone(parse_definition({}))

    def test_parse_synonyms(self):
        raw_syns = [
            {"pred": "hasExactSynonym", "val": "hemangiosarcoma"},
            {"pred": "hasBroadSynonym", "val": "vascular tumor"},
            {"pred": "hasExactSynonym", "val": "hemangiosarcoma"},  # duplicate
        ]
        parsed = parse_synonyms(raw_syns)
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0].synonym, "hemangiosarcoma")
        self.assertEqual(parsed[0].scope, "EXACT")
        self.assertEqual(parsed[1].synonym, "vascular tumor")
        self.assertEqual(parsed[1].scope, "BROAD")

    def test_parse_subsets(self):
        raw_subsets = [
            "http://purl.obolibrary.org/obo/doid#DO_cancer_slim",
            "http://purl.obolibrary.org/obo/doid#NCIthesaurus",
        ]
        subsets = parse_subsets(raw_subsets)
        self.assertEqual(subsets, ["DO_cancer_slim", "NCIthesaurus"])

    def test_parse_alt_ids(self):
        raw_props = [
            {
                "pred": "http://www.geneontology.org/formats/oboInOwl#hasAlternativeId",
                "val": "DOID:267",
            },
            {
                "pred": "http://www.geneontology.org/formats/oboInOwl#hasAlternativeId",
                "val": "DOID:4508",
            },
            {
                "pred": "http://www.geneontology.org/formats/oboInOwl#hasOBONamespace",
                "val": "disease_ontology",
            },
        ]
        alt_ids = parse_alt_ids(raw_props)
        self.assertEqual(alt_ids, ["DOID:267", "DOID:4508"])


if __name__ == "__main__":
    unittest.main()
