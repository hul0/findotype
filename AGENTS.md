# Findotype Agent Guidelines

This repository contains **Findotype**, an offline SQLite search engine and medical ontology toolkit for the Disease Ontology and Human Phenotype Ontology.

## Architecture

* `src/findotype/models/`: Immutable dataclasses for diseases, synonyms, definitions, cross-references, phenotypes, and graph edges.
* `src/findotype/db/`: Schema DDL, SQLite performance PRAGMAs (WAL mode, memory temp store), FTS5 virtual tables, and connection managers.
* `src/findotype/ontology/`: Bidirectional URI <-> CURIE converters and field normalizers.
* `src/findotype/importers/`: Input validators and transactional batch ingestion engines (DOID & HPO).
* `src/findotype/repositories/`: Data access layer for indexed queries, recursive CTE traversals, and multi-tiered FTS5 searches.
* `src/findotype/services/`: High-level `Findotype` public API facade, symptom parser, and phenotype matcher.
* `src/findotype/server/`: Zero-dependency HTTP server, monochrome human web interface, OpenAPI 3.0 generator, and Swagger UI.
* `src/findotype/cli/`: CLI entrypoints (`serve`, `download-db`, `download`, `validate`, `import`, `import-hpo`, `stats`, `search`, `inspect`, `match`).

## Rules for Modification

1. Never introduce heavy runtime external dependencies (keep runtime pure standard library + sqlite3).
2. Maintain parameterization for all SQL queries.
3. Keep code under GNU AGPL-3.0-or-later; keep third-party data under their respective open licenses.
4. Ensure all tests in `tests/` pass with `PYTHONPATH=src python3 -m unittest discover -s tests -v`.
