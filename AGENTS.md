# Findotype Agent Guidelines

This repository contains **Findotype**, a production-grade Python backend and offline SQLite search engine for the Disease Ontology.

## Architecture

* `src/findotype/models/`: Immutable dataclasses for diseases, synonyms, definitions, cross-references, and graph edges.
* `src/findotype/db/`: Schema DDL, SQLite performance PRAGMAs (WAL mode, memory temp store), FTS5 virtual tables, and connection managers.
* `src/findotype/ontology/`: Bidirectional URI <-> CURIE converters and field normalizers.
* `src/findotype/importers/`: Input validators and transactional batch ingestion engine.
* `src/findotype/repositories/`: Data access layer for indexed queries, recursive CTE traversals, and multi-tiered FTS5 searches.
* `src/findotype/services/`: High-level `Findotype` public API facade.
* `src/findotype/cli/`: CLI entrypoints (`download`, `validate`, `import`, `stats`, `search`, `inspect`).

## Rules for Modification

1. Never introduce heavy runtime external dependencies (keep runtime pure standard library + sqlite3).
2. Maintain parameterization for all SQL queries.
3. Keep code under GNU AGPL-3.0-or-later; keep third-party data under CC0 1.0.
4. Ensure all tests in `tests/` pass with `PYTHONPATH=src python3 -m unittest discover -s tests -v`.
