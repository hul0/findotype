"""Disease Ontology (doid.json) transactional parser and SQLite importer."""

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from findotype.config import DEFAULT_DOID_URL, SCHEMA_VERSION
from findotype.db.connection import get_connection
from findotype.importers.base import BaseImporter
from findotype.importers.validator import OntologyValidator
from findotype.models.stats import ImportStats
from findotype.ontology.curie import extract_namespace, uri_to_curie
from findotype.ontology.normalizer import (
    parse_alt_ids,
    parse_cross_reference,
    parse_definition,
    parse_subsets,
    parse_synonyms,
)


class DiseaseOntologyImporter(BaseImporter):
    """Parses OBO-JSON doid.json and imports all entities, relationships, and metadata."""

    def validate(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """Validate the dataset file structure."""
        return OntologyValidator.validate_file(file_path)

    def _compute_sha256(self, file_path: Path) -> str:
        """Compute SHA256 checksum of the source file."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def import_dataset(
        self,
        file_path: Union[str, Path],
        db_path: Union[str, Path],
        include_obsolete: bool = False,
        source_url: Optional[str] = None,
    ) -> ImportStats:
        """
        Import doid.json into SQLite inside a single atomic transaction.

        Args:
            file_path: Path to doid.json file
            db_path: Path to target SQLite database
            include_obsolete: Whether to import deprecated/obsolete terms
            source_url: Original download URL for provenance tracking

        Returns:
            ImportStats object with ingestion metrics
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Source file not found: {path}")

        start_time = time.perf_counter()
        source_sha256 = self._compute_sha256(path)

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        graphs = data.get("graphs", [])
        if not graphs:
            raise ValueError("Invalid doid.json: no graphs found in JSON root")

        # 1. First pass: extract ontology metadata and property labels
        main_graph = graphs[0]
        meta_dict = main_graph.get("meta", {})
        basic_props = meta_dict.get("basicPropertyValues", [])

        dataset_version = meta_dict.get("version")
        dataset_date = None
        dataset_title = "Human Disease Ontology"
        dataset_desc = None
        dataset_license = "https://creativecommons.org/publicdomain/zero/1.0/"
        root_term = None
        extra_metadata: Dict[str, str] = {}

        for prop in basic_props:
            if not isinstance(prop, dict):
                continue
            pred = prop.get("pred", "")
            val = str(prop.get("val", ""))

            if "versionInfo" in pred:
                dataset_version = val
            elif "date" in pred:
                dataset_date = val
            elif "title" in pred:
                dataset_title = val
            elif "description" in pred:
                dataset_desc = val
            elif "license" in pred:
                dataset_license = val
            elif "IAO_0000700" in pred:
                root_term = uri_to_curie(val)
            else:
                prop_key = uri_to_curie(pred)
                extra_metadata[prop_key] = val

        # Map of property URI -> human-readable label
        property_labels: Dict[str, str] = {
            "is_a": "is_a",
            "subClassOf": "is_a",
            "http://www.w3.org/2000/01/rdf-schema#subClassOf": "is_a",
        }

        for graph in graphs:
            for node in graph.get("nodes", []):
                if not isinstance(node, dict):
                    continue
                node_type = node.get("type", "")
                node_id = node.get("id", "")
                lbl = node.get("lbl")
                if lbl and (node_type == "PROPERTY" or "RO_" in node_id or "IDO_" in node_id or "IAO_" in node_id):
                    property_labels[node_id] = lbl
                    property_labels[uri_to_curie(node_id)] = lbl

        # 2. Extract and normalize all nodes across all graphs
        entities_batch: List[Tuple] = []
        definitions_batch: List[Tuple] = []
        synonyms_batch: List[Tuple] = []
        xrefs_batch: List[Tuple] = []
        subsets_batch: List[Tuple] = []
        alt_ids_batch: List[Tuple] = []
        fts_batch: List[Tuple] = []

        seen_entities: Set[str] = set()
        obsolete_skipped = 0
        diseases_count = 0

        for graph in graphs:
            for node in graph.get("nodes", []):
                if not isinstance(node, dict) or "id" not in node:
                    continue

                raw_id = node.get("id", "")
                curie_id = uri_to_curie(raw_id)
                if not curie_id:
                    continue

                node_meta = node.get("meta", {})
                is_obsolete = bool(node.get("deprecated", False) or node_meta.get("deprecated", False))

                if is_obsolete and not include_obsolete:
                    obsolete_skipped += 1
                    continue

                if curie_id in seen_entities:
                    continue
                seen_entities.add(curie_id)

                name = node.get("lbl", "").strip() or curie_id
                entity_type = node.get("type", "CLASS")
                namespace = extract_namespace(curie_id)
                if namespace == "DOID":
                    diseases_count += 1

                # Extract comments
                comments = node_meta.get("comments", [])
                comment_str = " ".join(comments) if comments else None

                entities_batch.append((
                    curie_id,
                    raw_id,
                    name,
                    entity_type,
                    namespace,
                    1 if is_obsolete else 0,
                    comment_str,
                ))

                # Definitions
                parsed_def = parse_definition(node_meta.get("definition"))
                def_text = ""
                if parsed_def:
                    def_text = parsed_def.definition
                    definitions_batch.append((
                        curie_id,
                        parsed_def.definition,
                        json.dumps(parsed_def.sources) if parsed_def.sources else None,
                    ))

                # Synonyms
                parsed_syns = parse_synonyms(node_meta.get("synonyms"))
                syn_texts: List[str] = []
                for s in parsed_syns:
                    syn_texts.append(s.synonym)
                    synonyms_batch.append((
                        curie_id,
                        s.synonym,
                        s.scope,
                        s.synonym_type,
                        json.dumps(s.xrefs) if s.xrefs else None,
                    ))

                # Cross-references
                raw_xrefs = node_meta.get("xrefs", [])
                if isinstance(raw_xrefs, list):
                    seen_xrefs = set()
                    for x in raw_xrefs:
                        pxref = parse_cross_reference(x)
                        if pxref:
                            xref_key = (pxref.db, pxref.accession)
                            if xref_key not in seen_xrefs:
                                seen_xrefs.add(xref_key)
                                xrefs_batch.append((
                                    curie_id,
                                    pxref.db,
                                    pxref.accession,
                                    pxref.full_reference,
                                ))

                # Subsets
                parsed_subs = parse_subsets(node_meta.get("subsets"))
                for sub in parsed_subs:
                    subsets_batch.append((curie_id, sub))

                # Alt IDs
                parsed_alts = parse_alt_ids(node_meta.get("basicPropertyValues"))
                for alt in parsed_alts:
                    alt_ids_batch.append((alt, curie_id))

                # Prepare FTS row: only for non-obsolete entities or if requested
                syns_joined = " ".join(syn_texts)
                fts_batch.append((
                    curie_id,
                    name,
                    syns_joined,
                    def_text,
                ))

        # 3. Extract and normalize all edges
        relationships_batch: List[Tuple] = []
        seen_edges: Set[Tuple[str, str, str]] = set()

        for graph in graphs:
            for edge in graph.get("edges", []):
                if not isinstance(edge, dict):
                    continue

                sub_raw = edge.get("sub", "")
                pred_raw = edge.get("pred", "")
                obj_raw = edge.get("obj", "")

                if not sub_raw or not pred_raw or not obj_raw:
                    continue

                sub_curie = uri_to_curie(sub_raw)
                pred_curie = uri_to_curie(pred_raw)
                obj_curie = uri_to_curie(obj_raw)

                # Only link entities that exist in our database
                if sub_curie not in seen_entities or obj_curie not in seen_entities:
                    continue

                edge_key = (sub_curie, pred_curie, obj_curie)
                if edge_key in seen_edges:
                    continue
                seen_edges.add(edge_key)

                pred_label = property_labels.get(
                    pred_raw, property_labels.get(pred_curie, pred_curie)
                )

                meta_json = json.dumps(edge.get("meta")) if edge.get("meta") else None

                relationships_batch.append((
                    sub_curie,
                    pred_curie,
                    pred_label,
                    obj_curie,
                    meta_json,
                ))

        # 4. Open DB and write inside a single atomic transaction
        conn = get_connection(db_path, initialize_schema=True)
        try:
            with conn:
                cursor = conn.cursor()

                # Clean existing tables for deterministic idempotent re-runs
                cursor.execute("DELETE FROM relationships;")
                cursor.execute("DELETE FROM alt_ids;")
                cursor.execute("DELETE FROM subsets;")
                cursor.execute("DELETE FROM cross_references;")
                cursor.execute("DELETE FROM synonyms;")
                cursor.execute("DELETE FROM definitions;")
                cursor.execute("DELETE FROM entities;")
                cursor.execute("DELETE FROM metadata;")
                cursor.execute("DELETE FROM provenance;")
                cursor.execute("DELETE FROM disease_fts;")

                # Batch insert entities
                cursor.executemany(
                    """
                    INSERT INTO entities (id, uri, name, entity_type, namespace, is_obsolete, comment)
                    VALUES (?, ?, ?, ?, ?, ?, ?);
                    """,
                    entities_batch,
                )

                # Batch insert definitions
                cursor.executemany(
                    """
                    INSERT INTO definitions (entity_id, definition, sources_json)
                    VALUES (?, ?, ?);
                    """,
                    definitions_batch,
                )

                # Batch insert synonyms
                cursor.executemany(
                    """
                    INSERT INTO synonyms (entity_id, synonym, scope, synonym_type, xrefs_json)
                    VALUES (?, ?, ?, ?, ?);
                    """,
                    synonyms_batch,
                )

                # Batch insert cross-references
                cursor.executemany(
                    """
                    INSERT INTO cross_references (entity_id, db, accession, full_reference)
                    VALUES (?, ?, ?, ?);
                    """,
                    xrefs_batch,
                )

                # Batch insert subsets
                cursor.executemany(
                    """
                    INSERT INTO subsets (entity_id, subset_name)
                    VALUES (?, ?);
                    """,
                    subsets_batch,
                )

                # Batch insert alt_ids
                cursor.executemany(
                    """
                    INSERT OR REPLACE INTO alt_ids (alt_id, entity_id)
                    VALUES (?, ?);
                    """,
                    alt_ids_batch,
                )

                # Batch insert relationships
                cursor.executemany(
                    """
                    INSERT INTO relationships (subject_id, predicate_id, predicate_label, object_id, meta_json)
                    VALUES (?, ?, ?, ?, ?);
                    """,
                    relationships_batch,
                )

                # Populate FTS5 index
                cursor.executemany(
                    """
                    INSERT INTO disease_fts (entity_id, name, synonyms, definition)
                    VALUES (?, ?, ?, ?);
                    """,
                    fts_batch,
                )

                duration = time.perf_counter() - start_time
                imported_at = datetime.now(timezone.utc).isoformat()

                stats = ImportStats(
                    entities_count=len(entities_batch),
                    diseases_count=diseases_count,
                    synonyms_count=len(synonyms_batch),
                    definitions_count=len(definitions_batch),
                    xrefs_count=len(xrefs_batch),
                    relationships_count=len(relationships_batch),
                    subsets_count=len(subsets_batch),
                    alt_ids_count=len(alt_ids_batch),
                    obsolete_skipped=obsolete_skipped,
                    duration_seconds=round(duration, 3),
                )

                stats_dict = {
                    "entities_count": stats.entities_count,
                    "diseases_count": stats.diseases_count,
                    "synonyms_count": stats.synonyms_count,
                    "definitions_count": stats.definitions_count,
                    "xrefs_count": stats.xrefs_count,
                    "relationships_count": stats.relationships_count,
                    "subsets_count": stats.subsets_count,
                    "alt_ids_count": stats.alt_ids_count,
                    "obsolete_skipped": stats.obsolete_skipped,
                    "duration_seconds": stats.duration_seconds,
                }

                # Record provenance
                cursor.execute(
                    """
                    INSERT INTO provenance (
                        dataset_name, dataset_version, source_uri, source_sha256,
                        schema_version, imported_at, stats_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        "Disease Ontology",
                        dataset_version,
                        source_url or DEFAULT_DOID_URL,
                        source_sha256,
                        SCHEMA_VERSION,
                        imported_at,
                        json.dumps(stats_dict),
                    ),
                )

                # Record key-value metadata
                metadata_items = [
                    ("title", dataset_title),
                    ("description", dataset_desc or ""),
                    ("version", dataset_version or ""),
                    ("date", dataset_date or ""),
                    ("license", dataset_license),
                    ("root_term", root_term or "DOID:4"),
                    ("source_sha256", source_sha256),
                    ("schema_version", SCHEMA_VERSION),
                    ("imported_at", imported_at),
                ]
                for k, v in extra_metadata.items():
                    metadata_items.append((f"prop:{k}", v))

                cursor.executemany(
                    "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?);",
                    metadata_items,
                )

            # Optimize SQLite database after full batch insertion
            conn.execute("PRAGMA optimize;")

        finally:
            conn.close()

        return stats
