"""Unit tests for URI to CURIE conversion and identifier normalization."""

import unittest
from findotype.ontology.curie import (
    curie_to_uri,
    extract_namespace,
    normalize_identifier,
    uri_to_curie,
)


class TestCurieConversion(unittest.TestCase):
    """Test suite for URI/CURIE conversion utilities."""

    def test_uri_to_curie(self):
        self.assertEqual(
            uri_to_curie("http://purl.obolibrary.org/obo/DOID_0001816"),
            "DOID:0001816",
        )
        self.assertEqual(
            uri_to_curie("http://purl.obolibrary.org/obo/CHEBI_15365"),
            "CHEBI:15365",
        )
        self.assertEqual(
            uri_to_curie("http://purl.obolibrary.org/obo/HP_0000118"),
            "HP:0000118",
        )
        self.assertEqual(
            uri_to_curie("is_a"),
            "is_a",
        )
        self.assertEqual(
            uri_to_curie("http://purl.obolibrary.org/obo/doid#DO_cancer_slim"),
            "DO_cancer_slim",
        )
        self.assertEqual(uri_to_curie(""), "")

    def test_curie_to_uri(self):
        self.assertEqual(
            curie_to_uri("DOID:0001816"),
            "http://purl.obolibrary.org/obo/DOID_0001816",
        )
        self.assertEqual(
            curie_to_uri("CHEBI:15365"),
            "http://purl.obolibrary.org/obo/CHEBI_15365",
        )
        self.assertEqual(
            curie_to_uri("http://example.org/test"),
            "http://example.org/test",
        )

    def test_extract_namespace(self):
        self.assertEqual(extract_namespace("DOID:0001816"), "DOID")
        self.assertEqual(
            extract_namespace("http://purl.obolibrary.org/obo/DOID_0001816"),
            "DOID",
        )
        self.assertEqual(extract_namespace("CHEBI:15365"), "CHEBI")
        self.assertEqual(extract_namespace("is_a"), "rdfs")
        self.assertEqual(extract_namespace(""), "UNKNOWN")

    def test_normalize_identifier(self):
        self.assertEqual(normalize_identifier("DOID:0001816"), "DOID:0001816")
        self.assertEqual(normalize_identifier("doid:0001816"), "DOID:0001816")
        self.assertEqual(normalize_identifier("DOID_0001816"), "DOID:0001816")
        self.assertEqual(normalize_identifier("0001816"), "DOID:0001816")
        self.assertEqual(normalize_identifier("4"), "DOID:4")
        self.assertEqual(
            normalize_identifier("http://purl.obolibrary.org/obo/DOID_4"),
            "DOID:4",
        )


if __name__ == "__main__":
    unittest.main()
