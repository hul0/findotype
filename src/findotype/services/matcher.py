"""Clinical phenotype-to-disease matching engine with disease-specific relationship queries."""

import sqlite3
from typing import Dict, List, Set, Union

from findotype.models.phenotype import (
    MatchedPhenotype,
    PhenotypeMatchResult,
)
from findotype.services.symptom_parser import SymptomParser


class PhenotypeMatcher:
    """
    Matches a collection of clinical symptoms against candidate diseases using
    disease-specific ontology relationship graphs and definition annotations.
    """

    def __init__(self, connection: sqlite3.Connection):
        self.conn = connection
        self.parser = SymptomParser(connection)

    def match_symptoms(
        self, query: Union[str, List[str]], limit: int = 10
    ) -> List[PhenotypeMatchResult]:
        """
        Match symptoms against candidate diseases.

        Args:
            query: Natural language string or list of symptoms
            limit: Maximum number of candidate diseases to return

        Returns:
            List of PhenotypeMatchResult objects ranked by phenotype concordance
        """
        extracted = self.parser.extract_symptoms(query)
        if not extracted:
            return []

        cursor = self.conn.cursor()

        # Build candidate associations: symptom -> set of (disease_id, source)
        symptom_to_disease_matches: Dict[str, Dict[str, str]] = {}
        total_query_ic = sum(s.information_content for s in extracted)

        for sym in extracted:
            matches_for_sym: Dict[str, str] = {}  # disease_id -> source ('relationship' or 'definition')

            # 1. Graph relationships (DOID --has_symptom--> HP/SYMP)
            term_ids = sym.synonym_ids if sym.synonym_ids else [sym.matched_term_id]
            placeholders = ",".join("?" * len(term_ids))

            sql = f"""
            SELECT DISTINCT r.subject_id
            FROM relationships r
            WHERE r.object_id IN ({placeholders})
              AND r.subject_id LIKE 'DOID:%'
              AND (r.predicate_label LIKE '%symptom%' OR r.predicate_label LIKE '%phenotype%');
            """
            cursor.execute(sql, tuple(term_ids))
            for row in cursor.fetchall():
                matches_for_sym[row[0]] = "relationship"

            # 2. Textual symptom assertions in definition
            symptom_lower = sym.matched_term_name.lower()
            cursor.execute(
                """
                SELECT entity_id, definition 
                FROM definitions
                WHERE entity_id LIKE 'DOID:%'
                  AND (
                    definition LIKE ? OR definition LIKE ? OR definition LIKE ?
                  );
                """,
                (
                    f"%has symptom {symptom_lower}%",
                    f"%has_symptom {symptom_lower}%",
                    f"%symptom {symptom_lower}%",
                ),
            )
            for row in cursor.fetchall():
                did = row[0]
                if did not in matches_for_sym:
                    matches_for_sym[did] = "definition"

            symptom_to_disease_matches[sym.matched_term_id] = matches_for_sym

        # Group all candidate diseases that have at least ONE matched symptom
        all_candidate_doids: Set[str] = set()
        for matches in symptom_to_disease_matches.values():
            all_candidate_doids.update(matches.keys())

        if not all_candidate_doids:
            return []

        # For each candidate disease, calculate exact matched and unmatched symptoms
        results: List[PhenotypeMatchResult] = []

        for did in all_candidate_doids:
            # Retrieve disease name and definition
            cursor.execute(
                """
                SELECT e.id, e.name, d.definition
                FROM entities e
                LEFT JOIN definitions d ON e.id = d.entity_id
                WHERE e.id = ?;
                """,
                (did,),
            )
            row = cursor.fetchone()
            if not row:
                continue

            matched_phenotypes: List[MatchedPhenotype] = []
            unmatched_phenotypes: List[MatchedPhenotype] = []
            matched_ic_sum = 0.0

            for sym in extracted:
                if did in symptom_to_disease_matches.get(sym.matched_term_id, {}):
                    source = symptom_to_disease_matches[sym.matched_term_id][did]
                    matched_phenotypes.append(
                        MatchedPhenotype(
                            id=sym.matched_term_id,
                            name=sym.matched_term_name,
                            ic=sym.information_content,
                            source=source,
                        )
                    )
                    matched_ic_sum += sym.information_content
                else:
                    unmatched_phenotypes.append(
                        MatchedPhenotype(
                            id=sym.matched_term_id,
                            name=sym.matched_term_name,
                            ic=sym.information_content,
                        )
                    )

            matched_count = len(matched_phenotypes)
            total_count = len(extracted)

            # Query coverage percentage (weighted by Information Content)
            if total_query_ic > 0:
                weighted_coverage = (matched_ic_sum / total_query_ic) * 100.0
            else:
                weighted_coverage = (matched_count / total_count) * 100.0

            # Score is weighted overlap (0.0 to 1.0)
            score = (matched_ic_sum / total_query_ic) * (0.5 + 0.5 * (matched_count / total_count))

            results.append(
                PhenotypeMatchResult(
                    disease_id=row["id"],
                    disease_name=row["name"],
                    score=round(score, 2),
                    query_coverage_pct=round(weighted_coverage, 1),
                    matched_count=matched_count,
                    total_query_count=total_count,
                    matched_phenotypes=matched_phenotypes,
                    unmatched_phenotypes=unmatched_phenotypes,
                    disease_definition=row["definition"],
                )
            )

        # Rank candidate diseases:
        # 1. Number of matched query symptoms (descending)
        # 2. Weighted query coverage (descending)
        # 3. Overall overlap score (descending)
        results.sort(
            key=lambda r: (r.matched_count, r.query_coverage_pct, r.score),
            reverse=True,
        )

        return results[:limit]
