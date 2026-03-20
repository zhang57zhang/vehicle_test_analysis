"""
Integration tests for multi-source time synchronization.

Tests the complete flow:
Multiple data sources -> Time sync -> Aligned data -> Analysis
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from src.parsers.csv_parser import CSVParser
from src.core.time_sync import TimeSynchronizer, convert_timestamp_to_seconds
from src.core.indicator_engine import (
    IndicatorDefinition,
    IndicatorEngine,
    IndicatorType,
)
from src.analyzers.functional_analyzer import FunctionalAnalyzer
from src.analyzers.performance_analyzer import PerformanceAnalyzer


class TestMultiSourceTimeSync:
    """Integration tests for multi-source time synchronization."""

    @pytest.fixture
    def multi_source_csv_data(self, tmp_path):
        """Create multiple CSV files with different sample rates."""
        # Source 1: Vehicle dynamics (100 Hz)
        source1 = pd.DataFrame({
            "time": np.linspace(0, 10, 1001),
            "VehicleSpeed": np.concatenate([
                np.linspace(0, 100, 500),
                np.linspace(100, 50, 501)
            ]),
            "LateralAccel": np.sin(2 * np.pi * 0.5 * np.linspace(0, 10, 1001)),
        })
        csv1 = tmp_path / "vehicle_dynamics.csv"
        source1.to_csv(csv1, index=False)

        # Source 2: Engine data (50 Hz)
        source2 = pd.DataFrame({
            "time": np.linspace(0, 10, 501),
            "EngineRPM": np.concatenate([
                np.linspace(800, 3000, 250),
                np.linspace(3000, 1500, 251)
            ]),
            "ThrottlePosition": np.concatenate([
                np.linspace(0, 100, 100),
                np.ones(300) * 100,
                np.linspace(100, 0, 101)
            ]),
        })
        csv2 = tmp_path / "engine_data.csv"
        source2.to_csv(csv2, index=False)

        # Source 3: Brake data (10 Hz)
        source3 = pd.DataFrame({
            "time": np.linspace(0, 10, 101),
            "BrakePressure": np.concatenate([
                np.zeros(30),
                np.linspace(0, 50, 30),
                np.linspace(50, 0, 41)
            ]),
            "ABS_State": [0] * 30 + [1] * 20 + [0] * 51,
        })
        csv3 = tmp_path / "brake_data.csv"
        source3.to_csv(csv3, index=False)

        return csv1, csv2, csv3, source1, source2, source3

    def test_sync_two_sources(self, multi_source_csv_data):
        """Test synchronizing two data sources."""
        csv1, csv2, _, source1, source2, _ = multi_source_csv_data

        # Parse both sources
        parser1 = CSVParser(csv1, time_column="time")
        parser2 = CSVParser(csv2, time_column="time")

        result1 = parser1.parse()
        result2 = parser2.parse()

        assert result1.is_success
        assert result2.is_success

        # Synchronize
        sync = TimeSynchronizer(precision_ms=20.0)
        aligned = sync.align_to_common_time(
            [result1.data, result2.data],
            ["time", "time"],
        )

        assert aligned is not None
        assert "time" in aligned.columns
        assert len(aligned) > 0

        # Check that both source signals are present (with source prefix)
        columns = aligned.columns.tolist()
        assert any("VehicleSpeed" in col for col in columns)
        assert any("EngineRPM" in col for col in columns)

    def test_sync_three_sources(self, multi_source_csv_data):
        """Test synchronizing three data sources."""
        csv1, csv2, csv3, source1, source2, source3 = multi_source_csv_data

        # Parse all sources
        parsers = [
            CSVParser(csv1, time_column="time"),
            CSVParser(csv2, time_column="time"),
            CSVParser(csv3, time_column="time"),
        ]

        results = [p.parse() for p in parsers]

        assert all(r.is_success for r in results)

        # Synchronize all three
        sync = TimeSynchronizer(precision_ms=50.0)
        aligned = sync.align_to_common_time(
            [r.data for r in results],
            ["time", "time", "time"],
        )

        assert aligned is not None
        assert "time" in aligned.columns

        # Check all signals are present
        columns = aligned.columns.tolist()
        assert any("VehicleSpeed" in col for col in columns)
        assert any("EngineRPM" in col for col in columns)
        assert any("BrakePressure" in col for col in columns)

    def test_sync_with_time_range(self, multi_source_csv_data):
        """Test synchronization with specified time range."""
        csv1, csv2, _, _, _, _ = multi_source_csv_data

        parser1 = CSVParser(csv1, time_column="time")
        parser2 = CSVParser(csv2, time_column="time")

        result1 = parser1.parse()
        result2 = parser2.parse()

        # Synchronize with specific time range
        sync = TimeSynchronizer(precision_ms=20.0)
        aligned = sync.align_to_common_time(
            [result1.data, result2.data],
            ["time", "time"],
            start_time=2.0,
            end_time=8.0,
        )

        assert aligned is not None
        assert aligned["time"].min() >= 2.0
        assert aligned["time"].max() <= 8.0

    def test_sync_to_indicator_workflow(self, multi_source_csv_data):
        """Test complete workflow: sync -> indicator calculation."""
        csv1, csv2, _, _, _, _ = multi_source_csv_data

        # Parse
        parser1 = CSVParser(csv1, time_column="time")
        parser2 = CSVParser(csv2, time_column="time")

        result1 = parser1.parse()
        result2 = parser2.parse()

        # Sync
        sync = TimeSynchronizer(precision_ms=20.0)
        aligned = sync.align_to_common_time(
            [result1.data, result2.data],
            ["time", "time"],
        )

        # Calculate indicators on aligned data
        engine = IndicatorEngine()

        # Find the actual column names (they have source prefix)
        speed_col = [c for c in aligned.columns if "VehicleSpeed" in c][0]
        rpm_col = [c for c in aligned.columns if "EngineRPM" in c][0]

        indicators = [
            IndicatorDefinition(
                name="MaxSpeed",
                signal_name=speed_col,
                indicator_type=IndicatorType.STATISTICAL,
                formula="max",
            ),
            IndicatorDefinition(
                name="MaxRPM",
                signal_name=rpm_col,
                indicator_type=IndicatorType.STATISTICAL,
                formula="max",
            ),
        ]

        results = [engine.calculate(ind, aligned) for ind in indicators]

        assert len(results) == 2
        assert all(r.calculated_value is not None for r in results)


class TestTimeSyncEdgeCases:
    """Edge case tests for time synchronization."""

    def test_sync_empty_dataframes(self):
        """Test synchronizing empty DataFrames."""
        sync = TimeSynchronizer()

        aligned = sync.align_to_common_time([], [])

        assert aligned is not None
        assert aligned.empty

    def test_sync_single_dataframe(self):
        """Test synchronizing a single DataFrame."""
        df = pd.DataFrame({
            "time": np.linspace(0, 1, 101),
            "signal": np.sin(2 * np.pi * 5 * np.linspace(0, 1, 101)),
        })

        sync = TimeSynchronizer(precision_ms=10.0)
        aligned = sync.align_to_common_time([df], ["time"])

        assert aligned is not None
        assert "time" in aligned.columns

    def test_sync_mismatched_time_columns(self):
        """Test synchronization with mismatched time column count."""
        df1 = pd.DataFrame({
            "time": [0, 1, 2],
            "signal1": [1, 2, 3],
        })
        df2 = pd.DataFrame({
            "time": [0, 1, 2],
            "signal2": [4, 5, 6],
        })

        sync = TimeSynchronizer()

        with pytest.raises(ValueError):
            sync.align_to_common_time([df1, df2], ["time"])  # Only one time column

    def test_sync_missing_time_column(self):
        """Test synchronization with missing time column."""
        df1 = pd.DataFrame({
            "time": [0, 1, 2],
            "signal1": [1, 2, 3],
        })
        df2 = pd.DataFrame({
            "timestamp": [0, 1, 2],  # Different column name
            "signal2": [4, 5, 6],
        })

        sync = TimeSynchronizer()
        aligned = sync.align_to_common_time([df1, df2], ["time", "timestamp"])

        # Should still work, but df2 won't contribute time values
        assert aligned is not None

    def test_sync_non_overlapping_time_ranges(self):
        """Test synchronization with non-overlapping time ranges."""
        df1 = pd.DataFrame({
            "time": [0, 1, 2],
            "signal1": [1, 2, 3],
        })
        df2 = pd.DataFrame({
            "time": [10, 11, 12],  # Non-overlapping
            "signal2": [4, 5, 6],
        })

        sync = TimeSynchronizer()
        aligned = sync.align_to_common_time([df1, df2], ["time", "time"])

        assert aligned is not None
        # Should have NaN values for non-overlapping regions


class TestTimeSyncResampling:
    """Tests for time synchronization resampling functionality."""

    def test_resample_to_higher_rate(self):
        """Test resampling to a higher rate."""
        df = pd.DataFrame({
            "time": np.linspace(0, 10, 101),  # 10 Hz
            "signal": np.sin(2 * np.pi * 0.5 * np.linspace(0, 10, 101)),
        })

        sync = TimeSynchronizer()
        resampled = sync.resample(df, "time", target_rate_hz=100.0)  # 100 Hz

        assert resampled is not None
        # Should have approximately 1000 samples
        assert 900 < len(resampled) < 1100

    def test_resample_to_lower_rate(self):
        """Test resampling to a lower rate."""
        df = pd.DataFrame({
            "time": np.linspace(0, 10, 1001),  # 100 Hz
            "signal": np.sin(2 * np.pi * 0.5 * np.linspace(0, 10, 1001)),
        })

        sync = TimeSynchronizer()
        resampled = sync.resample(df, "time", target_rate_hz=10.0)  # 10 Hz

        assert resampled is not None
        # Should have approximately 100 samples
        assert 90 < len(resampled) < 110

    def test_resample_single_point(self):
        """Test resampling a DataFrame with single point."""
        df = pd.DataFrame({
            "time": [0.0],
            "signal": [1.0],
        })

        sync = TimeSynchronizer()
        resampled = sync.resample(df, "time", target_rate_hz=10.0)

        assert resampled is not None
        assert len(resampled) == 1

    def test_resample_preserves_values(self):
        """Test that resampling preserves signal values."""
        # Create a slowly varying signal
        df = pd.DataFrame({
            "time": np.linspace(0, 10, 1001),
            "signal": np.linspace(0, 100, 1001),
        })

        sync = TimeSynchronizer()
        resampled = sync.resample(df, "time", target_rate_hz=10.0)

        # Check that interpolated values are close to expected
        expected_at_5s = 50.0
        actual_at_5s = resampled[resampled["time"].between(4.9, 5.1)]["signal"].mean()

        assert abs(actual_at_5s - expected_at_5s) < 1.0


class TestTimestampConversion:
    """Tests for timestamp conversion utilities."""

    def test_convert_float_timestamp(self):
        """Test converting float timestamp."""
        result = convert_timestamp_to_seconds(12345.678)
        assert result == 12345.678

    def test_convert_int_timestamp(self):
        """Test converting integer timestamp."""
        result = convert_timestamp_to_seconds(12345)
        assert result == 12345.0

    def test_convert_string_timestamp(self):
        """Test converting string timestamp."""
        result = convert_timestamp_to_seconds("12345.678")
        assert result == 12345.678

    def test_convert_string_with_format(self):
        """Test converting string timestamp with format."""
        from datetime import datetime

        result = convert_timestamp_to_seconds(
            "2023-03-15 10:00:00",
            format_string="%Y-%m-%d %H:%M:%S"
        )
        assert isinstance(result, float)

    def test_convert_datetime_object(self):
        """Test converting datetime object."""
        from datetime import datetime

        dt = datetime(2023, 3, 15, 10, 0, 0)
        result = convert_timestamp_to_seconds(dt)

        assert isinstance(result, float)

    def test_convert_invalid_string(self):
        """Test converting invalid string."""
        with pytest.raises(ValueError):
            convert_timestamp_to_seconds("not_a_number")

    def test_convert_invalid_type(self):
        """Test converting invalid type."""
        with pytest.raises(TypeError):
            convert_timestamp_to_seconds([1, 2, 3])


class TestMultiSourceAnalysis:
    """Integration tests for multi-source data analysis."""

    @pytest.fixture
    def synchronized_data(self, tmp_path):
        """Create and synchronize multi-source data."""
        # Create three data sources
        source1 = pd.DataFrame({
            "time": np.linspace(0, 10, 1001),
            "VehicleSpeed": np.concatenate([
                np.linspace(0, 100, 500),
                np.linspace(100, 50, 501)
            ]),
        })

        source2 = pd.DataFrame({
            "time": np.linspace(0, 10, 501),
            "EngineRPM": np.concatenate([
                np.linspace(800, 3000, 250),
                np.linspace(3000, 1500, 251)
            ]),
        })

        source3 = pd.DataFrame({
            "time": np.linspace(0, 10, 101),
            "BrakePressure": np.concatenate([
                np.zeros(30),
                np.linspace(0, 50, 30),
                np.linspace(50, 0, 41)
            ]),
        })

        # Synchronize
        sync = TimeSynchronizer(precision_ms=20.0)
        aligned = sync.align_to_common_time(
            [source1, source2, source3],
            ["time", "time", "time"],
        )

        return aligned

    def test_multi_source_functional_analysis(self, synchronized_data):
        """Test functional analysis on synchronized data."""
        analyzer = FunctionalAnalyzer()

        # Find signal columns
        speed_col = [c for c in synchronized_data.columns if "VehicleSpeed" in c][0]
        rpm_col = [c for c in synchronized_data.columns if "EngineRPM" in c][0]

        # Run range checks
        speed_result = analyzer.check_value_range(
            synchronized_data,
            speed_col,
            min_value=0,
            max_value=120,
        )

        rpm_result = analyzer.check_value_range(
            synchronized_data,
            rpm_col,
            min_value=500,
            max_value=5000,
        )

        assert speed_result.passed
        assert rpm_result.passed

    def test_multi_source_performance_analysis(self, synchronized_data):
        """Test performance analysis on synchronized data."""
        analyzer = PerformanceAnalyzer()

        # Find signal columns
        speed_col = [c for c in synchronized_data.columns if "VehicleSpeed" in c][0]

        # Calculate statistics
        stats = analyzer.calculate_statistics(synchronized_data, speed_col)

        assert stats.passed
        assert "mean" in stats.details
        assert "std" in stats.details

    def test_multi_source_correlation_analysis(self, synchronized_data):
        """Test correlation analysis on synchronized data."""
        # Find signal columns
        speed_col = [c for c in synchronized_data.columns if "VehicleSpeed" in c][0]
        rpm_col = [c for c in synchronized_data.columns if "EngineRPM" in c][0]

        # Calculate correlation
        valid_data = synchronized_data[[speed_col, rpm_col]].dropna()
        correlation = valid_data.corr().iloc[0, 1]

        # Speed and RPM should have some correlation
        assert -1 <= correlation <= 1


class TestTimeSyncPrecision:
    """Tests for time synchronization precision settings."""

    def test_high_precision_sync(self):
        """Test high precision synchronization."""
        df1 = pd.DataFrame({
            "time": [0.000, 0.001, 0.002, 0.003, 0.004],
            "signal1": [1, 2, 3, 4, 5],
        })
        df2 = pd.DataFrame({
            "time": [0.0005, 0.0015, 0.0025, 0.0035],
            "signal2": [10, 20, 30, 40],
        })

        sync = TimeSynchronizer(precision_ms=1.0)  # 1 ms precision
        aligned = sync.align_to_common_time([df1, df2], ["time", "time"])

        assert aligned is not None
        assert len(aligned) > 0

    def test_low_precision_sync(self):
        """Test low precision synchronization."""
        df1 = pd.DataFrame({
            "time": [0.0, 0.1, 0.2, 0.3, 0.4],
            "signal1": [1, 2, 3, 4, 5],
        })
        df2 = pd.DataFrame({
            "time": [0.05, 0.15, 0.25, 0.35],
            "signal2": [10, 20, 30, 40],
        })

        sync = TimeSynchronizer(precision_ms=100.0)  # 100 ms precision
        aligned = sync.align_to_common_time([df1, df2], ["time", "time"])

        assert aligned is not None
        assert len(aligned) > 0

    def test_precision_affects_sample_count(self):
        """Test that precision affects sample count."""
        df1 = pd.DataFrame({
            "time": np.linspace(0, 1, 1001),
            "signal1": np.random.randn(1001),
        })

        sync_high = TimeSynchronizer(precision_ms=1.0)
        sync_low = TimeSynchronizer(precision_ms=100.0)

        aligned_high = sync_high.align_to_common_time([df1], ["time"])
        aligned_low = sync_low.align_to_common_time([df1], ["time"])

        # Higher precision should result in more samples
        assert len(aligned_high) >= len(aligned_low)
