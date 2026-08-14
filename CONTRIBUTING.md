# Contributing to Findotype

Thank you for your interest in contributing to **Findotype**! We welcome contributions from researchers, software engineers, bioinformaticians, and medical clinicians.

---

## Code of Conduct

All contributors and maintainers are expected to adhere to our [Code of Conduct](CODE_OF_CONDUCT.md). Please report any unacceptable behavior to **[hulo@crine.in](mailto:hulo@crine.in)**.

---

## Development Setup

### 1. Requirements
* Python **3.10** or newer
* Git

### 2. Local Environment Setup

```bash
# Clone repository
git clone https://github.com/hul0/findotype.git
cd findotype

# Install in editable mode with development tools
pip install -e ".[dev]"
```

---

## Architectural Principles & Guidelines

1. **Zero External Runtime Dependencies**: Core packages (`models`, `db`, `ontology`, `importers`, `repositories`, `services`, `server`, `cli`) must rely solely on Python standard libraries and SQLite3.
2. **Strict Type Annotations**: All modules, functions, and public methods must include static type hints (`from typing import ...`).
3. **Deterministic Transactions**: Database ingestion operations must be atomic, idempotent, and handle edge cases gracefully without corrupting database state.
4. **Parameterized SQL Queries**: Never use string formatting or concatenation to build SQL statements. Use parameterized queries (`?`) everywhere to protect against injection.
5. **No Tracked Binary DBs**: Do not commit `.db`, `.tar.gz`, or raw JSON ontology files to git. Databases are built in CI and distributed via GitHub Releases.

---

## Running the Test Suite

Before opening a pull request, ensure all tests pass cleanly:

```bash
# Run unit and integration tests
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

If adding new functionality (e.g. normalizers, parsers, or API endpoints), write corresponding unit tests under the `tests/` directory.

---

## Contribution Workflow

1. **Fork & Branch**: Create a feature branch off `main` (e.g., `git checkout -b feature/mondo-importer`).
2. **Commit Hygiene**: Write clear, descriptive commit messages following the Conventional Commits format (e.g., `feat: add MONDO ontology importer`, `fix: handle missing alt_ids gracefully`).
3. **Test Verification**: Verify all unit tests pass locally.
4. **Open a Pull Request**: Submit your pull request against the `main` branch on [GitHub](https://github.com/hul0/findotype/pulls). Provide a clear description of the problem solved and any relevant test outputs.

---

## Questions & Support

* For discussions and questions, visit [GitHub Discussions](https://github.com/hul0/findotype/discussions).
* For support or sponsorship inquiries, email **[hulo@crine.in](mailto:hulo@crine.in)**.

---

## Licensing

By contributing to Findotype, you agree that your contributions will be licensed under the **[GNU Affero General Public License v3.0 or later (AGPL-3.0-or-later)](LICENSE)**.
