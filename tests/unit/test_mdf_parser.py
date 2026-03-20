"""Unit tests for MDF parser module."""

import sys
import numpy as np
import pandas as pd
import pytest
from pathlib import Path

from src.parsers.mdf_parser import MDFParser
from src.parsers.base_parser import ParserStatus


class TestMDFParser:
    """Tests for MDFParser class."""

    def test_supported_extensions(self):
        """Test supported file extensions."""
        assert ".mdf" in MDFParser.SUPPORTED_EXTENSIONS
        assert ".mf4" in MDFParser.SUPPORTED_EXTENSIONS
        assert ".dat" in MDFParser.SUPPORTED_EXTENSIONS

    def test_can_parse_mdf(self, tmp_path):
        """Test can_parse method for MDF files."""
        mdf_path = tmp_path / "test.mdf"
        mdf_path.write_bytes(b"MDF     ")  # MDF header
        assert MDFParser.can_parse(mdf_path)

    def test_can_parse_mf4(self, tmp_path):
        """Test can_parse method for MF4 files."""
        mf4_path = tmp_path / "test.mf4"
        mf4_path.write_bytes(b"MDF     ")
        assert MDFParser.can_parse(mf4_path)

    def test_can_parse_unsupported(self, tmp_path):
        """Test can_parse method for unsupported files."""
        bin_path = tmp_path / "test.bin"
        bin_path.write_bytes(b"\x00\x01")
        assert not MDFParser.can_parse(bin_path)

    def test_parse_nonexistent_file(self, tmp_path):
        """Test parsing non-existent file."""
        parser = MDFParser(tmp_path / "nonexistent.mdf")
        result = parser.parse()

        assert not result.is_success
        assert result.status == ParserStatus.ERROR
        assert "not found" in result.error_message.lower()

    def test_parse_empty_file(self, tmp_path):
        """Test parsing empty file."""
        empty_path = tmp_path / "empty.mdf"
        empty_path.write_bytes(b"")
        parser = MDFParser(empty_path)
        result = parser.parse()

        assert result.status == ParserStatus.ERROR

    def test_get_signal_list_before_parse(self):
        """Test getting signal list before parsing."""
        parser = MDFParser()
        signals = parser.get_signal_list()
        assert signals == []

    def test_get_data_before_parse(self):
        """Test getting data before parsing."""
        parser = MDFParser()
        assert parser.get_data() is None

    def test_get_all_channels_before_parse(self):
        """Test getting all channels before parsing."""
        parser = MDFParser()
        channels = parser.get_all_channels()
        assert channels == []

    def test_init_with_channels(self):
        """Test initialization with channel list."""
        parser = MDFParser(channels=["channel1", "channel2"])
        assert parser.channels == ["channel1", "channel2"]

    def test_init_with_raster(self):
        """Test initialization with raster."""
        parser = MDFParser(raster=0.01)
        assert parser.raster == 0.01

    def test_init_with_time_from_zero(self):
        """Test initialization with time_from_zero option."""
        parser = MDFParser(time_from_zero=True)
        assert parser.time_from_zero is True

        parser2 = MDFParser(time_from_zero=False)
        assert parser2.time_from_zero is False

    def test_close_without_file(self):
        """Test close method without opened file."""
        parser = MDFParser()
        parser.close()  # Should not raise

    def test_parse_with_mock_mdf(self, tmp_path, monkeypatch):
        """Test parsing with mocked MDF data."""
        # Create a mock MDF file
        mdf_path = tmp_path / "test.mdf"
        mdf_path.write_bytes(b"MDF     " * 100)

        # Mock the MDF class
        class MockSignal:
            def __init__(self, samples, timestamps):
                self.samples = samples
                self.timestamps = timestamps

        class MockMDF:
            version = "4.10"
            channels_db = {"time": None, "signal1": None, "signal2": None}

            def get(self, channel):
                if channel == "signal1":
                    return MockSignal(
                        np.array([1.0, 2.0, 3.0]),
                        np.array([0.0, 0.1, 0.2])
                    )
                elif channel == "signal2":
                    return MockSignal(
                        np.array([10.0, 20.0, 30.0]),
                        np.array([0.0, 0.1, 0.2])
                    )
                return None

            def resample(self, raster):
                return self

            def close(self):
                pass

        # Mock asammdf module
        import types
        mock_asammdf = types.ModuleType('asammdf')
        mock_asammdf.MDF = lambda file_path: MockMDF()
        monkeypatch.setitem(sys.modules, 'asammdf', mock_asammdf)

        parser = MDFParser(mdf_path, channels=["signal1", "signal2"])
        result = parser.parse()

        assert result.is_success
        assert result.status == ParserStatus.SUCCESS
        assert "signal1" in parser.get_signal_list()
        assert "signal2" in parser.get_signal_list()

    def test_get_data_filtered(self, tmp_path, monkeypatch):
        """Test getting filtered data."""
        mdf_path = tmp_path / "test.mdf"
        mdf_path.write_bytes(b"MDF     " * 100)

        class MockSignal:
            def __init__(self, samples, timestamps):
                self.samples = samples
                self.timestamps = timestamps

        class MockMDF:
            version = "4.10"
            channels_db = {"time": None, "signal1": None, "signal2": None}

            def get(self, channel):
                if channel == "signal1":
                    return MockSignal(
                        np.array([1.0, 2.0, 3.0, 4.0, 5.0]),
                        np.array([0.0, 0.1, 0.2, 0.3, 0.4])
                    )
                return None

            def resample(self, raster):
                return self

            def close(self):
                pass

        import types
        mock_asammdf = types.ModuleType('asammdf')
        mock_asammdf.MDF = lambda x: MockMDF()
        monkeypatch.setitem(sys.modules, 'asammdf', mock_asammdf)

        parser = MDFParser(mdf_path, channels=["signal1"])
        parser.parse()

        filtered = parser.get_data(signals=["signal1"], time_range=(0.1, 0.3))
        assert filtered is not None
        assert "signal1" in filtered.columns

    def test_parse_no_channels_found(self, tmp_path, monkeypatch):
        """Test parsing when no channels are found."""
        mdf_path = tmp_path / "test.mdf"
        mdf_path.write_bytes(b"MDF     " * 100)

        class MockMDF:
            version = "4.10"
            channels_db = {}

            def get(self, channel):
                return None

            def resample(self, raster):
                return self

            def close(self):
                pass

        import types
        mock_asammdf = types.ModuleType('asammdf')
        mock_asammdf.MDF = lambda x: MockMDF()
        monkeypatch.setitem(sys.modules, 'asammdf', mock_asammdf)

        parser = MDFParser(mdf_path)
        result = parser.parse()

        assert result.status == ParserStatus.ERROR

    def test_parse_missing_asammdf(self, tmp_path, monkeypatch):
        """Test parsing when asammdf is not installed."""
        mdf_path = tmp_path / "test.mdf"
        mdf_path.write_bytes(b"MDF     " * 100)

        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "asammdf":
                raise ImportError("asammdf not installed")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)

        parser = MDFParser(mdf_path)
        result = parser.parse()

        assert result.status == ParserStatus.ERROR
        assert "asammdf" in result.error_message.lower()
