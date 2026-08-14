# Contributing to Findotype

Thank you for your interest in contributing to **Findotype**!

## Code Guidelines

1. **Zero External Runtime Dependencies**: Core functionality (importers, database access, repositories, services, CLI) must rely exclusively on Python 3.10+ standard libraries and SQLite.
2. **Type Annotations**: All modules, functions, and classes must include Python type hints.
3. **Deterministic Transactions**: Database operations must be transactional, idempotent, and handle edge cases gracefully without corrupting database state.
4. **Security & Input Validation**: Treat all external ontology files as untrusted. Use parameterized SQL queries everywhere.
5. **Testing**: Add unit and integration tests under `tests/` for all new features, normalizers, or queries.

## Running Tests

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Licensing

By contributing, you agree that your contributions will be licensed under the **GNU Affero General Public License v3.0 or later (AGPL-3.0-or-later)**.
