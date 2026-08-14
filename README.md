# Findotype

[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL%203.0-blue.svg)](LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/python-3.10+-brightgreen.svg)](pyproject.toml)
[![Data License: CC0-1.0](https://img.shields.io/badge/Data%20License-CC0%201.0-lightgrey.svg)](THIRD_PARTY.md)

**Findotype** is a high-performance, modular, and production-ready Python backend and library for offline disease ontology exploration, querying, and search.

Engineered with **zero runtime external dependencies** (using pure Python standard library and SQLite), Findotype converts raw OBO-JSON datasets (such as `doid.json`) into an indexed, normalized relational SQLite database with full SQLite FTS5 search, sub-millisecond lookups, and graph traversals.

---

## Key Features

* **Zero External Runtime Dependencies**: Powered entirely by the Python 3.10+ standard library and SQLite3.
* **High-Performance SQLite Engine**: Configured with WAL mode, 64 MB page cache, 256 MB memory-mapped I/O, and cascading foreign keys.
* **Full-Text Search (FTS5)**: Multi-tiered ranking (Exact ID -> Name -> Synonyms -> BM25 Definitions) with unicode normalization and prefix autocomplete.
* **Hierarchy & Graph Traversals**: Direct 1-hop parent/child lookups as well as recursive multi-hop ancestor/descendant CTE queries with cycle protection.
* **Cryptographic Data Provenance**: Tracks SHA-256 dataset hashes, release dates, import timestamps, source URLs, and schema versions.
* **Transactional & Idempotent**: Ingestion runs inside an atomic SQLite transaction, ensuring safe re-runs and zero database corruption.
* **Extensible Schema**: Designed to support future multi-ontology datasets (HPO, MONDO, Orphanet, etc.).
* **Ergonomic CLI & API**: Rich interactive CLI outputs and typed Python dataclass objects.

---

## Architecture Overview

```text
doid.json / OBO-JSON
        ↓
OntologyValidator (Schema & Structural AST Checking)
        ↓
DiseaseOntologyImporter (SHA-256 + CURIE & Synonym Normalization)
        ↓  (Atomic Transaction)
SQLite Database (WAL Mode + FTS5 Indexing + Performance Pragmas)
        ↓
Repository & Service Layer (Findotype Python API & CLI)
```

---

## Installation

Findotype requires **Python 3.10+**.

```bash
# Clone the repository
git clone https://github.com/your-username/findotype.git
cd findotype

# Install in editable mode
pip install -e .

# Or with dev dependencies (pytest)
pip install -e ".[dev]"
```

---

## CLI Usage

Findotype provides a comprehensive CLI for all dataset and search operations:

### 1. Download Disease Ontology
```bash
python -m findotype download --output assets/DO/doid.json
```

### 2. Validate Dataset
```bash
python -m findotype validate assets/DO/doid.json
```

### 3. Ingest into SQLite Database
```bash
python -m findotype import assets/DO/doid.json
```

### 4. Ingest Human Phenotype Ontology (HPO)
```bash
python -m findotype import-hpo assets/hp-base.json
```

### 5. Match Clinical Symptoms to Diseases
```bash
# Match natural language clinical symptoms with match percentage
python -m findotype match "I have fever, cough, nausea"

# Machine-readable JSON output
python -m findotype match "I have fever, cough, nausea" --json
```

### 6. Inspect Database Summary & Provenance
```bash
python -m findotype stats
```

### 7. Multi-Tiered Search
```bash
# Human-readable search
python -m findotype search "tuberculosis"

# Machine-readable JSON output
python -m findotype search "angiosarcoma" --json
```

### 8. Inspect Disease Details
```bash
python -m findotype inspect DOID:0001816
```

### 9. Launch Monochrome Web UI & Swagger REST API
```bash
python -m findotype serve --port 8000
```
* **Web UI (Human Interface)**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/) (Strict monochrome aesthetic, zero gradients, clinical symptom matcher, disease search, deep inspector, and knowledge base metrics).
* **Interactive Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* **OpenAPI 3.0 Specification**: [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json)

---

## Python API Usage

```python
from findotype import Findotype

# Initialize the engine (connects to local SQLite database)
engine = Findotype("data/disease_ontology.db")

# 1. Clinical Symptom & Phenotype Disease Matching
# Takes natural language text or structured lists and calculates match %
matches = engine.match_phenotypes("I have fever, cough, nausea", limit=5)
for m in matches:
    matched_names = ", ".join(s.matched_term_name for s in m.matched_symptoms)
    print(f"[{m.disease_id}] {m.disease_name} -> Match: {m.match_percentage}% (Matched: {matched_names})")

# 2. Direct Disease Lookup (by DOID, numeric ID, or Alt ID)
disease = engine.get_disease("DOID:0001816")
print(disease.name)
# 'angiosarcoma'

# 3. Synonyms and Cross References
for synonym in disease.synonyms:
    print(f"[{synonym.scope}] {synonym.synonym}")

for xref in disease.cross_references:
    print(f"{xref.db}: {xref.accession}")

# 4. Multi-Tiered Full-Text Search
results = engine.search_diseases("angiosarcoma", limit=10)
for res in results:
    print(f"[{res.id}] {res.name} (Match: {res.match_type.value}, Rank: {res.rank_score})")

# 5. Ontology Hierarchy & Traversals
parents = engine.get_parents("DOID:0001816")
children = engine.get_children("DOID:175")
ancestors = engine.get_ancestors("DOID:0001816")  # Recursive CTE up to root
descendants = engine.get_descendants("DOID:175") # Recursive CTE down hierarchy

# 6. Connected Graph Relationships
relationships = engine.get_relationships("DOID:0001816")
for rel in relationships:
    print(f"--[{rel.predicate_label}]--> {rel.object_id} ({rel.object_name})")

# 7. Data Provenance & Release Info
prov = engine.get_provenance()
print(f"Release: {prov.dataset_version} | Imported: {prov.imported_at} | SHA256: {prov.source_sha256}")

# Close connection
engine.close()
```

You can also use context managers:
```python
with Findotype("data/disease_ontology.db") as engine:
    disease = engine.get_disease("DOID:399")
    print(disease.name)
```

---

## Benchmark & Performance

Benchmark results against the full Disease Ontology dataset (24 MB JSON / 25.5 MB SQLite DB):

| Operation | Mean Latency | P95 Latency | Description |
| :--- | :--- | :--- | :--- |
| **Direct DOID Lookup** | **0.064 ms** | 0.073 ms | Instant indexed B-tree retrieval |
| **Recursive Ancestor CTE** | **0.063 ms** | 0.109 ms | Multi-hop graph traversal to root |
| **Multi-Tiered FTS Search**| **22.4 ms** | 26.2 ms | Exact, prefix, synonym & FTS5 rank |
| **Full Import Pipeline** | **1.45 s** | N/A | Full parse, validation & batch insert |

Run the benchmark on your machine:
```bash
PYTHONPATH=src python3 scripts/benchmark.py
```

---

## Running the Test Suite

```bash
# Run using standard unittest
PYTHONPATH=src python3 -m unittest discover -s tests -v

# Or using pytest (if installed)
pytest -v
```

---

## Database Schema

```text
entities            : All ontology terms across namespaces (DOID, CHEBI, UBERON, HP, etc.)
definitions         : Formal definitions and citation sources
synonyms            : EXACT, NARROW, BROAD, and RELATED synonyms
cross_references    : Normalized external database cross-references (MESH, ICD10CM, OMIM, UMLS, etc.)
subsets             : Ontology slims (e.g. DO_cancer_slim, DO_rare_slim)
alt_ids             : Merged/alternative secondary IDs mapped to canonical entities
relationships       : Directed typed graph edges with human-readable predicate labels
provenance          : Cryptographic hash, source URI, import timestamp, and schema version
metadata            : Ontology-level key-values (title, description, license, root term)
disease_fts         : SQLite FTS5 virtual table for high-speed full-text queries
```

---

## Adding Future Ontology Datasets

Findotype's relational schema is ontology-agnostic. To add support for new ontologies:

1. Subclass [`BaseImporter`](file:///home/johan/CRINE/findotype/src/findotype/importers/base.py) in `src/findotype/importers/<dataset>.py`.
2. Register any custom CURIE prefixes in [`src/findotype/ontology/curie.py`](file:///home/johan/CRINE/findotype/src/findotype/ontology/curie.py).
3. Ingest into the common `entities`, `relationships`, `synonyms`, and `cross_references` tables with the appropriate namespace.

---

## Feature Roadmap

See [`FEATURES.md`](FEATURES.md) for a comprehensive list of planned capabilities across clinical intelligence, graph traversals, data formats, developer ergonomics, and CLI tooling.

---

## Licensing

* **Source Code**: [GNU AGPL-3.0-or-later](LICENSE).
* **Disease Ontology Data**: [Creative Commons CC0 1.0 Universal](THIRD_PARTY.md).
