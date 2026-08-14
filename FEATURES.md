# Findotype Feature Roadmap

A comprehensive roadmap of potential capabilities to expand the Findotype Python library and CLI into an enterprise-grade medical ontology engine.

---

## 1. Clinical & Phenotypic Intelligence

- [ ] Add HPO DAG semantic similarity algorithms (Resnik, Lin, Schlicker Information Content similarity) between patient phenotype profiles and diseases.
- [ ] Implement negative phenotype filtering (`"fever, cough, NO rash"`) to actively penalize and exclude diseases featuring absent symptoms.
- [ ] Support age-of-onset phenotype weighting (e.g., congenital, pediatric, adult, late-onset) using HPO onset terms (`HP:0003577`).
- [ ] Support mode-of-inheritance filtering (e.g., autosomal dominant, autosomal recessive, X-linked) using HPO inheritance terms (`HP:0000005`).
- [ ] Implement symptom severity/frequency weighting (e.g., frequent >79%, occasional 30-79%, very rare <30%) from HPO annotations.
- [ ] Add phenotypic differential diagnosis report generator comparing overlapping and distinguishing symptoms between 2+ candidate diseases.
- [ ] Build clinical text entity recognition (NER) pipeline capable of parsing multi-paragraph discharge summaries and clinical case notes into HPO profiles.
- [ ] Support temporal symptom progression modeling (e.g., symptom A followed by symptom B within X days/weeks).

---

## 2. Ontology Graph & Hierarchy Traversals

- [ ] Implement Lowest Common Ancestor (LCA) query between any arbitrary set of disease or phenotype entities.
- [ ] Add shortest path and semantic distance calculator between two arbitrary nodes across any relationship predicate.
- [ ] Build a precomputed Transitive Closure table builder for sub-millisecond zero-hop ancestor/descendant lookups.
- [ ] Support custom predicate traversal chains (e.g., follow `derives_from` followed by `has_material_basis_in`).
- [ ] Implement subgraph extraction utility to isolate specific disease branches (e.g., "all cardiovascular diseases and their phenotypes").
- [ ] Add cycle detection and graph validation tools for multi-ontology directed acyclic graphs.
- [ ] Generate ASCII hierarchy trees and visual tree branches directly in CLI and library returns.

---

## 3. Multi-Ontology & Knowledge Base Expansion

- [ ] Build transactional importer for MONDO Disease Ontology (`mondo.json`) with cross-species mappings.
- [ ] Build transactional importer for Orphanet Rare Diseases dataset (ORDO / `orphanet.json`).
- [ ] Build disease-to-gene association ingestion engine (OMIM, ClinVar, and NCBI Gene mappings).
- [ ] Build disease-to-drug indication and contraindication ingestion engine (DrugCentral / ChEMBL / RxNorm).
- [ ] Build MedDRA-to-HPO and ICD-10-to-DOID synonym crosswalk mapper for standardized clinical coding.
- [ ] Build anatomical mapping layer using UBERON ontology to enable organ/system-based disease queries (e.g., "all diseases affecting liver").
- [ ] Add infectious agent taxonomy explorer using NCBITaxon ontology to query diseases by pathogen genus/family/species.

---

## 4. Advanced Search & Text Exploration

- [ ] Support boolean search syntax (`AND`, `OR`, `NOT`, exact quotes) across FTS5 tables with parenthetical grouping.
- [ ] Add fuzzy matching with Damerau-Levenshtein distance and spelling auto-correction suggestions for mispelled clinical queries.
- [ ] Implement medical acronym and abbreviation expander (e.g., "COPD" -> "chronic obstructive pulmonary disease", "T1D" -> "type 1 diabetes").
- [ ] Add batch search mode accepting CSV/TSV/JSONL files containing thousands of queries with parallel multi-core execution.
- [ ] Add regex pattern matching across cross-references, accession numbers, and synonym text.
- [ ] Support faceted search filtering by namespace, subset/slim, database xref, and relationship type simultaneously.

---

## 5. Developer API & Framework Ergonomics

- [ ] Implement asynchronous client (`AsyncFindotype`) with `aiosqlite` support for high-concurrency FastAPI/Tornado backends.
- [ ] Add in-memory LRU caching layer for hot entity lookups, synonym lookups, and hierarchy traversals.
- [ ] Add direct export of query results and entity collections to Pandas and Polars DataFrames (`engine.to_pandas(...)`, `engine.to_polars(...)`).
- [ ] Provide entity diff utility (`engine.diff_entities(id1, id2)`) highlighting shared and divergent synonyms, parents, xrefs, and definitions.
- [ ] Add raw parameterized SQL execution helper (`engine.raw_query(...)`) returning typed dataclasses or dictionaries.
- [ ] Add streaming cursor generators (`engine.iter_diseases(...)`, `engine.iter_phenotypes(...)`) for memory-efficient iteration over millions of rows.
- [ ] Create Pydantic v2 model compatibility bridge for seamless validation in web frameworks.

---

## 6. Data Export, Serialization & Interoperability

- [ ] Add FHIR Condition and PhenotypicFeature resource exporter (`engine.to_fhir(...)`) adhering to HL7 FHIR R4/R5 specifications.
- [ ] Support bulk export to Apache Parquet, Arrow IPC, and DuckDB formats for big-data analytical pipelines.
- [ ] Add serialization to OBO Flat File format (`.obo`) and RDF/OWL Turtle format (`.ttl`).
- [ ] Add GraphML and DOT export for rendering graph relationships in Gephi, Graphviz, or Cytoscape.
- [ ] Support compressed SQLite database export with zstandard / gzip dictionary optimization for compact distribution.

---

## 7. CLI Enhancements & Tooling

- [ ] Add interactive Terminal User Interface (TUI) with fuzzy search, hierarchy navigation, and live symptom typing.
- [ ] Add `findotype diff <ID1> <ID2>` CLI subcommand comparing two diseases side-by-side with color-coded diffs.
- [ ] Add `findotype graph <ID> --depth 3 --format svg/png/ascii` CLI subcommand to render graphical relationship diagrams.
- [ ] Add `findotype export --format parquet/csv/jsonl/fhir` CLI subcommand to dump custom slices of the knowledge base.
- [ ] Add `findotype doctor` CLI health-check subcommand verifying database integrity, FTS indexes, pragma performance, and orphaned records.
- [ ] Add `findotype serve --port 8000` CLI subcommand launching an instant lightweight offline REST/JSON API server.
- [ ] Add shell completion generator (`findotype completion bash/zsh/fish`) with auto-complete for commands and DOID/HP CURIEs.

---

## 8. Database Administration & Optimization

- [ ] Support zero-disk in-memory database loading (`Findotype(":memory:")`) by pre-hydrating SQLite schema and datasets.
- [ ] Add `findotype db vacuum` and `findotype db reindex` commands for automated database defragmentation and optimization.
- [ ] Support multi-threaded concurrent transactional batch imports with SQLite chunked wal checkpoints.
- [ ] Support custom SQLite extensions loading (e.g., `sqlite-vss` for vector embeddings, `spellfix1` for phonetic search).
- [ ] Add database snapshot and version rollback mechanism to safely test dataset upgrades.
