"""Data models for clinical symptoms, phenotype extraction, and disease matching results."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class ExtractedSymptom:
    """Represents a recognized clinical symptom or phenotype extracted from user input."""
    raw_query_text: str
    matched_term_id: str  # Canonical HPO ID (e.g. 'HP:0001945')
    matched_term_name: str  # Canonical name (e.g. 'Fever')
    confidence: float = 1.0
    information_content: float = 1.0  # Statistical rarity / specificity (IC)
    synonym_ids: List[str] = field(default_factory=list)  # Alternative vocabulary IDs, e.g. ['SYMP:0000613']


@dataclass(frozen=True)
class MatchedPhenotype:
    """A matched phenotype associated with a candidate disease."""
    id: str  # Canonical HPO ID
    name: str  # Phenotype name
    ic: float  # Information content
    source: str = "relationship"  # 'relationship' or 'definition'


@dataclass(frozen=True)
class PhenotypeMatchResult:
    """
    Represents a candidate disease matched against user-provided symptoms.

    Note: Scores represent ontology symptom concordance, NOT a clinical
    diagnosis or medical probability.
    """
    disease_id: str
    disease_name: str
    score: float  # Weighted phenotype overlap score (0.0 to 1.0)
    query_coverage_pct: float  # Percentage of user's query covered by this disease (0.0 to 100.0%)
    matched_count: int  # e.g. 2
    total_query_count: int  # e.g. 3
    matched_phenotypes: List[MatchedPhenotype] = field(default_factory=list)
    unmatched_phenotypes: List[MatchedPhenotype] = field(default_factory=list)
    disease_definition: Optional[str] = None

    @property
    def match_percentage(self) -> float:
        """Backward-compatible alias for query_coverage_pct."""
        return self.query_coverage_pct

    @property
    def overlap_score(self) -> float:
        """Backward-compatible alias for score as percentage (0-100%)."""
        return round(self.score * 100.0, 1)

    @property
    def specificity_level(self) -> str:
        """Categorize matched phenotype specificity based on average IC."""
        if not self.matched_phenotypes:
            return "NONE"
        avg_ic = sum(p.ic for p in self.matched_phenotypes) / len(self.matched_phenotypes)
        if avg_ic < 3.5:
            return "LOW (Common/Generic Symptoms)"
        elif avg_ic < 5.5:
            return "MODERATE"
        return "HIGH (Distinctive Phenotypic Markers)"

    @property
    def matched_symptoms(self) -> List[ExtractedSymptom]:
        """Backward-compatible property returning matched symptoms as ExtractedSymptom list."""
        return [
            ExtractedSymptom(
                raw_query_text=p.name,
                matched_term_id=p.id,
                matched_term_name=p.name,
                information_content=p.ic,
            )
            for p in self.matched_phenotypes
        ]

    @property
    def unmatched_query_symptoms(self) -> List[str]:
        """Backward-compatible property returning list of unmatched symptom names."""
        return [p.name for p in self.unmatched_phenotypes]
