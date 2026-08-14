"""Data models for data provenance, release information, and dataset metadata."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class DatasetProvenance:
    """Represents the cryptographic and release provenance of an individual ingested dataset."""
    dataset_name: str
    dataset_version: Optional[str]
    release_date: Optional[str] = None
    license: Optional[str] = None
    root_term: Optional[str] = None
    source_uri: Optional[str] = None
    source_sha256: str = ""
    schema_version: str = "1.0.0"
    imported_at: str = ""
    stats: Dict[str, Any] = field(default_factory=dict)


# Backward compatibility alias
Provenance = DatasetProvenance


@dataclass(frozen=True)
class KnowledgeBaseMetadata:
    """Top-level metadata for the Findotype Knowledge Base across all ingested ontologies."""
    name: str = "Findotype Biomedical Knowledge Base"
    schema_version: str = "1.0.0"
    datasets: List[DatasetProvenance] = field(default_factory=list)


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
