"""Base interface for ontology dataset importers."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional, Union

from findotype.models.stats import ImportStats


class BaseImporter(ABC):
    """Abstract base class for all ontology dataset importers."""

    @abstractmethod
    def validate(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Validate the raw dataset file format and integrity.

        Returns a dictionary with validation summary:
        {'valid': bool, 'errors': list, 'warnings': list, 'node_count': int, 'edge_count': int}
        """
        pass

    @abstractmethod
    def import_dataset(
        self,
        file_path: Union[str, Path],
        db_path: Union[str, Path],
        include_obsolete: bool = False,
        source_url: Optional[str] = None,
    ) -> ImportStats:
        """
        Import the dataset into the SQLite database inside a transaction.

        Returns ImportStats with counts of ingested entities.
        """
        pass
