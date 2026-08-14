"""
Findotype: High-Performance Offline Disease Ontology Backend & SQLite Search Engine.

Author: Rupam Ghosh
License: GNU AGPL-3.0-or-later
"""

from findotype.models.disease import (
    Disease,
    Synonym,
    Definition,
    CrossReference,
    Subset,
)
from findotype.models.relationship import (
    Relationship,
    HierarchyNode,
)
from findotype.models.provenance import (
    Provenance,
    DatasetMetadata,
)
from findotype.models.search import (
    SearchResult,
    SearchMatchType,
)
from findotype.models.stats import (
    ImportStats,
    DatabaseStats,
)
from findotype.services.ontology_service import Findotype

__version__ = "0.1.0"
__author__ = "Rupam Ghosh"
__license__ = "AGPL-3.0-or-later"

__all__ = [
    "Findotype",
    "Disease",
    "Synonym",
    "Definition",
    "CrossReference",
    "Subset",
    "Relationship",
    "HierarchyNode",
    "Provenance",
    "DatasetMetadata",
    "SearchResult",
    "SearchMatchType",
    "ImportStats",
    "DatabaseStats",
]
