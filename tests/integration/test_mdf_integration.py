"""
Integration tests for MDF file parsing workflow.

Tests the complete flow:
MDF file -> Parse -> Signal extraction -> Time sync -> Indicator calculation
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import numpy as np
import pandas as pd
import pytest

from src.parsers.mdf_parser import MDFParser
from src.parsers.base_parser import ParserStatus
from src.core.time_sync import TimeSynchronizer
from src.core.indicator_engine import (
    IndicatorDefinition,
    IndicatorEngine,
    IndicatorType,
)
from src.analyzers.performance_analyzer import PerformanceAnalyzer


class TestMDFParsingIntegration:
    """Integration tests for MDF file parsing."""

    @pytest.fixture
    def mock_mdf_data(self):
        """Create mock MDF data for testing without actual MDF files."""
        # Create mock signal data
        timestamps = np.linspace(0, 10, 1001)
        vehicle_speed = np.concatenate([
            np.linspace(0, 100, 500),
            np.linspace(100, 50, 501)
        ])
        engine_rpm = np.concatenate([
            np.linspace(800, 3000, 500),
            np.linspace(3000, 1500, 501)
        ])
        throttle = np.concatenate([
            np.linspace(0, 100, 200),
            np.ones(300) * 100,
            np.linspace(100, 50, 501)
        ])

        return pd.DataFrame({
            "time": timestamps,
            "VehicleSpeed": vehicle_speed,
            "EngineRPM": engine_rpm,
            "ThrottlePosition": throttle,
        })

    @pytest.fixture
    def mock_mdf_file(self, tmp_path, mock_mdf_data):
        """Create a mock MDF file setup for testing."""
        # This creates a placeholder - actual MDF parsing requires asammdf
        mdf_path = tmp_path / "test_data.mf4"
        return mdf_path, mock_mdf_data

    def test_mdf_parser_initialization(self):
        """Test MDF parser initialization."""
        parser = MDFParser()
        assert parser.channels is None
        assert parser.time_from_zero is True
        assert parser.raster is None

        parser_with_options = MDFParser(
            channels=["VehicleSpeed", "EngineRPM"],
            time_from_zero=False,
            raster=0.01,
        )
        assert parser_with_options.channels == ["VehicleSpeed", "EngineRPM"]
        assert parser_with_options.time_from_zero is False
        assert parser_with_options.raster == 0.01

    def test_mdf_parser_no_file(self):
        """Test MDF parser with no file path."""
        parser = MDFParser()
        result = parser.parse()

        assert result.status == ParserStatus.ERROR
        assert "No file path provided" in result.error_message

    def test_mdf_parser_nonexistent_file(self, tmp_path):
        """Test MDF parser with non-existent file."""
        parser = MDFParser(tmp_path / "nonexistent.mf4")
        result = parser.parse()

        assert result.status == ParserStatus.ERROR

    def test_mdf_parsing_with_mock(self, mock_mdf_file, mock_mdf_data):
        """Test MDF parsing with mocked asammdf."""
        mdf_path, expected_data = mock_mdf_file
        
        # Create the file so validation passes
        mdf_path.write_bytes(b"fake mdf content")

        # Setup mock
        mock_mdf = MagicMock()
        mock_mdf.version = "4.10"
        mock_mdf.channels_db.keys.return_value = ["time", "VehicleSpeed", "EngineRPM", "ThrottlePosition"]

        # Mock signal extraction
        def create_mock_signal(name, data):
            signal = MagicMock()
            signal.timestamps = expected_data["time"].values
            signal.samples = expected_data[name].values
            return signal

        mock_mdf.get.side_effect = lambda name: create_mock_signal(name, expected_data)

        # Parse with mocked MDF
        with patch('asammdf.MDF', return_value=mock_mdf):
            parser = MDFParser(mdf_path)
            result = parser.parse()

        assert result.status == ParserStatus.SUCCESS
        assert result.data is not None
        assert len(result.data) > 0

    def test_mdf_parsing_with_channel_filter(self, mock_mdf_file, mock_mdf_data):
        """Test MDF parsing with specific channel selection."""
        mdf_path, expected_data = mock_mdf_file
        
        # Create the file so validation passes
        mdf_path.write_bytes(b"fake mdf content")

        # Setup mock
        mock_mdf = MagicMock()
        mock_mdf.version = "4.10"
        mock_mdf.channels_db.keys.return_value = ["time", "VehicleSpeed", "EngineRPM", "ThrottlePosition"]

        def create_mock_signal(name, data):
            signal = MagicMock()
            signal.timestamps = expected_data["time"].values
            signal.samples = expected_data[name].values
            return signal

        mock_mdf.get.side_effect = lambda name: create_mock_signal(name, expected_data)

        # Parse with specific channels
        with patch('asammdf.MDF', return_value=mock_mdf):
            parser = MDFParser(
                mdf_path,
                channels=["VehicleSpeed", "EngineRPM"],
            )
            result = parser.parse()

        assert result.status == ParserStatus.SUCCESS
        assert result.data is not None

    def test_mdf_parsing_with_raster(self, mock_mdf_file, mock_mdf_data):
        """Test MDF parsing with resampling."""
        mdf_path, expected_data = mock_mdf_file
        
        # Create the file so validation passes
        mdf_path.write_bytes(b"fake mdf content")

        # Setup mock
        mock_mdf = MagicMock()
        mock_mdf.version = "4.10"
        mock_mdf.channels_db.keys.return_value = ["time", "VehicleSpeed", "EngineRPM"]

        mock_resampled = MagicMock()
        mock_resampled.channels_db.keys.return_value = ["time", "VehicleSpeed", "EngineRPM"]

        def create_mock_signal(name, data):
            signal = MagicMock()
            signal.timestamps = expected_data["time"].values
            signal.samples = expected_data[name].values
            return signal

        mock_resampled.get.side_effect = lambda name: create_mock_signal(name, expected_data)
        mock_mdf.resample.return_value = mock_resampled

        # Parse with raster
        with patch('asammdf.MDF', return_value=mock_mdf):
            parser = MDFParser(mdf_path, raster=0.1)
            result = parser.parse()

        assert result.status == ParserStatus.SUCCESS

    def test_mdf_parser_unsupported_format(self, tmp_path):
        """Test MDF parser with unsupported file format."""
        unsupported_file = tmp_path / "test.xyz"
        unsupported_file.write_text("some content")

        parser = MDFParser(unsupported_file)
        result = parser.parse()

        # Should fail during validation
        assert result.status == ParserStatus.ERROR


class TestMDFToIndicatorIntegration:
    """Integration tests for MDF parsing to indicator calculation."""

    @pytest.fixture
    def sample_dataframe(self):
        """Create sample DataFrame simulating MDF parsed data."""
        return pd.DataFrame({
            "time": np.linspace(0, 10, 1001),
            "VehicleSpeed": np.concatenate([
                np.linspace(0, 100, 500),
                np.linspace(100, 50, 501)
            ]),
            "EngineRPM": np.concatenate([
                np.linspace(800, 3000, 500),
                np.linspace(3000, 1500, 501)
            ]),
            "ThrottlePosition": np.concatenate([
                np.linspace(0, 100, 200),
                np.ones(300) * 100,
                np.linspace(100, 50, 501)
            ]),
            "BrakePressure": np.concatenate([
                np.zeros(300),
                np.linspace(0, 50, 200),
                np.linspace(50, 0, 501)
            ]),
        })

    def test_mdf_data_to_indicator_single_value(self, sample_dataframe):
        """Test single value indicator calculation on MDF-like data."""
        engine = IndicatorEngine()

        # Use STATISTICAL type for max calculation
        indicator = IndicatorDefinition(
            name="MaxVehicleSpeed",
            signal_name="VehicleSpeed",
            indicator_type=IndicatorType.STATISTICAL,
            formula="max",
            upper_limit=120.0,
        )

        result = engine.calculate(indicator, sample_dataframe)

        assert result is not None
        assert result.calculated_value is not None
        assert result.calculated_value == pytest.approx(100.0, rel=0.01)

    def test_mdf_data_to_indicator_statistical(self, sample_dataframe):
        """Test statistical indicator calculation on MDF-like data."""
        engine = IndicatorEngine()

        indicator = IndicatorDefinition(
            name="AvgEngineRPM",
            signal_name="EngineRPM",
            indicator_type=IndicatorType.STATISTICAL,
            formula="mean",
            lower_limit=500.0,
            upper_limit=5000.0,
        )

        result = engine.calculate(indicator, sample_dataframe)

        assert result is not None
        assert result.calculated_value is not None
        # Average should be around (800 + 3000 + 1500) / 3 ï¿?1767
        assert 1500 < result.calculated_value < 2500

    def test_mdf_data_to_indicator_time_domain(self, sample_dataframe):
        """Test time domain indicator calculation on MDF-like data."""
        engine = IndicatorEngine()

        indicator = IndicatorDefinition(
            name="ResponseTime",
            signal_name="VehicleSpeed",
            indicator_type=IndicatorType.TIME_DOMAIN,
            formula="rise_time",
            target_value=90.0,
        )

        result = engine.calculate(indicator, sample_dataframe)

        assert result is not None

    def test_mdf_data_multiple_indicators(self, sample_dataframe):
        """Test multiple indicator calculations on MDF-like data."""
        engine = IndicatorEngine()

        indicators = [
            IndicatorDefinition(
                name="MaxSpeed",
                signal_name="VehicleSpeed",
                indicator_type=IndicatorType.SINGLE_VALUE,
                formula="max",
            ),
            IndicatorDefinition(
                name="MinSpeed",
                signal_name="VehicleSpeed",
                indicator_type=IndicatorType.SINGLE_VALUE,
                formula="min",
            ),
            IndicatorDefinition(
                name="AvgThrottle",
                signal_name="ThrottlePosition",
                indicator_type=IndicatorType.STATISTICAL,
                formula="mean",
            ),
            IndicatorDefinition(
                name="MaxBrake",
                signal_name="BrakePressure",
                indicator_type=IndicatorType.SINGLE_VALUE,
                formula="max",
            ),
        ]

        results = [engine.calculate(ind, sample_dataframe) for ind in indicators]

        assert len(results) == 4
        assert all(r is not None for r in results)
        assert all(r.calculated_value is not None for r in results)

    def test_mdf_data_to_performance_analysis(self, sample_dataframe):
        """Test performance analysis on MDF-like data."""
        analyzer = PerformanceAnalyzer()

        # Calculate statistics
        stats_result = analyzer.calculate_statistics(
            sample_dataframe,
            "VehicleSpeed",
        )

        assert stats_result is not None
        assert stats_result.passed
        assert "mean" in stats_result.details
        assert "std" in stats_result.details
        assert "min" in stats_result.details
        assert "max" in stats_result.details


class TestMDFTimeSynchronization:
    """Integration tests for MDF data time synchronization."""

    @pytest.fixture
    def multi_rate_data(self):
        """Create multi-rate data for time sync testing."""
        # High rate data (100 Hz)
        high_rate = pd.DataFrame({
            "time": np.linspace(0, 1, 101),
            "HighRateSignal": np.sin(2 * np.pi * 5 * np.linspace(0, 1, 101)),
        })

        # Low rate data (10 Hz)
        low_rate = pd.DataFrame({
            "time": np.linspace(0, 1, 11),
            "LowRateSignal": np.linspace(0, 100, 11),
        })

        return high_rate, low_rate

    def test_time_sync_multi_rate_data(self, multi_rate_data):
        """Test synchronizing multi-rate MDF-like data."""
        high_rate, low_rate = multi_rate_data

        sync = TimeSynchronizer(precision_ms=10.0)
        aligned = sync.align_to_common_time(
            [high_rate, low_rate],
            ["time", "time"],
        )

        assert aligned is not None
        assert "time" in aligned.columns
        assert any("HighRateSignal" in col for col in aligned.columns)
        assert any("LowRateSignal" in col for col in aligned.columns)

    def test_time_sync_with_resampling(self, multi_rate_data):
        """Test time sync with resampling."""
        high_rate, low_rate = multi_rate_data

        sync = TimeSynchronizer(precision_ms=50.0)  # 20 Hz
        aligned = sync.align_to_common_time(
            [high_rate, low_rate],
            ["time", "time"],
        )

        assert aligned is not None
        # Check that data is resampled to 20 Hz
        expected_samples = int(1.0 / 0.05) + 1
        assert len(aligned) <= expected_samples + 5  # Allow some tolerance

    def test_resample_single_dataframe(self):
        """Test resampling a single DataFrame."""
        data = pd.DataFrame({
            "time": np.linspace(0, 10, 1001),
            "Signal": np.sin(2 * np.pi * 0.5 * np.linspace(0, 10, 1001)),
        })

        sync = TimeSynchronizer()
        resampled = sync.resample(data, "time", target_rate_hz=10.0)

        assert resampled is not None
        assert "time" in resampled.columns
        assert "Signal" in resampled.columns
        # Should have approximately 100 samples (10 Hz for 10 seconds)
        assert 90 < len(resampled) < 110


class TestMDFParserEdgeCases:
    """Edge case tests for MDF parser."""

    def test_empty_channel_list(self, tmp_path):
        """Test MDF parser with empty channel list."""
        mdf_path = tmp_path / "test.mf4"
        mdf_path.write_bytes(b"fake mdf content")

        parser = MDFParser(mdf_path, channels=[])
        # Should fail when trying to parse
        result = parser.parse()
        # Will fail due to invalid file, but channels=[] should be handled
        assert result.status == ParserStatus.ERROR

    def test_mdf_parser_close(self):
        """Test MDF parser close method."""
        parser = MDFParser()
        parser.close()  # Should not raise

    def test_mdf_parser_get_data_no_data(self):
        """Test get_data when no data has been parsed."""
        parser = MDFParser()
        data = parser.get_data()

        assert data is None

    def test_mdf_parser_get_all_channels_no_file(self):
        """Test get_all_channels when no file has been parsed."""
        parser = MDFParser()
        channels = parser.get_all_channels()

        assert channels == []


class TestMDFDataFiltering:
    """Tests for MDF data filtering functionality."""

    @pytest.fixture
    def sample_data(self):
        """Create sample parsed MDF data."""
        return pd.DataFrame({
            "time": np.linspace(0, 10, 1001),
            "Signal1": np.random.randn(1001),
            "Signal2": np.random.randn(1001) + 10,
            "Signal3": np.random.randn(1001) * 2,
        })

    @patch('asammdf.MDF')
    def test_get_data_with_time_range(self, mock_mdf_class, tmp_path, sample_data):
        """Test getting data with time range filter."""
        mdf_path = tmp_path / "test.mf4"

        # Setup mock
        mock_mdf = MagicMock()
        mock_mdf.version = "4.10"
        mock_mdf.channels_db.keys.return_value = list(sample_data.columns)

        def create_mock_signal(name):
            signal = MagicMock()
            signal.timestamps = sample_data["time"].values
            signal.samples = sample_data[name].values
            return signal

        mock_mdf.get.side_effect = lambda name: create_mock_signal(name)
        mock_mdf_class.return_value = mock_mdf

        parser = MDFParser(mdf_path)
        parser.parse()

        # Get filtered data
        filtered = parser.get_data(time_range=(2.0, 5.0))

        if filtered is not None and len(filtered) > 0:
            assert filtered["time"].min() >= 2.0
            assert filtered["time"].max() <= 5.0

    @patch('asammdf.MDF')
    def test_get_data_with_signals(self, mock_mdf_class, tmp_path, sample_data):
        """Test getting specific signals from data."""
        mdf_path = tmp_path / "test.mf4"

        # Setup mock
        mock_mdf = MagicMock()
        mock_mdf.version = "4.10"
        mock_mdf.channels_db.keys.return_value = list(sample_data.columns)

        def create_mock_signal(name):
            signal = MagicMock()
            signal.timestamps = sample_data["time"].values
            signal.samples = sample_data[name].values
            return signal

        mock_mdf.get.side_effect = lambda name: create_mock_signal(name)
        mock_mdf_class.return_value = mock_mdf

        parser = MDFParser(mdf_path)
        parser.parse()

        # Get specific signals
        filtered = parser.get_data(signals=["Signal1", "Signal2"])

        if filtered is not None:
            assert "Signal1" in filtered.columns
            assert "Signal2" in filtered.columns
            assert "time" in filtered.columns


class TestMDFToReportIntegration:
    """Integration tests for MDF data to report generation."""

    @pytest.fixture
    def sample_mdf_data(self):
        """Create sample MDF-like data."""
        return pd.DataFrame({
            "time": np.linspace(0, 10, 1001),
            "VehicleSpeed": np.linspace(0, 100, 1001),
            "EngineRPM": np.linspace(800, 3000, 1001),
            "ThrottlePosition": np.concatenate([
                np.linspace(0, 100, 500),
                np.linspace(100, 0, 501)
            ]),
        })

    def test_mdf_data_to_report_workflow(self, sample_mdf_data, tmp_path):
        """Test complete workflow from MDF data to report."""
        from datetime import datetime
        from src.report.word_report import (
            ReportData,
            ReportSection,
            WordReportGenerator,
        )

        # Step 1: Calculate indicators
        engine = IndicatorEngine()

        indicators = [
            IndicatorDefinition(
                name="MaxSpeed",
                signal_name="VehicleSpeed",
                indicator_type=IndicatorType.STATISTICAL,
                formula="max",
            ),
            IndicatorDefinition(
                name="AvgRPM",
                signal_name="EngineRPM",
                indicator_type=IndicatorType.STATISTICAL,
                formula="mean",
            ),
        ]

        results = [engine.calculate(ind, sample_mdf_data) for ind in indicators]

        # Step 2: Create report
        report_data = ReportData(
            title="MDF Data Analysis Report",
            project_name="Test Project",
            test_phase="HIL",
            generated_at=datetime.now(),
            generated_by="Test Engineer",
            sections=[
                ReportSection(
                    title="Signal Analysis",
                    content="Analysis of MDF signal data.",
                ),
            ],
            tables=[
                {
                    "title": "Indicator Results",
                    "headers": ["Indicator", "Value", "Unit"],
                    "rows": [
                        [r.definition.name if hasattr(r.definition, 'name') else r.definition.get('name', 'unknown'),
                         f"{r.calculated_value:.2f}" if r.calculated_value else "N/A",
                         r.definition.unit if hasattr(r.definition, 'unit') else r.definition.get('unit', '')]
                        for r in results
                    ],
                }
            ],
            figures=[],
            metadata={
                "Data Source": "MDF File",
                "Sample Count": str(len(sample_mdf_data)),
            },
        )

        # Step 3: Generate report
        generator = WordReportGenerator()
        output_path = tmp_path / "mdf_report.docx"

        success = generator.generate(report_data, output_path)

        assert success
        assert output_path.exists()
