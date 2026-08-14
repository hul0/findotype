"""Ontology normalization and identifier conversion package."""

from findotype.ontology.curie import (
    curie_to_uri,
    extract_namespace,
    normalize_identifier,
    uri_to_curie,
)
from findotype.ontology.normalizer import (
    normalize_synonym_scope,
    parse_alt_ids,
    parse_cross_reference,
    parse_definition,
    parse_subsets,
    parse_synonyms,
)

__all__ = [
    "uri_to_curie",
    "curie_to_uri",
    "extract_namespace",
    "normalize_identifier",
    "normalize_synonym_scope",
    "parse_cross_reference",
    "parse_definition",
    "parse_synonyms",
    "parse_subsets",
    "parse_alt_ids",
]
