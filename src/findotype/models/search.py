"""Data models for full-text search results and match categorization."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class SearchMatchType(str, Enum):
    """Categorization of how a search result matched the query."""
    EXACT_ID = "EXACT_ID"
    ALT_ID = "ALT_ID"
    EXACT_NAME = "EXACT_NAME"
    PREFIX_NAME = "PREFIX_NAME"
    SYNONYM = "SYNONYM"
    DEFINITION = "DEFINITION"
    FTS_RANKED = "FTS_RANKED"


@dataclass(frozen=True)
class SearchResult:
    """Represents a single ranked search result."""
    id: str
    name: str
    match_type: SearchMatchType
    matched_text: str
    rank_score: float
    definition: Optional[str] = None
