"""Configuration defaults and SQLite settings for Findotype."""

from pathlib import Path

# Default file paths
DEFAULT_DATA_DIR = Path("data")
DEFAULT_DB_NAME = "findotype.db"
DEFAULT_DB_PATH = DEFAULT_DATA_DIR / DEFAULT_DB_NAME

# Upstream Disease Ontology source URL
DEFAULT_DOID_URL = "http://purl.obolibrary.org/obo/doid.json"

# SQLite Pragmas for maximum offline read/write throughput and reliability
SQLITE_PRAGMAS = {
    "journal_mode": "WAL",
    "synchronous": "NORMAL",
    "foreign_keys": "ON",
    "temp_store": "MEMORY",
    "cache_size": -64000,  # 64 MB page cache
    "mmap_size": 268435456,  # 256 MB memory-mapped I/O
    "busy_timeout": 5000,
}

# Current schema version
SCHEMA_VERSION = "1.0.0"
