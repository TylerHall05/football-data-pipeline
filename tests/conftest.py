from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_csv_bytes() -> bytes:
    """Synthetic E0 2024/25 sample with deliberate data-quality problems."""
    return (FIXTURES / "sample_E0_2425.csv").read_bytes()
