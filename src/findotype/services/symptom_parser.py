"""Clinical symptom extractor for natural language expressions and structured lists."""

import math
import re
import sqlite3
from typing import List, Set, Union

from findotype.models.phenotype import ExtractedSymptom
from findotype.ontology.curie import normalize_identifier


class SymptomParser:
    """Extracts canonical HPO phenotype terms from natural language or structured queries."""

    STOP_PHRASES = [
        r"\bi have\b",
        r"\bi feel\b",
        r"\bi am experiencing\b",
        r"\bi'm experiencing\b",
        r"\bpatient presents with\b",
        r"\bpatient has\b",
        r"\bcomplaining of\b",
        r"\bsuffering from\b",
        r"\bsymptoms of\b",
        r"\bsymptoms include\b",
        r"\bsymptoms are\b",
        r"\band\b",
        r"\balso\b",
        r"\bwith\b",
        r"\bsevere\b",
        r"\bmild\b",
        r"\bacute\b",
        r"\bchronic\b",
    ]

    def __init__(self, connection: sqlite3.Connection):
        self.conn = connection

    def _clean_natural_language(self, text: str) -> List[str]:
        """Convert natural language string into candidate symptom phrases."""
        cleaned = text.lower()
        for phrase_pat in self.STOP_PHRASES:
            cleaned = re.sub(phrase_pat, ",", cleaned, flags=re.IGNORECASE)

        raw_parts = re.split(r"[,;\n\.\+\-\•]+", cleaned)
        candidate_phrases = []
        for part in raw_parts:
            p = part.strip()
            p = re.sub(r"[^\w\s\-]", "", p).strip()
            if len(p) >= 2 and p not in ("i", "have", "a", "an", "the", "in", "my", "is", "and"):
                candidate_phrases.append(p)
        return candidate_phrases

    def _get_equivalent_ids(self, term_name: str) -> List[str]:
        """Find equivalent SYMP, HP, or DOID IDs matching a phenotype name."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT id FROM entities 
            WHERE LOWER(name) = LOWER(?) AND namespace IN ('HP', 'SYMP')
            UNION
            SELECT s.entity_id FROM synonyms s
            JOIN entities e ON s.entity_id = e.id
            WHERE LOWER(s.synonym) = LOWER(?) AND e.namespace IN ('HP', 'SYMP');
            """,
            (term_name, term_name),
        )
        return [row[0] for row in cursor.fetchall()]

    def _calculate_ic(self, equivalent_ids: List[str], term_name: str) -> float:
        """Calculate statistical Information Content (IC) based on disease annotations."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM entities WHERE namespace = 'DOID' OR id LIKE 'DOID:%';")
        total_diseases = max(1, cursor.fetchone()[0])

        placeholders = ",".join("?" * len(equivalent_ids)) if equivalent_ids else "''"
        sql = f"""
        SELECT COUNT(DISTINCT r.subject_id)
        FROM relationships r
        WHERE r.object_id IN ({placeholders})
          AND r.subject_id LIKE 'DOID:%'
          AND r.predicate_label LIKE '%symptom%';
        """
        cursor.execute(sql, tuple(equivalent_ids) if equivalent_ids else ())
        count = cursor.fetchone()[0]

        # Also check definition mentions
        cursor.execute(
            """
            SELECT COUNT(*) FROM definitions
            WHERE entity_id LIKE 'DOID:%'
              AND (definition LIKE ? OR definition LIKE ?);
            """,
            (f"%has symptom {term_name}%", f"%has_symptom {term_name}%"),
        )
        def_count = cursor.fetchone()[0]
        total_annotated = max(1, count + def_count)

        # Statistical IC: rarity = -ln(P(symptom))
        ic = -math.log((total_annotated + 1) / (total_diseases + 1))
        return round(max(1.0, ic), 2)

    def extract_symptoms(
        self, query: Union[str, List[str]]
    ) -> List[ExtractedSymptom]:
        """
        Parse input text or list into recognized canonical ExtractedSymptom objects.
        Prioritizes HPO (HP:) identifiers as canonical concepts.
        """
        candidates: List[str] = []
        if isinstance(query, list):
            for item in query:
                if isinstance(item, str):
                    candidates.extend(self._clean_natural_language(item))
        elif isinstance(query, str):
            candidates = self._clean_natural_language(query)

        extracted: List[ExtractedSymptom] = []
        seen_ids: Set[str] = set()
        seen_names: Set[str] = set()

        cursor = self.conn.cursor()

        for cand in candidates:
            cand_clean = cand.strip()
            if not cand_clean or cand_clean.lower() in seen_names:
                continue

            # 1. Direct CURIE check (e.g. HP:0001945 or SYMP:0000596)
            norm_id = normalize_identifier(cand_clean)
            cursor.execute(
                "SELECT id, name, namespace FROM entities WHERE id = ? LIMIT 1;",
                (norm_id,),
            )
            row = cursor.fetchone()
            if row:
                term_id = row["id"]
                term_name = row["name"]
                if term_id not in seen_ids:
                    seen_ids.add(term_id)
                    seen_names.add(term_name.lower())
                    eq_ids = self._get_equivalent_ids(term_name)
                    if term_id not in eq_ids:
                        eq_ids.append(term_id)
                    ic = self._calculate_ic(eq_ids, term_name)
                    extracted.append(
                        ExtractedSymptom(
                            raw_query_text=cand_clean,
                            matched_term_id=term_id,
                            matched_term_name=term_name,
                            confidence=1.0,
                            information_content=ic,
                            synonym_ids=eq_ids,
                        )
                    )
                    continue

            # 2. Match in entities (preferring HP namespace first)
            cursor.execute(
                """
                SELECT id, name, namespace FROM entities 
                WHERE LOWER(name) = LOWER(?) AND (namespace IN ('HP', 'SYMP') OR id LIKE 'HP:%' OR id LIKE 'SYMP:%')
                ORDER BY CASE WHEN namespace = 'HP' OR id LIKE 'HP:%' THEN 1 ELSE 2 END
                LIMIT 1;
                """,
                (cand_clean,),
            )
            row = cursor.fetchone()
            if row:
                term_id = row["id"]
                term_name = row["name"]
                if term_id not in seen_ids:
                    seen_ids.add(term_id)
                    seen_names.add(term_name.lower())
                    eq_ids = self._get_equivalent_ids(term_name)
                    if term_id not in eq_ids:
                        eq_ids.append(term_id)
                    ic = self._calculate_ic(eq_ids, term_name)
                    extracted.append(
                        ExtractedSymptom(
                            raw_query_text=cand_clean,
                            matched_term_id=term_id,
                            matched_term_name=term_name,
                            confidence=0.98,
                            information_content=ic,
                            synonym_ids=eq_ids,
                        )
                    )
                    continue

            # 3. Match in synonyms (preferring HP namespace first)
            cursor.execute(
                """
                SELECT s.entity_id, e.name, e.namespace 
                FROM synonyms s
                JOIN entities e ON s.entity_id = e.id
                WHERE LOWER(s.synonym) = LOWER(?) AND (e.namespace IN ('HP', 'SYMP') OR e.id LIKE 'HP:%' OR e.id LIKE 'SYMP:%')
                ORDER BY CASE WHEN e.namespace = 'HP' OR e.id LIKE 'HP:%' THEN 1 ELSE 2 END
                LIMIT 1;
                """,
                (cand_clean,),
            )
            row = cursor.fetchone()
            if row:
                term_id = row["entity_id"]
                term_name = row["name"]
                if term_id not in seen_ids:
                    seen_ids.add(term_id)
                    seen_names.add(term_name.lower())
                    eq_ids = self._get_equivalent_ids(term_name)
                    if term_id not in eq_ids:
                        eq_ids.append(term_id)
                    ic = self._calculate_ic(eq_ids, term_name)
                    extracted.append(
                        ExtractedSymptom(
                            raw_query_text=cand_clean,
                            matched_term_id=term_id,
                            matched_term_name=term_name,
                            confidence=0.95,
                            information_content=ic,
                            synonym_ids=eq_ids,
                        )
                    )
                    continue

            # 4. Fallback: Prefix match in HP or SYMP entities
            cursor.execute(
                """
                SELECT id, name, namespace FROM entities 
                WHERE name LIKE ? AND (namespace IN ('HP', 'SYMP') OR id LIKE 'HP:%' OR id LIKE 'SYMP:%')
                ORDER BY CASE WHEN namespace = 'HP' OR id LIKE 'HP:%' THEN 1 ELSE 2 END, LENGTH(name) ASC
                LIMIT 1;
                """,
                (f"{cand_clean}%",),
            )
            row = cursor.fetchone()
            if row:
                term_id = row["id"]
                term_name = row["name"]
                if term_id not in seen_ids:
                    seen_ids.add(term_id)
                    seen_names.add(term_name.lower())
                    eq_ids = self._get_equivalent_ids(term_name)
                    if term_id not in eq_ids:
                        eq_ids.append(term_id)
                    ic = self._calculate_ic(eq_ids, term_name)
                    extracted.append(
                        ExtractedSymptom(
                            raw_query_text=cand_clean,
                            matched_term_id=term_id,
                            matched_term_name=term_name,
                            confidence=0.85,
                            information_content=ic,
                            synonym_ids=eq_ids,
                        )
                    )
                    continue

        return extracted
