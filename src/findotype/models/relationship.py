"""Data models representing ontology graph relationships and hierarchy nodes."""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class Relationship:
    """Represents a directed relationship between two ontology entities."""
    subject_id: str
    subject_name: Optional[str]
    predicate_id: str  # e.g. "is_a", "RO:0002452", "IDO:0000664"
    predicate_label: str  # e.g. "is_a", "has substance added", "has material basis in"
    object_id: str
    object_name: Optional[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class HierarchyNode:
    """Represents a node in an ontology hierarchy tree with its depth and distance."""
    id: str
    name: str
    depth: int = 0
    predicate_id: str = "is_a"
    predicate_label: str = "is_a"
