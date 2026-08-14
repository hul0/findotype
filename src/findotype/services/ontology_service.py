"""Findotype: High-level Python service and library interface."""

import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from findotype.config import DEFAULT_DB_PATH
from findotype.db.connection import get_connection
from findotype.importers.doid import DiseaseOntologyImporter
from findotype.importers.hpo import HpoImporter
from findotype.models.disease import CrossReference, Definition, Disease, Synonym
from findotype.models.phenotype import ExtractedSymptom, PhenotypeMatchResult
from findotype.models.provenance import (
    DatasetMetadata,
    DatasetProvenance,
    KnowledgeBaseMetadata,
    Provenance,
)
from findotype.models.relationship import HierarchyNode, Relationship
from findotype.models.search import SearchResult
from findotype.models.stats import DatabaseStats, ImportStats
from findotype.repositories.disease_repo import DiseaseRepository
from findotype.repositories.metadata_repo import MetadataRepository
from findotype.services.matcher import PhenotypeMatcher
from findotype.services.symptom_parser import SymptomParser


class Findotype:
    """
    Main interface for the Findotype Disease Ontology library and query engine.

    Example:
        >>> from findotype import Findotype
        >>> engine = Findotype("disease_ontology.db")
        >>> disease = engine.get_disease("DOID:0001816")
        >>> print(disease.name)
        'angiosarcoma'
        >>> results = engine.match_phenotypes("I have fever, cough, nausea")
    """

    def __init__(
        self,
        db_path: Union[str, Path] = DEFAULT_DB_PATH,
        initialize_schema: bool = True,
    ):
        self.db_path = Path(db_path) if db_path != ":memory:" else ":memory:"
        self._conn: Optional[sqlite3.Connection] = None
        self._initialize_schema = initialize_schema

    @property
    def connection(self) -> sqlite3.Connection:
        """Lazily initialize and return the SQLite connection."""
        if self._conn is None:
            self._conn = get_connection(
                self.db_path,
                initialize_schema=self._initialize_schema,
            )
        return self._conn

    @property
    def disease_repo(self) -> DiseaseRepository:
        """Disease repository instance."""
        return DiseaseRepository(self.connection)

    @property
    def metadata_repo(self) -> MetadataRepository:
        """Metadata and provenance repository instance."""
        return MetadataRepository(self.connection)

    @property
    def matcher(self) -> PhenotypeMatcher:
        """Clinical phenotype matching engine."""
        return PhenotypeMatcher(self.connection)

    @property
    def symptom_parser(self) -> SymptomParser:
        """Clinical symptom parser."""
        return SymptomParser(self.connection)

    def close(self) -> None:
        """Close the underlying SQLite connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    # --- Clinical Phenotype & Symptom Matching ---

    def extract_symptoms(self, query: Union[str, List[str]]) -> List[ExtractedSymptom]:
        """
        Extract recognized ontology phenotype terms from natural language or text.
        """
        return self.symptom_parser.extract_symptoms(query)

    def match_phenotypes(
        self, query: Union[str, List[str]], limit: int = 10
    ) -> List[PhenotypeMatchResult]:
        """
        Match user symptoms (e.g. 'I have fever, cough, nausea') against candidate diseases
        and compute match percentages based on Information Content weighting.
        """
        return self.matcher.match_symptoms(query, limit=limit)

    def match_symptoms(
        self, query: Union[str, List[str]], limit: int = 10
    ) -> List[PhenotypeMatchResult]:
        """Alias for match_phenotypes."""
        return self.match_phenotypes(query, limit=limit)

    # --- Core Disease Queries ---

    def get_disease(self, identifier: str) -> Optional[Disease]:
        """
        Retrieve a disease by DOID (e.g. 'DOID:0001816', 'DOID_0001816', or numeric '0001816')
        or alternative merged ID.
        """
        return self.disease_repo.get_by_id(identifier)

    def get_disease_by_name(self, name: str) -> Optional[Disease]:
        """Retrieve a disease by exact name (case-insensitive)."""
        return self.disease_repo.get_by_name(name)

    def search_diseases(self, query: str, limit: int = 20) -> List[SearchResult]:
        """
        Search diseases using multi-tiered matching: exact DOID, exact/prefix name,
        synonyms, and FTS5 full-text rank.
        """
        return self.disease_repo.search(query, limit=limit)

    def get_synonyms(self, identifier: str) -> List[Synonym]:
        """Retrieve all synonyms for a given disease."""
        return self.disease_repo.get_synonyms(identifier)

    def get_definition(self, identifier: str) -> Optional[Definition]:
        """Retrieve the definition and source citations for a disease."""
        return self.disease_repo.get_definition(identifier)

    def get_cross_references(
        self, identifier: str, db: Optional[str] = None
    ) -> List[CrossReference]:
        """Retrieve external database cross references (MESH, ICD10, OMIM, UMLS, etc.)."""
        return self.disease_repo.get_cross_references(identifier, db=db)

    # --- Hierarchy & Graph Queries ---

    def get_parents(self, identifier: str, predicate: str = "is_a") -> List[HierarchyNode]:
        """Retrieve direct 1-hop parent terms."""
        return self.disease_repo.get_parents(identifier, predicate=predicate)

    def get_children(self, identifier: str, predicate: str = "is_a") -> List[HierarchyNode]:
        """Retrieve direct 1-hop child terms."""
        return self.disease_repo.get_children(identifier, predicate=predicate)

    def get_ancestors(
        self, identifier: str, predicate: str = "is_a", max_depth: int = 50
    ) -> List[HierarchyNode]:
        """Retrieve all ancestor terms up the hierarchy tree."""
        return self.disease_repo.get_ancestors(
            identifier, predicate=predicate, max_depth=max_depth
        )

    def get_descendants(
        self, identifier: str, predicate: str = "is_a", max_depth: int = 50
    ) -> List[HierarchyNode]:
        """Retrieve all descendant terms down the hierarchy tree."""
        return self.disease_repo.get_descendants(
            identifier, predicate=predicate, max_depth=max_depth
        )

    def get_relationships(
        self,
        identifier: str,
        predicate: Optional[str] = None,
        direction: str = "both",
    ) -> List[Relationship]:
        """Retrieve typed graph relationships (e.g. causes, triggers, phenotypes)."""
        return self.disease_repo.get_relationships(
            identifier, predicate=predicate, direction=direction
        )

    # --- Provenance & Metadata ---

    def get_provenance(self, dataset_name: Optional[str] = None) -> Optional[Provenance]:
        """Retrieve provenance record for a specific dataset or the latest imported dataset."""
        return self.metadata_repo.get_provenance(dataset_name=dataset_name)

    def get_datasets(self) -> List[DatasetProvenance]:
        """Retrieve list of all individual datasets ingested into this database."""
        return self.metadata_repo.get_provenance_list()

    def get_knowledge_base_metadata(self) -> KnowledgeBaseMetadata:
        """Retrieve top-level Knowledge Base metadata and constituent datasets."""
        return self.metadata_repo.get_knowledge_base_metadata()

    def get_metadata(self) -> DatasetMetadata:
        """Retrieve dataset title, description, license, root term, and version."""
        return self.metadata_repo.get_metadata()

    def get_stats(self) -> DatabaseStats:
        """Retrieve comprehensive database statistics, entity counts, and disk size."""
        db_p = self.db_path if isinstance(self.db_path, Path) else None
        return self.metadata_repo.get_database_stats(db_path=db_p)

    # --- Dataset Operations ---

    def import_doid(
        self,
        file_path: Union[str, Path],
        include_obsolete: bool = False,
        source_url: Optional[str] = None,
    ) -> ImportStats:
        """
        Import a doid.json file into the configured database.
        """
        importer = DiseaseOntologyImporter()
        stats = importer.import_dataset(
            file_path=file_path,
            db_path=self.db_path,
            include_obsolete=include_obsolete,
            source_url=source_url,
        )
        if self._conn is not None:
            self._conn.close()
            self._conn = None
        return stats

    def import_hpo(
        self,
        file_path: Union[str, Path],
        include_obsolete: bool = False,
        source_url: Optional[str] = None,
    ) -> ImportStats:
        """
        Import an hp-base.json file into the configured database.
        """
        importer = HpoImporter()
        stats = importer.import_dataset(
            file_path=file_path,
            db_path=self.db_path,
            include_obsolete=include_obsolete,
            source_url=source_url,
        )
        if self._conn is not None:
            self._conn.close()
            self._conn = None
        return stats

    @staticmethod
    def validate_doid(file_path: Union[str, Path]) -> Dict[str, Any]:
        """Validate a doid.json file before importing."""
        return DiseaseOntologyImporter().validate(file_path)

    @staticmethod
    def validate_hpo(file_path: Union[str, Path]) -> Dict[str, Any]:
        """Validate an hp-base.json file before importing."""
        return HpoImporter().validate(file_path)
