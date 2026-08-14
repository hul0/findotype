"""Data models for import statistics and database metrics."""

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class ImportStats:
    """Statistics captured during dataset import."""
    entities_count: int
    diseases_count: int
    synonyms_count: int
    definitions_count: int
    xrefs_count: int
    relationships_count: int
    subsets_count: int
    alt_ids_count: int
    obsolete_skipped: int
    duration_seconds: float


@dataclass(frozen=True)
class DatabaseStats:
    """Overall statistics for the SQLite database."""
    total_entities: int
    total_diseases: int
    total_synonyms: int
    total_definitions: int
    total_xrefs: int
    total_relationships: int
    total_subsets: int
    total_alt_ids: int
    db_size_bytes: int
    entity_namespaces: Dict[str, int]
    top_predicates: Dict[str, int]
    top_xref_databases: Dict[str, int]
