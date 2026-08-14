"""Database schema definition, DDL statements, FTS5 virtual tables, and indexes."""

SCHEMA_DDL = """
-- Provenance of imported datasets
CREATE TABLE IF NOT EXISTS provenance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dataset_name TEXT NOT NULL,
    dataset_version TEXT,
    release_date TEXT,
    license TEXT,
    root_term TEXT,
    source_uri TEXT,
    source_sha256 TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    imported_at TEXT NOT NULL,
    stats_json TEXT
);

-- General dataset metadata key-values
CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Core ontology entities (diseases, phenotypes, anatomical structures, properties)
CREATE TABLE IF NOT EXISTS entities (
    id TEXT PRIMARY KEY,
    uri TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    entity_type TEXT NOT NULL DEFAULT 'CLASS',
    namespace TEXT,
    is_obsolete INTEGER NOT NULL DEFAULT 0,
    comment TEXT
);

-- Textual definitions
CREATE TABLE IF NOT EXISTS definitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id TEXT NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    definition TEXT NOT NULL,
    sources_json TEXT
);

-- Synonyms with scopes (EXACT, NARROW, BROAD, RELATED)
CREATE TABLE IF NOT EXISTS synonyms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id TEXT NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    synonym TEXT NOT NULL,
    scope TEXT NOT NULL DEFAULT 'RELATED',
    synonym_type TEXT,
    xrefs_json TEXT
);

-- External database cross-references (MESH, ICD10, OMIM, UMLS, NCI, etc.)
CREATE TABLE IF NOT EXISTS cross_references (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id TEXT NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    db TEXT NOT NULL,
    accession TEXT NOT NULL,
    full_reference TEXT NOT NULL
);

-- Ontology subsets and slims (e.g. DO_cancer_slim)
CREATE TABLE IF NOT EXISTS subsets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id TEXT NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    subset_name TEXT NOT NULL
);

-- Alternative / merged identifiers (e.g. merged DOID terms)
CREATE TABLE IF NOT EXISTS alt_ids (
    alt_id TEXT PRIMARY KEY,
    entity_id TEXT NOT NULL REFERENCES entities(id) ON DELETE CASCADE
);

-- Directed typed relationships between ontology entities
CREATE TABLE IF NOT EXISTS relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id TEXT NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    predicate_id TEXT NOT NULL,
    predicate_label TEXT,
    object_id TEXT NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    meta_json TEXT
);

-- SQLite FTS5 Virtual Table for full-text search across names, synonyms, and definitions
CREATE VIRTUAL TABLE IF NOT EXISTS disease_fts USING fts5(
    entity_id UNINDEXED,
    name,
    synonyms,
    definition,
    tokenize='unicode61 remove_diacritics 2'
);

-- Performance Indexes
CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name);
CREATE INDEX IF NOT EXISTS idx_entities_ns ON entities(namespace);
CREATE INDEX IF NOT EXISTS idx_entities_obs ON entities(is_obsolete);

CREATE INDEX IF NOT EXISTS idx_definitions_entity ON definitions(entity_id);

CREATE INDEX IF NOT EXISTS idx_synonyms_entity ON synonyms(entity_id);
CREATE INDEX IF NOT EXISTS idx_synonyms_text ON synonyms(synonym);

CREATE INDEX IF NOT EXISTS idx_xrefs_entity ON cross_references(entity_id);
CREATE INDEX IF NOT EXISTS idx_xrefs_db_acc ON cross_references(db, accession);
CREATE INDEX IF NOT EXISTS idx_xrefs_full ON cross_references(full_reference);

CREATE INDEX IF NOT EXISTS idx_subsets_entity ON subsets(entity_id);
CREATE INDEX IF NOT EXISTS idx_subsets_name ON subsets(subset_name);

CREATE INDEX IF NOT EXISTS idx_alt_ids_entity ON alt_ids(entity_id);

CREATE INDEX IF NOT EXISTS idx_rel_sub_pred ON relationships(subject_id, predicate_id);
CREATE INDEX IF NOT EXISTS idx_rel_obj_pred ON relationships(object_id, predicate_id);
CREATE INDEX IF NOT EXISTS idx_rel_pred ON relationships(predicate_id);

-- Views for developer convenience
CREATE VIEW IF NOT EXISTS v_diseases AS
SELECT 
    e.id,
    e.uri,
    e.name,
    e.namespace,
    e.is_obsolete,
    e.comment,
    d.definition,
    d.sources_json AS definition_sources
FROM entities e
LEFT JOIN definitions d ON e.id = d.entity_id
WHERE e.namespace = 'DOID' OR e.id LIKE 'DOID:%';

CREATE VIEW IF NOT EXISTS v_relationships AS
SELECT 
    r.id,
    r.subject_id,
    s.name AS subject_name,
    r.predicate_id,
    r.predicate_label,
    r.object_id,
    o.name AS object_name,
    r.meta_json
FROM relationships r
JOIN entities s ON r.subject_id = s.id
JOIN entities o ON r.object_id = o.id;
"""


def init_db_schema(conn) -> None:
    """Initialize all tables, indexes, views, and virtual tables in the database."""
    conn.executescript(SCHEMA_DDL)
