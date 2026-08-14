"""Repository for disease queries, graph traversals, and FTS5 search."""

import json
import re
import sqlite3
from typing import Any, Dict, List, Optional, Set, Tuple

from findotype.models.disease import CrossReference, Definition, Disease, Subset, Synonym
from findotype.models.relationship import HierarchyNode, Relationship
from findotype.models.search import SearchMatchType, SearchResult
from findotype.ontology.curie import normalize_identifier


class DiseaseRepository:
    """Provides structured data access to diseases, ontology hierarchy, and FTS5 search."""

    def __init__(self, connection: sqlite3.Connection):
        self.conn = connection

    def _resolve_entity_id(self, identifier: str) -> Optional[str]:
        """Resolve a DOID or alternate ID to the canonical primary entity ID."""
        norm_id = normalize_identifier(identifier)
        cursor = self.conn.cursor()

        # Check direct entity ID
        cursor.execute("SELECT id FROM entities WHERE id = ? LIMIT 1;", (norm_id,))
        row = cursor.fetchone()
        if row:
            return row["id"]

        # Check alternative ID mapping
        cursor.execute("SELECT entity_id FROM alt_ids WHERE alt_id = ? LIMIT 1;", (norm_id,))
        row = cursor.fetchone()
        if row:
            return row["entity_id"]

        return None

    def get_by_id(self, identifier: str) -> Optional[Disease]:
        """Retrieve a complete Disease record by primary ID or alternative ID."""
        primary_id = self._resolve_entity_id(identifier)
        if not primary_id:
            return None

        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT id, uri, name, entity_type, namespace, is_obsolete, comment
            FROM entities
            WHERE id = ?;
            """,
            (primary_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None

        # Fetch definition
        cursor.execute(
            "SELECT definition, sources_json FROM definitions WHERE entity_id = ? LIMIT 1;",
            (primary_id,),
        )
        def_row = cursor.fetchone()
        definition = None
        if def_row:
            sources = json.loads(def_row["sources_json"]) if def_row["sources_json"] else []
            definition = Definition(definition=def_row["definition"], sources=sources)

        # Fetch synonyms
        cursor.execute(
            "SELECT synonym, scope, synonym_type, xrefs_json FROM synonyms WHERE entity_id = ?;",
            (primary_id,),
        )
        synonyms = []
        for s_row in cursor.fetchall():
            xrefs = json.loads(s_row["xrefs_json"]) if s_row["xrefs_json"] else []
            synonyms.append(
                Synonym(
                    synonym=s_row["synonym"],
                    scope=s_row["scope"],
                    synonym_type=s_row["synonym_type"],
                    xrefs=xrefs,
                )
            )

        # Fetch cross references
        cursor.execute(
            "SELECT db, accession, full_reference FROM cross_references WHERE entity_id = ?;",
            (primary_id,),
        )
        xrefs = [
            CrossReference(
                db=x_row["db"],
                accession=x_row["accession"],
                full_reference=x_row["full_reference"],
            )
            for x_row in cursor.fetchall()
        ]

        # Fetch subsets
        cursor.execute(
            "SELECT subset_name FROM subsets WHERE entity_id = ?;",
            (primary_id,),
        )
        subsets = [Subset(name=sub_row["subset_name"]) for sub_row in cursor.fetchall()]

        # Fetch alt IDs
        cursor.execute(
            "SELECT alt_id FROM alt_ids WHERE entity_id = ?;",
            (primary_id,),
        )
        alt_ids = [alt_row["alt_id"] for alt_row in cursor.fetchall()]

        return Disease(
            id=row["id"],
            name=row["name"],
            uri=row["uri"],
            namespace=row["namespace"],
            entity_type=row["entity_type"],
            is_obsolete=bool(row["is_obsolete"]),
            comment=row["comment"],
            definition=definition,
            synonyms=synonyms,
            cross_references=xrefs,
            subsets=subsets,
            alt_ids=alt_ids,
        )

    def get_by_name(self, name: str) -> Optional[Disease]:
        """Retrieve a disease by exact name (case-insensitive)."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id FROM entities WHERE LOWER(name) = LOWER(?) LIMIT 1;",
            (name.strip(),),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return self.get_by_id(row["id"])

    def get_definition(self, identifier: str) -> Optional[Definition]:
        """Retrieve only the formal definition for a disease."""
        primary_id = self._resolve_entity_id(identifier)
        if not primary_id:
            return None

        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT definition, sources_json FROM definitions WHERE entity_id = ? LIMIT 1;",
            (primary_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None

        sources = json.loads(row["sources_json"]) if row["sources_json"] else []
        return Definition(definition=row["definition"], sources=sources)

    def get_synonyms(self, identifier: str) -> List[Synonym]:
        """Retrieve all synonyms for a given disease ID."""
        primary_id = self._resolve_entity_id(identifier)
        if not primary_id:
            return []

        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT synonym, scope, synonym_type, xrefs_json FROM synonyms WHERE entity_id = ?;",
            (primary_id,),
        )
        results = []
        for row in cursor.fetchall():
            xrefs = json.loads(row["xrefs_json"]) if row["xrefs_json"] else []
            results.append(
                Synonym(
                    synonym=row["synonym"],
                    scope=row["scope"],
                    synonym_type=row["synonym_type"],
                    xrefs=xrefs,
                )
            )
        return results

    def get_cross_references(self, identifier: str, db: Optional[str] = None) -> List[CrossReference]:
        """Retrieve cross-references, optionally filtered by database name (e.g. MESH, ICD10CM)."""
        primary_id = self._resolve_entity_id(identifier)
        if not primary_id:
            return []

        cursor = self.conn.cursor()
        if db:
            cursor.execute(
                """
                SELECT db, accession, full_reference
                FROM cross_references
                WHERE entity_id = ? AND UPPER(db) = UPPER(?);
                """,
                (primary_id, db.strip()),
            )
        else:
            cursor.execute(
                """
                SELECT db, accession, full_reference
                FROM cross_references
                WHERE entity_id = ?;
                """,
                (primary_id,),
            )

        return [
            CrossReference(
                db=row["db"],
                accession=row["accession"],
                full_reference=row["full_reference"],
            )
            for row in cursor.fetchall()
        ]

    def get_parents(self, identifier: str, predicate: str = "is_a") -> List[HierarchyNode]:
        """Retrieve direct 1-hop parent terms (is_a or specific predicate)."""
        primary_id = self._resolve_entity_id(identifier)
        if not primary_id:
            return []

        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT e.id, e.name, r.predicate_id, r.predicate_label
            FROM relationships r
            JOIN entities e ON r.object_id = e.id
            WHERE r.subject_id = ? AND r.predicate_id = ?
            ORDER BY e.name ASC;
            """,
            (primary_id, predicate),
        )
        return [
            HierarchyNode(
                id=row["id"],
                name=row["name"],
                depth=1,
                predicate_id=row["predicate_id"],
                predicate_label=row["predicate_label"],
            )
            for row in cursor.fetchall()
        ]

    def get_children(self, identifier: str, predicate: str = "is_a") -> List[HierarchyNode]:
        """Retrieve direct 1-hop child terms (is_a or specific predicate)."""
        primary_id = self._resolve_entity_id(identifier)
        if not primary_id:
            return []

        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT e.id, e.name, r.predicate_id, r.predicate_label
            FROM relationships r
            JOIN entities e ON r.subject_id = e.id
            WHERE r.object_id = ? AND r.predicate_id = ?
            ORDER BY e.name ASC;
            """,
            (primary_id, predicate),
        )
        return [
            HierarchyNode(
                id=row["id"],
                name=row["name"],
                depth=1,
                predicate_id=row["predicate_id"],
                predicate_label=row["predicate_label"],
            )
            for row in cursor.fetchall()
        ]

    def get_ancestors(
        self, identifier: str, predicate: str = "is_a", max_depth: int = 50
    ) -> List[HierarchyNode]:
        """
        Recursively retrieve all ancestors up the ontology hierarchy using a CTE with cycle prevention.
        """
        primary_id = self._resolve_entity_id(identifier)
        if not primary_id:
            return []

        cursor = self.conn.cursor()
        query = f"""
        WITH RECURSIVE ancestor_tree(id, name, depth, predicate_id, predicate_label, path) AS (
            SELECT 
                e.id,
                e.name,
                1 AS depth,
                r.predicate_id,
                r.predicate_label,
                '/' || e.id || '/' AS path
            FROM relationships r
            JOIN entities e ON r.object_id = e.id
            WHERE r.subject_id = ? AND r.predicate_id = ?

            UNION ALL

            SELECT 
                e.id,
                e.name,
                t.depth + 1,
                r.predicate_id,
                r.predicate_label,
                t.path || e.id || '/'
            FROM relationships r
            JOIN entities e ON r.object_id = e.id
            JOIN ancestor_tree t ON r.subject_id = t.id
            WHERE r.predicate_id = ?
              AND t.depth < ?
              AND t.path NOT LIKE '%/' || e.id || '/%'
        )
        SELECT id, name, MIN(depth) as min_depth, predicate_id, predicate_label
        FROM ancestor_tree
        GROUP BY id
        ORDER BY min_depth ASC, name ASC;
        """
        cursor.execute(query, (primary_id, predicate, predicate, max_depth))
        return [
            HierarchyNode(
                id=row["id"],
                name=row["name"],
                depth=row["min_depth"],
                predicate_id=row["predicate_id"],
                predicate_label=row["predicate_label"],
            )
            for row in cursor.fetchall()
        ]

    def get_descendants(
        self, identifier: str, predicate: str = "is_a", max_depth: int = 50
    ) -> List[HierarchyNode]:
        """
        Recursively retrieve all descendants down the ontology hierarchy using a CTE with cycle prevention.
        """
        primary_id = self._resolve_entity_id(identifier)
        if not primary_id:
            return []

        cursor = self.conn.cursor()
        query = f"""
        WITH RECURSIVE descendant_tree(id, name, depth, predicate_id, predicate_label, path) AS (
            SELECT 
                e.id,
                e.name,
                1 AS depth,
                r.predicate_id,
                r.predicate_label,
                '/' || e.id || '/' AS path
            FROM relationships r
            JOIN entities e ON r.subject_id = e.id
            WHERE r.object_id = ? AND r.predicate_id = ?

            UNION ALL

            SELECT 
                e.id,
                e.name,
                t.depth + 1,
                r.predicate_id,
                r.predicate_label,
                t.path || e.id || '/'
            FROM relationships r
            JOIN entities e ON r.subject_id = e.id
            JOIN descendant_tree t ON r.object_id = t.id
            WHERE r.predicate_id = ?
              AND t.depth < ?
              AND t.path NOT LIKE '%/' || e.id || '/%'
        )
        SELECT id, name, MIN(depth) as min_depth, predicate_id, predicate_label
        FROM descendant_tree
        GROUP BY id
        ORDER BY min_depth ASC, name ASC;
        """
        cursor.execute(query, (primary_id, predicate, predicate, max_depth))
        return [
            HierarchyNode(
                id=row["id"],
                name=row["name"],
                depth=row["min_depth"],
                predicate_id=row["predicate_id"],
                predicate_label=row["predicate_label"],
            )
            for row in cursor.fetchall()
        ]

    def get_relationships(
        self,
        identifier: str,
        predicate: Optional[str] = None,
        direction: str = "both",  # "outgoing", "incoming", "both"
    ) -> List[Relationship]:
        """Retrieve typed graph relationships connected to this entity."""
        primary_id = self._resolve_entity_id(identifier)
        if not primary_id:
            return []

        cursor = self.conn.cursor()
        results: List[Relationship] = []

        # Outgoing (subject is this entity)
        if direction in ("outgoing", "both"):
            params: List[Any] = [primary_id]
            pred_sql = ""
            if predicate:
                pred_sql = "AND r.predicate_id = ?"
                params.append(predicate)

            cursor.execute(
                f"""
                SELECT 
                    r.subject_id, s.name as subject_name,
                    r.predicate_id, r.predicate_label,
                    r.object_id, o.name as object_name,
                    r.meta_json
                FROM relationships r
                JOIN entities s ON r.subject_id = s.id
                JOIN entities o ON r.object_id = o.id
                WHERE r.subject_id = ? {pred_sql};
                """,
                params,
            )
            for row in cursor.fetchall():
                meta = json.loads(row["meta_json"]) if row["meta_json"] else {}
                results.append(
                    Relationship(
                        subject_id=row["subject_id"],
                        subject_name=row["subject_name"],
                        predicate_id=row["predicate_id"],
                        predicate_label=row["predicate_label"],
                        object_id=row["object_id"],
                        object_name=row["object_name"],
                        metadata=meta,
                    )
                )

        # Incoming (object is this entity)
        if direction in ("incoming", "both"):
            params = [primary_id]
            pred_sql = ""
            if predicate:
                pred_sql = "AND r.predicate_id = ?"
                params.append(predicate)

            cursor.execute(
                f"""
                SELECT 
                    r.subject_id, s.name as subject_name,
                    r.predicate_id, r.predicate_label,
                    r.object_id, o.name as object_name,
                    r.meta_json
                FROM relationships r
                JOIN entities s ON r.subject_id = s.id
                JOIN entities o ON r.object_id = o.id
                WHERE r.object_id = ? {pred_sql};
                """,
                params,
            )
            for row in cursor.fetchall():
                meta = json.loads(row["meta_json"]) if row["meta_json"] else {}
                results.append(
                    Relationship(
                        subject_id=row["subject_id"],
                        subject_name=row["subject_name"],
                        predicate_id=row["predicate_id"],
                        predicate_label=row["predicate_label"],
                        object_id=row["object_id"],
                        object_name=row["object_name"],
                        metadata=meta,
                    )
                )

        return results

    def get_subsets(self, identifier: str) -> List[Subset]:
        """Retrieve subset tags (slims) for a disease."""
        primary_id = self._resolve_entity_id(identifier)
        if not primary_id:
            return []

        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT subset_name FROM subsets WHERE entity_id = ?;",
            (primary_id,),
        )
        return [Subset(name=row["subset_name"]) for row in cursor.fetchall()]

    def search(self, query: str, limit: int = 20) -> List[SearchResult]:
        """
        Execute multi-tiered search:
        1. Exact DOID / Alt ID match
        2. Exact Disease Name
        3. Prefix Disease Name
        4. Synonym match
        5. FTS5 Full-Text Search (definitions & terms)
        """
        cleaned_query = query.strip()
        if not cleaned_query:
            return []

        results: List[SearchResult] = []
        seen_ids: Set[str] = set()
        cursor = self.conn.cursor()

        # Tier 1: Check exact ID or Alt ID
        norm_id = normalize_identifier(cleaned_query)
        primary_id = self._resolve_entity_id(norm_id)
        if primary_id:
            cursor.execute(
                """
                SELECT e.id, e.name, d.definition
                FROM entities e
                LEFT JOIN definitions d ON e.id = d.entity_id
                WHERE e.id = ?;
                """,
                (primary_id,),
            )
            row = cursor.fetchone()
            if row:
                seen_ids.add(row["id"])
                match_type = SearchMatchType.EXACT_ID if norm_id == row["id"] else SearchMatchType.ALT_ID
                results.append(
                    SearchResult(
                        id=row["id"],
                        name=row["name"],
                        match_type=match_type,
                        matched_text=norm_id,
                        rank_score=100.0,
                        definition=row["definition"],
                    )
                )
                if len(results) >= limit:
                    return results

        # Tier 2: Exact Name Match
        cursor.execute(
            """
            SELECT e.id, e.name, d.definition
            FROM entities e
            LEFT JOIN definitions d ON e.id = d.entity_id
            WHERE LOWER(e.name) = LOWER(?) AND e.is_obsolete = 0
            LIMIT ?;
            """,
            (cleaned_query, limit),
        )
        for row in cursor.fetchall():
            if row["id"] not in seen_ids:
                seen_ids.add(row["id"])
                results.append(
                    SearchResult(
                        id=row["id"],
                        name=row["name"],
                        match_type=SearchMatchType.EXACT_NAME,
                        matched_text=row["name"],
                        rank_score=90.0,
                        definition=row["definition"],
                    )
                )
                if len(results) >= limit:
                    return results

        # Tier 3: Prefix Name Match
        cursor.execute(
            """
            SELECT e.id, e.name, d.definition
            FROM entities e
            LEFT JOIN definitions d ON e.id = d.entity_id
            WHERE e.name LIKE ? AND e.is_obsolete = 0
            ORDER BY LENGTH(e.name) ASC
            LIMIT ?;
            """,
            (f"{cleaned_query}%", limit),
        )
        for row in cursor.fetchall():
            if row["id"] not in seen_ids:
                seen_ids.add(row["id"])
                results.append(
                    SearchResult(
                        id=row["id"],
                        name=row["name"],
                        match_type=SearchMatchType.PREFIX_NAME,
                        matched_text=row["name"],
                        rank_score=80.0,
                        definition=row["definition"],
                    )
                )
                if len(results) >= limit:
                    return results

        # Tier 4: Exact / Prefix Synonym Match
        cursor.execute(
            """
            SELECT s.entity_id, e.name, s.synonym, s.scope, d.definition
            FROM synonyms s
            JOIN entities e ON s.entity_id = e.id
            LEFT JOIN definitions d ON e.id = d.entity_id
            WHERE (LOWER(s.synonym) = LOWER(?) OR s.synonym LIKE ?) AND e.is_obsolete = 0
            LIMIT ?;
            """,
            (cleaned_query, f"{cleaned_query}%", limit),
        )
        for row in cursor.fetchall():
            if row["entity_id"] not in seen_ids:
                seen_ids.add(row["entity_id"])
                results.append(
                    SearchResult(
                        id=row["entity_id"],
                        name=row["name"],
                        match_type=SearchMatchType.SYNONYM,
                        matched_text=f"{row['synonym']} ({row['scope']})",
                        rank_score=70.0,
                        definition=row["definition"],
                    )
                )
                if len(results) >= limit:
                    return results

        # Tier 5: FTS5 BM25 Full-Text Match
        # Prepare sanitized FTS query: remove special chars, add prefix asterisk to last term
        fts_tokens = [re.sub(r"[^\w\s]", "", t) for t in cleaned_query.split() if t.strip()]
        if fts_tokens:
            if len(fts_tokens) == 1:
                fts_expr = f'"{fts_tokens[0]}"*'
            else:
                fts_expr = " ".join(f'"{t}"' for t in fts_tokens[:-1]) + f' "{fts_tokens[-1]}"*'

            try:
                cursor.execute(
                    """
                    SELECT f.entity_id, e.name, d.definition, f.rank
                    FROM disease_fts f
                    JOIN entities e ON f.entity_id = e.id
                    LEFT JOIN definitions d ON e.id = d.entity_id
                    WHERE disease_fts MATCH ? AND e.is_obsolete = 0
                    ORDER BY f.rank ASC
                    LIMIT ?;
                    """,
                    (fts_expr, limit),
                )
                for row in cursor.fetchall():
                    if row["entity_id"] not in seen_ids:
                        seen_ids.add(row["entity_id"])
                        # FTS5 rank is negative (lower = better)
                        score = max(10.0, 50.0 - float(row["rank"]))
                        results.append(
                            SearchResult(
                                id=row["entity_id"],
                                name=row["name"],
                                match_type=SearchMatchType.FTS_RANKED,
                                matched_text=row["name"],
                                rank_score=round(score, 2),
                                definition=row["definition"],
                            )
                        )
                        if len(results) >= limit:
                            return results
            except sqlite3.OperationalError:
                # Fallback if FTS query syntax error occurs
                pass

        return results
