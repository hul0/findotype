"""Data models representing diseases, synonyms, definitions, and cross-references."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class Synonym:
    """Represents a synonym of an ontology entity."""
    synonym: str
    scope: str  # EXACT, NARROW, BROAD, RELATED
    synonym_type: Optional[str] = None
    xrefs: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class Definition:
    """Represents the formal definition of an ontology entity."""
    definition: str
    sources: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class CrossReference:
    """Represents a cross-reference to external databases (e.g. MESH, ICD10, OMIM, UMLS)."""
    db: str
    accession: str
    full_reference: str


@dataclass(frozen=True)
class Subset:
    """Represents an ontology subset or slim (e.g. DO_cancer_slim)."""
    name: str


@dataclass(frozen=True)
class Disease:
    """Represents a disease or ontology entity with its rich associated metadata."""
    id: str  # e.g. "DOID:0001816"
    name: str  # e.g. "angiosarcoma"
    uri: str  # e.g. "http://purl.obolibrary.org/obo/DOID_0001816"
    namespace: Optional[str] = "disease_ontology"
    entity_type: str = "CLASS"
    is_obsolete: bool = False
    comment: Optional[str] = None
    definition: Optional[Definition] = None
    synonyms: List[Synonym] = field(default_factory=list)
    cross_references: List[CrossReference] = field(default_factory=list)
    subsets: List[Subset] = field(default_factory=list)
    alt_ids: List[str] = field(default_factory=list)

    @property
    def exact_synonyms(self) -> List[str]:
        """Convenience property for exact synonyms."""
        return [s.synonym for s in self.synonyms if s.scope == "EXACT"]
