"""Repository for provenance tracking, dataset metadata, and database metrics."""

import json
import sqlite3
from pathlib import Path
from typing import Dict, Optional

from findotype.models.provenance import DatasetMetadata, Provenance
from findotype.models.stats import DatabaseStats


class MetadataRepository:
    """Provides access to data provenance, dataset release information, and metrics."""

    def __init__(self, connection: sqlite3.Connection):
        self.conn = connection

    def get_provenance(self) -> Optional[Provenance]:
        """Retrieve the latest import provenance record."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT dataset_name, dataset_version, source_uri, source_sha256,
                   schema_version, imported_at, stats_json
            FROM provenance
            ORDER BY id DESC
            LIMIT 1;
            """
        )
        row = cursor.fetchone()
        if not row:
            return None

        stats = json.loads(row["stats_json"]) if row["stats_json"] else {}
        return Provenance(
            dataset_name=row["dataset_name"],
            dataset_version=row["dataset_version"],
            source_uri=row["source_uri"],
            source_sha256=row["source_sha256"],
            schema_version=row["schema_version"],
            imported_at=row["imported_at"],
            stats=stats,
        )

    def get_metadata(self) -> DatasetMetadata:
        """Retrieve all key-value metadata stored during import."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT key, value FROM metadata;")
        meta_dict = {row["key"]: row["value"] for row in cursor.fetchall()}

        extra = {}
        for k, v in meta_dict.items():
            if k.startswith("prop:"):
                extra[k[5:]] = v

        return DatasetMetadata(
            title=meta_dict.get("title"),
            description=meta_dict.get("description"),
            version=meta_dict.get("version"),
            date=meta_dict.get("date"),
            license=meta_dict.get("license"),
            root_term=meta_dict.get("root_term"),
            extra_properties=extra,
        )

    def get_database_stats(self, db_path: Optional[Path] = None) -> DatabaseStats:
        """Calculate summary counts and metrics for all tables."""
        cursor = self.conn.cursor()

        def _count(table: str, condition: str = "") -> int:
            sql = f"SELECT COUNT(*) FROM {table} {condition};"
            cursor.execute(sql)
            return cursor.fetchone()[0]

        total_entities = _count("entities")
        total_diseases = _count("entities", "WHERE namespace = 'DOID' OR id LIKE 'DOID:%'")
        total_synonyms = _count("synonyms")
        total_definitions = _count("definitions")
        total_xrefs = _count("cross_references")
        total_relationships = _count("relationships")
        total_subsets = _count("subsets")
        total_alt_ids = _count("alt_ids")

        # Breakdown by namespace
        cursor.execute(
            """
            SELECT namespace, COUNT(*) as cnt
            FROM entities
            GROUP BY namespace
            ORDER BY cnt DESC;
            """
        )
        namespaces = {row["namespace"] or "UNKNOWN": row["cnt"] for row in cursor.fetchall()}

        # Top relationship predicates
        cursor.execute(
            """
            SELECT COALESCE(predicate_label, predicate_id) as pred, COUNT(*) as cnt
            FROM relationships
            GROUP BY pred
            ORDER BY cnt DESC
            LIMIT 10;
            """
        )
        top_predicates = {row["pred"]: row["cnt"] for row in cursor.fetchall()}

        # Top cross reference databases
        cursor.execute(
            """
            SELECT db, COUNT(*) as cnt
            FROM cross_references
            GROUP BY db
            ORDER BY cnt DESC
            LIMIT 10;
            """
        )
        top_xrefs = {row["db"]: row["cnt"] for row in cursor.fetchall()}

        db_size_bytes = 0
        if db_path and Path(db_path).exists():
            db_size_bytes = Path(db_path).stat().st_size
        else:
            # Fallback to page_count * page_size
            try:
                cursor.execute("PRAGMA page_count;")
                pages = cursor.fetchone()[0]
                cursor.execute("PRAGMA page_size;")
                page_size = cursor.fetchone()[0]
                db_size_bytes = pages * page_size
            except Exception:
                db_size_bytes = 0

        return DatabaseStats(
            total_entities=total_entities,
            total_diseases=total_diseases,
            total_synonyms=total_synonyms,
            total_definitions=total_definitions,
            total_xrefs=total_xrefs,
            total_relationships=total_relationships,
            total_subsets=total_subsets,
            total_alt_ids=total_alt_ids,
            db_size_bytes=db_size_bytes,
            entity_namespaces=namespaces,
            top_predicates=top_predicates,
            top_xref_databases=top_xrefs,
        )
