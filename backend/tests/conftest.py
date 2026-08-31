"""
Pytest fixtures untuk Asmeranda backend tests.

Menyediakan:
- Sample data (DataFrames)
- Mock clients (FastAPI TestClient)
- Database fixtures
- Temporary directories
"""
import os
import sys
import tempfile
from pathlib import Path
from typing import Generator

import polars as pl
import pytest
from fastapi.testclient import TestClient

# Tambah project root ke path agar imports bekerja
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.main import create_app


# ──────────────────────────────────────────────────────────
# Application & Client Fixtures
# ──────────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def app():
    """Create FastAPI application instance."""
    return create_app()


@pytest.fixture
def client(app) -> TestClient:
    """Create TestClient for API testing."""
    return TestClient(app)


# ──────────────────────────────────────────────────────────
# Sample Data Fixtures
# ──────────────────────────────────────────────────────────


@pytest.fixture
def sample_df_classification() -> pl.DataFrame:
    """Sample dataset untuk classification tasks."""
    return pl.DataFrame({
        "age": [25, 32, 47, 51, 22, 38, 44, 29, 60, 35, 41, 28],
        "salary": [50000, 60000, 80000, 90000, 45000, 70000, 85000, 55000, 95000, 65000, 75000, 52000],
        "department": ["IT", "HR", "IT", "Finance", "HR", "IT", "Finance", "HR", "Finance", "IT", "HR", "IT"],
        "experience_years": [2, 5, 10, 15, 1, 8, 12, 4, 20, 7, 9, 3],
        "churn": [0, 0, 1, 1, 0, 1, 1, 0, 1, 0, 0, 0],  # Target
    })


@pytest.fixture
def sample_df_regression() -> pl.DataFrame:
    """Sample dataset untuk regression tasks."""
    return pl.DataFrame({
        "square_meters": [50, 75, 100, 125, 150, 175, 200, 225, 250, 275, 300, 325],
        "bedrooms": [1, 1, 2, 2, 3, 3, 3, 4, 4, 4, 5, 5],
        "age_years": [10, 15, 5, 20, 8, 3, 12, 6, 9, 14, 2, 11],
        "price": [100000, 150000, 200000, 250000, 300000, 350000, 400000, 450000, 500000, 550000, 600000, 650000],  # Target
    })


@pytest.fixture
def sample_df_with_nulls() -> pl.DataFrame:
    """Sample dataset dengan missing values."""
    return pl.DataFrame({
        "age": [25, None, 47, 51, 22, None, 44, 29, 60, 35],
        "salary": [50000, 60000, None, 90000, 45000, 70000, None, 55000, 95000, 65000],
        "department": ["IT", "HR", None, "Finance", "HR", "IT", "Finance", None, "Finance", "IT"],
        "churn": [0, 0, 1, 1, 0, None, 1, 0, 1, 0],
    })


@pytest.fixture
def sample_df_categorical() -> pl.DataFrame:
    """Sample dataset dengan banyak categorical features."""
    return pl.DataFrame({
        "color": ["red", "blue", "green", "red", "blue", "green", "red", "blue", "green", "red"],
        "size": ["S", "M", "L", "S", "M", "L", "S", "M", "L", "S"],
        "material": ["wood", "plastic", "metal", "wood", "plastic", "metal", "wood", "plastic", "metal", "wood"],
        "price": [100, 150, 200, 110, 160, 210, 105, 155, 205, 115],
    })


@pytest.fixture
def sample_df_timeseries() -> pl.DataFrame:
    """Sample time series dataset."""
    import datetime
    dates = [datetime.datetime(2024, 1, 1) + datetime.timedelta(days=i) for i in range(30)]
    return pl.DataFrame({
        "date": dates,
        "value": [100 + i + (5 if i % 2 == 0 else -5) for i in range(30)],
        "trend": list(range(30)),
    })


# ──────────────────────────────────────────────────────────
# Temporary Directory & File Fixtures
# ──────────────────────────────────────────────────────────


@pytest.fixture
def temp_data_dir() -> Generator[Path, None, None]:
    """Create temporary directory untuk test data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_csv_file(sample_df_classification, temp_data_dir) -> Path:
    """Create sample CSV file."""
    csv_path = temp_data_dir / "sample.csv"
    sample_df_classification.write_csv(csv_path)
    return csv_path


@pytest.fixture
def sample_parquet_file(sample_df_classification, temp_data_dir) -> Path:
    """Create sample Parquet file."""
    parquet_path = temp_data_dir / "sample.parquet"
    sample_df_classification.write_parquet(parquet_path)
    return parquet_path


# ──────────────────────────────────────────────────────────
# Environment & Configuration Fixtures
# ──────────────────────────────────────────────────────────


@pytest.fixture
def test_env(monkeypatch, temp_data_dir):
    """Setup test environment variables."""
    monkeypatch.setenv("ASMERANDA_DATA_DIR", str(temp_data_dir))
    monkeypatch.setenv("ASMERANDA_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("ASMERANDA_DEBUG", "true")
    return monkeypatch


@pytest.fixture
def clean_state():
    """Clean core.state sebelum test."""
    from core import state
    yield
    # Cleanup setelah test
    for state_id in list(state._states.keys()):
        state.delete_state(state_id)


# ──────────────────────────────────────────────────────────
# Mock & Patch Fixtures
# ──────────────────────────────────────────────────────────


@pytest.fixture
def mock_file_upload(monkeypatch, sample_df_classification):
    """Mock file upload untuk testing upload functionality."""
    
    def mock_save_dataset(*args, **kwargs):
        return "mock-dataset-id-123"
    
    monkeypatch.setattr("backend.services.dataset_service.DatasetService.save_dataset", mock_save_dataset)


# ──────────────────────────────────────────────────────────
# Marker untuk kategorisasi tests
# ──────────────────────────────────────────────────────────


def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "unit: Mark test sebagai unit test")
    config.addinivalue_line("markers", "integration: Mark test sebagai integration test")
    config.addinivalue_line("markers", "security: Mark test sebagai security test")
    config.addinivalue_line("markers", "slow: Mark test sebagai slow")


# ──────────────────────────────────────────────────────────
# Helper Functions untuk Tests
# ──────────────────────────────────────────────────────────


def assert_dataframe_shape(df: pl.DataFrame, expected_rows: int, expected_cols: int):
    """Assert DataFrame shape."""
    rows, cols = df.shape
    assert rows == expected_rows, f"Expected {expected_rows} rows, got {rows}"
    assert cols == expected_cols, f"Expected {expected_cols} columns, got {cols}"


def assert_no_nulls(df: pl.DataFrame):
    """Assert DataFrame has no null values."""
    null_count = df.null_count().sum()
    assert null_count == 0, f"Expected no nulls, but found {null_count}"


def assert_all_unique(df: pl.DataFrame, column: str):
    """Assert column has all unique values."""
    unique_count = df.select(column).n_unique()
    total_count = len(df)
    assert unique_count == total_count, f"Column {column} has {total_count - unique_count} duplicates"
