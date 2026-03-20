"""Unit tests for time synchronization module."""

import numpy as np
import pandas as pd
import pytest

from src.core.time_sync import TimeSynchronizer, convert_timestamp_to_seconds


class TestTimeSynchronizer:
    """Tests for TimeSynchronizer class."""

    def test_init_default_precision(self):
        """Test default precision initialization."""
        sync = TimeSynchronizer()
        assert sync.precision_ms == 10.0
        assert sync.precision_s == 0.01

    def test_init_custom_precision(self):
        """Test custom precision initialization."""
        sync = TimeSynchronizer(precision_ms=5.0)
        assert sync.precision_ms == 5.0
        assert sync.precision_s == 0.005

    def test_align_empty_dataframes(self):
        """Test alignment with empty input."""
        sync = TimeSynchronizer()
        result = sync.align_to_common_time([], [])
        assert result.empty

    def test_align_single_dataframe(self):
        """Test alignment with single DataFrame."""
        sync = TimeSynchronizer()
        df = pd.DataFrame(
            {
                "time": [0.0, 0.1, 0.2],
                "signal": [1.0, 2.0, 3.0],
            }
        )
        result = sync.align_to_common_time([df], ["time"])
        assert "time" in result.columns
        assert len(result) > 0

    def test_align_multiple_dataframes(self):
        """Test alignment with multiple DataFrames."""
        sync = TimeSynchronizer()
        df1 = pd.DataFrame(
            {
                "time": [0.0, 0.05, 0.1, 0.15, 0.2],
                "signal1": [1.0, 1.5, 2.0, 2.5, 3.0],
            }
        )
        df2 = pd.DataFrame(
            {
                "time": [0.0, 0.02, 0.04, 0.06, 0.08, 0.1],
                "signal2": [10.0, 12.0, 14.0, 16.0, 18.0, 20.0],
            }
        )
        result = sync.align_to_common_time([df1, df2], ["time", "time"])
        assert "time" in result.columns
        assert any("signal1" in col for col in result.columns)
        assert any("signal2" in col for col in result.columns)

    def test_align_with_time_range(self):
        """Test alignment with specified time range."""
        sync = TimeSynchronizer()
        df = pd.DataFrame(
            {
                "time": [0.0, 0.1, 0.2, 0.3, 0.4],
                "signal": [1.0, 2.0, 3.0, 4.0, 5.0],
            }
        )
        result = sync.align_to_common_time(
            [df], ["time"], start_time=0.1, end_time=0.3
        )
        assert result["time"].iloc[0] >= 0.1
        assert result["time"].iloc[-1] <= 0.3

    def test_resample_basic(self):
        """Test basic resampling."""
        sync = TimeSynchronizer()
        df = pd.DataFrame(
            {
                "time": [0.0, 0.1, 0.2, 0.3, 0.4],
                "signal": [1.0, 2.0, 3.0, 4.0, 5.0],
            }
        )
        result = sync.resample(df, "time", target_rate_hz=5.0)
        assert "time" in result.columns
        assert "signal" in result.columns

    def test_resample_single_row(self):
        """Test resampling with single row DataFrame."""
        sync = TimeSynchronizer()
        df = pd.DataFrame({"time": [0.0], "signal": [1.0]})
        result = sync.resample(df, "time", target_rate_hz=10.0)
        assert len(result) == 1

    def test_resample_missing_time_column(self):
        """Test resampling with missing time column."""
        sync = TimeSynchronizer()
        df = pd.DataFrame({"signal": [1.0, 2.0, 3.0]})
        with pytest.raises(ValueError):
            sync.resample(df, "time", target_rate_hz=10.0)


class TestConvertTimestamp:
    """Tests for timestamp conversion function."""

    def test_convert_int_timestamp(self):
        """Test converting integer timestamp."""
        result = convert_timestamp_to_seconds(1000)
        assert result == 1000.0

    def test_convert_float_timestamp(self):
        """Test converting float timestamp."""
        result = convert_timestamp_to_seconds(1.5)
        assert result == 1.5

    def test_convert_string_float(self):
        """Test converting string float."""
        result = convert_timestamp_to_seconds("1.5")
        assert result == 1.5

    def test_convert_string_with_format(self):
        """Test converting string with format."""
        from datetime import datetime

        dt = datetime(2024, 1, 1, 12, 0, 0)
        result = convert_timestamp_to_seconds(
            "2024-01-01 12:00:00", format_string="%Y-%m-%d %H:%M:%S"
        )
        assert abs(result - dt.timestamp()) < 0.001

    def test_convert_datetime_object(self):
        """Test converting datetime object."""
        from datetime import datetime

        dt = datetime(2024, 1, 1, 12, 0, 0)
        result = convert_timestamp_to_seconds(dt)
        assert abs(result - dt.timestamp()) < 0.001

    def test_convert_invalid_string(self):
        """Test converting invalid string."""
        with pytest.raises(ValueError):
            convert_timestamp_to_seconds("invalid")

    def test_convert_unsupported_type(self):
        """Test converting unsupported type."""
        with pytest.raises(TypeError):
            convert_timestamp_to_seconds([])
