# Findotype Architecture & Design Guide

**Author**: Rupam Ghosh  
**License**: GNU AGPL-3.0-or-later  

Findotype is a modular, high-performance offline disease ontology backend and search engine engineered for zero-runtime external dependencies, atomic transactions, microsecond direct lookups, and multi-tiered full-text search.

---

## 1. High-Level Architecture Diagram

```text
                               +-----------------------------------+
                               | Upstream doid.json / OBO-JSON     |
                               +-----------------+-----------------+
                                                 |
                                                 v
                               +-----------------------------------+
                               |     OntologyValidator (AST)       |
                               +-----------------+-----------------+
                                                 |
                                                 v
                               +-----------------------------------+
                               |   DiseaseOntologyImporter         |
                               |  - SHA256 & Provenance Tagging   |
                               |  - URI <-> CURIE Normalizer      |
                               |  - Synonym & XRef Normalization  |
                               +-----------------+-----------------+
                                                 |
                                                 v (Atomic Transaction)
+----------------------------------------------------------------------------------------------------+
|                                    Indexed SQLite Database (WAL)                                   |
|                                                                                                    |
|  +----------------+  +----------------+  +----------------+  +----------------+  +---------------+ |
|  |    entities    |  |  definitions   |  |    synonyms    |  |cross_references|  |  subsets/slims| |
|  +----------------+  +----------------+  +----------------+  +----------------+  +---------------+ |
|  +----------------+  +----------------+  +----------------+  +----------------+  +---------------+ |
|  | relationships  |  |    alt_ids     |  |   provenance   |  |    metadata    |  |  disease_fts  | |
|  +----------------+  +----------------+  +----------------+  +----------------+  +---------------+ |
+------------------------------------------------+---------------------------------------------------+
                                                 |
                                                 v
                               +-----------------------------------+
                               |      Repositories & Services      |
                               |  - DiseaseRepository (FTS5 / CTE) |
                               |  - MetadataRepository             |
                               |  - Findotype (Public Facade)      |
                               +--------+-----------------+--------+
                                        |                 |
                         +--------------+                 +--------------+
                         |                                               |
                         v                                               v
        +----------------------------------+            +----------------------------------+
        |        Python Library API        |            |            CLI Engine            |
        |  from findotype import Findotype |            |   python -m findotype ...        |
        +----------------------------------+            +----------------------------------+
```

---

## 2. Component Responsibilities

| Component | Path | Responsibility |
| :--- | :--- | :--- |
| **`models`** | [`src/findotype/models/`](/src/findotype/models/) | Immutable typed dataclasses (`Disease`, `Synonym`, `Definition`, `CrossReference`, `Relationship`, `Provenance`, `SearchResult`, `DatabaseStats`). |
| **`db`** | [`src/findotype/db/`](/src/findotype/db/) | DDL schema, performance PRAGMAs (WAL, memory cache, memory temp store), FTS5 virtual table, and connection management. |
| **`ontology`** | [`src/findotype/ontology/`](/src/findotype/ontology/) | Bidirectional CURIE converters (`uri_to_curie`, `curie_to_uri`), synonym scope normalizers, cross-reference parsers. |
| **`importers`** | [`src/findotype/importers/`](/src/findotype/importers/) | Strict input validation, cryptographic hashing, and transactional batch loading of OBO-JSON graphs. |
| **`repositories`**| [`src/findotype/repositories/`](/src/findotype/repositories/) | Data access layer: indexed Lookups, recursive CTE graph traversals (`get_ancestors`, `get_descendants`), and multi-tiered FTS5 searches. |
| **`services`** | [`src/findotype/services/`](/src/findotype/services/) | High-level `Findotype` public facade with context manager lifecycle. |
| **`cli`** | [`src/findotype/cli/`](/src/findotype/cli/) | CLI commands (`download`, `validate`, `import`, `stats`, `search`, `inspect`) with formatted tables and `--json` support. |

---

## 3. Database Schema Design

### Unified Extensible Entity Model
Rather than a single flat table or disease-specific column assumptions, Findotype uses a generalized relational ontology model:

1. **`entities`**:
   - Stores terms across all namespaces (`DOID`, `CHEBI`, `UBERON`, `HP`, `NCBITaxon`, `SYMP`, `SO`, etc.).
   - Indexed on `id`, `name`, `namespace`, and `is_obsolete`.
2. **`definitions`**:
   - Formal descriptions and source citation arrays (PMID, URLs, ISBN).
3. **`synonyms`**:
   - Scope-categorized synonyms (`EXACT`, `NARROW`, `BROAD`, `RELATED`), types, and citation xrefs.
4. **`cross_references`**:
   - Split database key and accession (e.g. `MESH` / `D006394`, `ICD10CM` / `A15`) for fast indexed prefix and reverse lookups.
5. **`subsets`**:
   - Subsets/slims (e.g. `DO_cancer_slim`, `DO_rare_slim`).
6. **`alt_ids`**:
   - Mapping table resolving obsolete/merged IDs to active canonical IDs.
7. **`relationships`**:
   - Directed typed graph edges (`is_a`, `IDO:0000664` has material basis in, `RO:0002452` has substance added, `RO:0002200` has phenotype, `RO:0001022` has allergic trigger, etc.) with human-readable labels.
8. **`disease_fts` (SQLite FTS5)**:
   - Full-text search virtual table indexed with `unicode61 remove_diacritics 2`.
9. **`provenance` & `metadata`**:
   - Cryptographic SHA-256 source verification, ontology release version, import timestamps, and schema versioning.

---

## 4. Multi-Tiered Search Strategy

When querying `search_diseases(query)`:

1. **Tier 1 (Exact ID / Alt ID)**: Direct index lookup on primary CURIE (`DOID:0001816`), numeric string (`0001816`), or merged alternative ID (`DOID:267`).
2. **Tier 2 (Exact Name)**: Case-insensitive match on `entities.name`.
3. **Tier 3 (Prefix Name)**: Autocomplete-style match on `entities.name LIKE 'query%'`.
4. **Tier 4 (Synonym Match)**: Case-insensitive and prefix match on `synonyms.synonym`.
5. **Tier 5 (FTS5 BM25 Full-Text)**: Tokenized multi-word search across entity names, synonyms, and definition text with BM25 score ranking.

---

## 5. Adding Future Ontology Datasets (HPO, MONDO, Orphanet)

Findotype's relational schema is ontology-agnostic. To add support for new ontologies:

1. Subclass [`BaseImporter`](/src/findotype/importers/base.py) in `src/findotype/importers/<dataset>.py` (e.g. `HpoImporter`, `MondoImporter`, `OrphanetImporter`).
2. Register the prefix in [`src/findotype/ontology/curie.py`](/src/findotype/ontology/curie.py).
3. Import into the common `entities`, `relationships`, `synonyms`, and `cross_references` tables with the appropriate `namespace` (e.g. `HP`, `MONDO`, `ORPHA`).
4. Cross-ontology relationships will resolve automatically through unified foreign keys.
