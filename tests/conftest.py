"""Shared pytest and test fixtures for Findotype."""

from pathlib import Path
import tempfile
import pytest

from findotype.services.ontology_service import Findotype

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_DOID_PATH = FIXTURES_DIR / "sample_doid.json"


@pytest.fixture
def sample_doid_file() -> Path:
    """Path to sample doid.json fixture."""
    return SAMPLE_DOID_PATH


@pytest.fixture
def temp_db_path():
    """Temporary SQLite database file path."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = Path(f.name)
    yield path
    if path.exists():
        path.unlink()
        # Clean up WAL files if any
        for extra in [f"{path}-wal", f"{path}-shm"]:
            if Path(extra).exists():
                Path(extra).unlink()


@pytest.fixture
def populated_engine(sample_doid_file, temp_db_path):
    """A Findotype instance pre-populated with sample_doid.json."""
    engine = Findotype(db_path=temp_db_path)
    engine.import_doid(sample_doid_file, include_obsolete=False)
    yield engine
    engine.close()
