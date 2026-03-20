"""Pytest configuration for vehicle test analysis tests."""

import sys
from pathlib import Path

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def sample_csv_data(tmp_path):
    """Create a sample CSV file for testing."""
    import pandas as pd

    data = pd.DataFrame(
        {
            "time": [0.0, 0.1, 0.2, 0.3, 0.4, 0.5],
            "signal1": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
            "signal2": [10.0, 20.0, 30.0, 40.0, 50.0, 60.0],
        }
    )

    csv_path = tmp_path / "test_data.csv"
    data.to_csv(csv_path, index=False)
    return csv_path


@pytest.fixture
def sample_can_data(tmp_path):
    """Create sample CAN log data for testing."""
    # This would create a sample BLF or ASC file
    # For now, return a path to be used by tests
    return tmp_path / "test_can.blf"


@pytest.fixture
def sample_indicator_definition():
    """Create a sample indicator definition for testing."""
    from src.core.indicator_engine import IndicatorDefinition, IndicatorType

    return IndicatorDefinition(
        name="test_indicator",
        indicator_type=IndicatorType.SINGLE_VALUE,
        signal_name="signal1",
        lower_limit=0.0,
        upper_limit=10.0,
    )


@pytest.fixture
def sample_dataframe():
    """Create a sample DataFrame for testing."""
    import pandas as pd

    return pd.DataFrame(
        {
            "time": [0.0, 0.1, 0.2, 0.3, 0.4, 0.5],
            "signal1": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
            "signal2": [10.0, 20.0, 30.0, 40.0, 50.0, 60.0],
        }
    )
