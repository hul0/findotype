# Findotype

[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL%203.0-blue.svg)](LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/python-3.10+-brightgreen.svg)](pyproject.toml)
[![Data License: CC0-1.0](https://img.shields.io/badge/Data%20License-CC0%201.0-lightgrey.svg)](THIRD_PARTY.md)
[![CI](https://github.com/hul0/findotype/actions/workflows/ci.yml/badge.svg)](https://github.com/hul0/findotype/actions/workflows/ci.yml)

![Findotype Banner](assets/images/banner.jpeg)

Findotype is an offline medical ontology search engine, relational database, and Python library for the Disease Ontology (DOID) and Human Phenotype Ontology (HPO).

It parses OBO-JSON graphs into a normalized SQLite database with FTS5 text indexing, recursive ancestor/descendant graph traversals, and clinical symptom matching. It requires only the Python standard library and SQLite3.

### Knowledge Base at a Glance

| Metric | Verified Count | Description |
| :--- | :--- | :--- |
| **Diseases & Conditions** | **12,247** | Human disease terms from the Disease Ontology (`DOID`) |
| **Phenotypes & Symptoms** | **19,836** | Clinical signs and phenotypic abnormalities from `HPO` |
| **Medical Definitions** | **27,902** | Formal definitions with primary literature citations |
| **Clinical Synonyms** | **46,187** | Scope-classified synonyms (Exact, Narrow, Broad, Related) |
| **Authority Cross-References** | **57,889** | External database mappings (MeSH, ICD-10, OMIM, UMLS, SNOMED CT, NCI, Orphanet) |
| **Graph Connections** | **53,791** | Typed relationships (`is_a`, `has_symptom`, `has_material_basis_in`, etc.) |
| **Offline Database Footprint** | **51.3 MB** | Compact single-file SQLite database (`data/findotype.db`) |
| **External Dependencies** | **0** | Pure standard library (`python >= 3.10` + `sqlite3`) |

---

## Contents

- [Knowledge Base at a Glance](#knowledge-base-at-a-glance)
- [Quickstart](#quickstart)
- [Web Interface & REST API](#web-interface--rest-api)
- [CLI Reference](#cli-reference)
- [Python API Reference](#python-api-reference)
- [REST API Endpoints](#rest-api-endpoints)
- [Database Schema](#database-schema)
- [Building from Source Datasets](#building-from-source-datasets)
- [Benchmarks](#benchmarks)
- [Contributing & Community](#contributing--community)
- [Support & Sponsorship](#support--sponsorship)
- [License & Authors](#license--authors)

---

## Quickstart

### 1. Installation

Requires **Python 3.10** or newer.

```bash
git clone https://github.com/hul0/findotype.git
cd findotype
pip install -e .
```

### 2. Download Precompiled Knowledge Base

Download the release database (`findotype.db`, ~51 MB):

```bash
findotype download-db
```

### 3. Launch Local Server

```bash
findotype serve --port 8000
```

- **Web Interface**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Interactive Swagger Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **OpenAPI 3.0 Specification**: [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json)

---

## Web Interface & REST API

The local web interface is built with a monochrome design (no gradients, accessible high-contrast layout) and includes:

1. **Clinical Symptom Matcher**: Extracts symptoms from natural language text, computes Information Content ($IC$) per phenotype, and ranks candidate diseases by query coverage.
2. **Disease Search**: Full-text search across disease names, synonyms, CURIEs, and definitions using SQLite FTS5.
3. **Entity Inspector**: Displays definitions, scope-grouped synonyms, cross-references (MeSH, ICD-10, OMIM, UMLS, NCI), and hierarchical parent/child trees.
4. **Knowledge Base Statistics**: Dataset provenance, release dates, SHA-256 checksums, and namespace distribution.

---

## CLI Reference

All commands support `--json` for machine-readable output.

| Command | Arguments | Description |
| :--- | :--- | :--- |
| `serve` | `[-p PORT] [-H HOST] [--db PATH]` | Launch the web interface, OpenAPI schema, and Swagger UI |
| `download-db` | `[-t TAG] [-o OUTPUT]` | Download precompiled `findotype.db` from GitHub Releases |
| `match` | `"<symptoms>" [-n LIMIT] [--db PATH]` | Match symptoms to candidate diseases with query coverage |
| `search` | `"<query>" [-n LIMIT] [--db PATH]` | Search terms by name, synonym, CURIE, or definition |
| `inspect` | `<CURIE> [--db PATH]` | Inspect full details of a specific disease entity |
| `stats` | `[--db PATH]` | Print database metrics, dataset provenance, and namespaces |
| `download` | `[-o OUTPUT] [--url URL]` | Download raw `doid.json` dataset from upstream |
| `validate` | `<file>` | Validate structure and node counts of an OBO-JSON file |
| `import` | `<file> [--db PATH] [--include-obsolete]` | Ingest `doid.json` into SQLite database |
| `import-hpo` | `<file> [--db PATH] [--include-obsolete]` | Ingest `hp-base.json` into SQLite database |

### Examples

```bash
# Match clinical symptoms
findotype match "I have fever, cough, nausea"

# Search diseases
findotype search "tuberculosis"

# Inspect a specific disease term
findotype inspect DOID:0001816

# View dataset stats in JSON
findotype stats --json
```

---

## Python API Reference

```python
from findotype import Findotype

# Initialize engine (defaults to data/findotype.db)
engine = Findotype()

# 1. Clinical Symptom & Phenotype Matching
matches = engine.match_phenotypes("I have fever, cough, nausea", limit=5)
for m in matches:
    matched = ", ".join(p.name for p in m.matched_phenotypes)
    print(f"{m.disease_name} ({m.disease_id}) -> Coverage: {m.query_coverage_pct}% | Matched: {matched}")

# 2. Disease Lookup
disease = engine.get_disease("DOID:0001816")
print(f"Name: {disease.name}")
print(f"Definition: {disease.definition.definition if disease.definition else 'N/A'}")

# Synonyms by scope (EXACT, NARROW, BROAD, RELATED)
for syn in disease.synonyms:
    print(f"[{syn.scope}] {syn.synonym}")

# External Database References (MeSH, ICD-10, OMIM, UMLS)
for xref in disease.cross_references:
    print(f"{xref.db}: {xref.accession}")

# 3. Full-Text Search
results = engine.search_diseases("angiosarcoma", limit=10)
for r in results:
    print(f"[{r.id}] {r.name} (Match: {r.match_type.value}, Score: {r.rank_score})")

# 4. Hierarchy Traversals (Recursive CTEs)
parents = engine.get_parents("DOID:0001816")
children = engine.get_children("DOID:175")
ancestors = engine.get_ancestors("DOID:0001816", max_depth=50)
descendants = engine.get_descendants("DOID:175", max_depth=50)

# 5. Graph Relationships
relationships = engine.get_relationships("DOID:0001816")
for rel in relationships:
    print(f"--[{rel.predicate_label}]--> {rel.object_id} ({rel.object_name})")

# 6. Provenance & Metadata
kb_meta = engine.get_knowledge_base_metadata()
datasets = engine.get_datasets()
print(f"Knowledge Base: {kb_meta.name} (Schema v{kb_meta.schema_version})")
for ds in datasets:
    print(f" - {ds.dataset_name} v{ds.dataset_version} (License: {ds.license})")

# Close connection
engine.close()
```

Context manager support:

```python
with Findotype() as engine:
    disease = engine.get_disease("DOID:399")
    print(disease.name)
```

---

## REST API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Web application interface |
| `GET` | `/docs` | Interactive Swagger UI documentation |
| `GET` | `/openapi.json` | OpenAPI 3.0.3 specification |
| `GET` | `/api/stats` | Database summary, counts, datasets, and namespaces |
| `GET` | `/api/search?q=<query>&limit=<n>` | Full-text disease search |
| `GET` | `/api/diseases/{id}` | Complete disease details, synonyms, xrefs, hierarchy |
| `GET` | `/api/diseases/{id}/parents` | Direct 1-hop parent terms |
| `GET` | `/api/diseases/{id}/children` | Direct 1-hop child terms |
| `GET` | `/api/diseases/{id}/ancestors` | Recursive ancestor hierarchy |
| `GET` | `/api/diseases/{id}/descendants` | Recursive descendant hierarchy |
| `GET` | `/api/diseases/{id}/relationships` | Connected graph relationships |
| `GET` | `/api/match?symptoms=<text>&limit=<n>` | Clinical phenotype matching (GET) |
| `POST` | `/api/match` | Clinical phenotype matching (JSON body: `{"symptoms": "...", "limit": 10}`) |

---

## Database Schema

Findotype normalizes OBO-JSON graphs into the following relational tables:

```text
entities            : Ontology terms across namespaces (DOID, HP, CHEBI, UBERON, etc.)
definitions         : Formal definitions and citation sources
synonyms            : EXACT, NARROW, BROAD, and RELATED synonyms
cross_references    : External database mappings (MeSH, ICD-10, OMIM, UMLS, NCI)
subsets             : Ontology slims (e.g. DO_cancer_slim, DO_rare_slim)
alt_ids             : Secondary identifiers mapped to canonical entities
relationships       : Directed graph edges with predicate labels
provenance          : Dataset hashes, source URIs, release dates, and import timestamps
metadata            : Knowledge Base schema and metadata key-values
disease_fts         : SQLite FTS5 virtual table for full-text search
```

---

## Building from Source Datasets

To construct `findotype.db` directly from raw upstream OBO-JSON files:

```bash
# 1. Download source datasets
mkdir -p assets/DO
curl -sSL "https://raw.githubusercontent.com/DiseaseOntology/HumanDiseaseOntology/main/src/ontology/doid.json" -o assets/DO/doid.json
curl -sSL "https://github.com/obophenotype/human-phenotype-ontology/releases/latest/download/hp-base.json" -o assets/hp-base.json

# 2. Validate structures
findotype validate assets/DO/doid.json
findotype validate assets/hp-base.json

# 3. Ingest into SQLite
findotype import assets/DO/doid.json --db data/findotype.db
findotype import-hpo assets/hp-base.json --db data/findotype.db

# 4. Verify database metrics
findotype stats --db data/findotype.db
```

---

## Benchmarks

Measured on Ubuntu Linux (AMD x86_64, Python 3.12, SQLite 3.45) with the combined Disease Ontology and HPO datasets (38,296 entities, 53,791 relationships, 46,187 synonyms):

| Operation | Mean Latency | P95 Latency | Implementation Detail |
| :--- | :--- | :--- | :--- |
| **Direct Entity Lookup** | **0.064 ms** | 0.072 ms | Primary key indexed B-tree retrieval |
| **Recursive Ancestor CTE** | **0.065 ms** | 0.113 ms | Recursive SQLite CTE traversal to root |
| **Multi-Tiered FTS Search** | **50.4 ms** | 58.4 ms | Exact, prefix, synonym and FTS5 ranking |
| **Clinical Phenotype Match**| **190.6 ms** | 235.1 ms | Multi-symptom extraction + graph intersection |
| **Full Ingestion Pipeline** | **2.80 s** | N/A | Parsing, validation, and batch transactions |

Run benchmarks locally:
```bash
python3 scripts/benchmark.py
```

---

## Test Suite

```bash
python3 -m unittest discover -s tests -v
```

---

## Contributing & Community

Contributions are welcome from bioinformaticians, medical researchers, and software engineers.

- **Guidelines**: Please read [CONTRIBUTING.md](CONTRIBUTING.md) before submitting pull requests.
- **Code of Conduct**: All participants agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).
- **Discussions**: Ask questions or share ideas on [GitHub Discussions](https://github.com/hul0/findotype/discussions).

---

## Support & Sponsorship

Findotype is an independent open-source medical ontology engine and research project.

If you or your organization are interested in **supporting, sponsoring, or partnering** on this project:

- **Email**: [hulo@crine.in](mailto:hulo@crine.in)
- **Support Guide**: See [SUPPORT.md](SUPPORT.md) for details on sponsorship, infrastructure grants, and feature prioritization.

---

## License & Authors

- **Source Code**: [GNU AGPL-3.0-or-later](LICENSE)
- **Ontology Data**: [Creative Commons CC0 1.0 Universal](THIRD_PARTY.md)
- **Author & Maintainer**: Rupam Ghosh ([hulo@crine.in](mailto:hulo@crine.in))
- **Repository**: [https://github.com/hul0/findotype](https://github.com/hul0/findotype)
