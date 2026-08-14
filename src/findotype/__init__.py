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
    DatasetMetadata,
    DatasetProvenance,
    KnowledgeBaseMetadata,
    Provenance,
)
from findotype.models.phenotype import (
    ExtractedSymptom,
    MatchedPhenotype,
    PhenotypeMatchResult,
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
from findotype.server.app import run_server

__version__ = "1.0.0"
__author__ = "Rupam Ghosh"
__email__ = "hulo@crine.in"
__license__ = "AGPL-3.0-or-later"

__all__ = [
    "Findotype",
    "run_server",
    "Disease",
    "Synonym",
    "Definition",
    "CrossReference",
    "Subset",
    "Relationship",
    "HierarchyNode",
    "Provenance",
    "DatasetMetadata",
    "DatasetProvenance",
    "KnowledgeBaseMetadata",
    "ExtractedSymptom",
    "MatchedPhenotype",
    "PhenotypeMatchResult",
    "SearchResult",
    "SearchMatchType",
    "ImportStats",
    "DatabaseStats",
]
