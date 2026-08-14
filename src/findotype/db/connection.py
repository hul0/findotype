"""Database connection manager with PRAGMA tuning and context management."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional, Union

from findotype.config import SQLITE_PRAGMAS
from findotype.db.schema import init_db_schema


def get_connection(
    db_path: Union[str, Path] = ":memory:",
    initialize_schema: bool = False,
    timeout: float = 10.0,
) -> sqlite3.Connection:
    """
    Create a configured SQLite connection with optimized pragmas.

    Args:
        db_path: Path to SQLite file or ':memory:'
        initialize_schema: If True, executes schema DDL
        timeout: Lock acquisition timeout in seconds

    Returns:
        Configured sqlite3.Connection instance with Row factory
    """
    if db_path != ":memory:":
        path = Path(db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        db_str = str(path)
    else:
        db_str = ":memory:"

    conn = sqlite3.connect(db_str, timeout=timeout)
    conn.row_factory = sqlite3.Row

    # Apply performance and integrity pragmas
    cursor = conn.cursor()
    for pragma_key, pragma_val in SQLITE_PRAGMAS.items():
        try:
            cursor.execute(f"PRAGMA {pragma_key} = {pragma_val};")
        except sqlite3.DatabaseError:
            # Pragmas like WAL might fail on in-memory or specific filesystems gracefully
            pass

    if initialize_schema:
        init_db_schema(conn)

    return conn


@contextmanager
def get_db_context(
    db_path: Union[str, Path] = ":memory:",
    initialize_schema: bool = False,
) -> Generator[sqlite3.Connection, None, None]:
    """Context manager for SQLite connections with automatic commit/rollback and close."""
    conn = get_connection(db_path, initialize_schema=initialize_schema)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
