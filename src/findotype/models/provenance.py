"""Data models for data provenance, release information, and dataset metadata."""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class Provenance:
    """Represents the cryptographic and historical provenance of an imported dataset."""
    dataset_name: str
    dataset_version: Optional[str]
    source_uri: Optional[str]
    source_sha256: str
    schema_version: str
    imported_at: str
    stats: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DatasetMetadata:
    """Key-value ontology metadata (e.g. title, description, license, root term)."""
    title: Optional[str] = None
    description: Optional[str] = None
    version: Optional[str] = None
    date: Optional[str] = None
    license: Optional[str] = None
    root_term: Optional[str] = None
    extra_properties: Dict[str, str] = field(default_factory=dict)
