"""Unit tests for CAN parser module."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pandas as pd
import pytest

from src.parsers.can_parser import CANParser
from src.parsers.base_parser import ParserStatus


class TestCANParserInit:
    """Tests for CANParser initialization."""

    def test_default_init(self):
        """Test default initialization."""
        parser = CANParser()
        assert parser.file_path is None
        assert parser.dbc_path is None
        assert parser.ignore_invalid_frames is True

    def test_init_with_file_path(self, tmp_path):
        """Test initialization with file path."""
        blf_path = tmp_path / "test.blf"
        blf_path.write_bytes(b"test")
        parser = CANParser(file_path=blf_path)
        assert parser.file_path == blf_path

    def test_init_with_dbc_path(self, tmp_path):
        """Test initialization with DBC path."""
        dbc_path = tmp_path / "test.dbc"
        dbc_path.write_text('VERSION ""')
        parser = CANParser(dbc_path=dbc_path)
        assert parser.dbc_path == dbc_path

    def test_init_with_ignore_invalid_frames_false(self):
        """Test initialization with ignore_invalid_frames=False."""
        parser = CANParser(ignore_invalid_frames=False)
        assert parser.ignore_invalid_frames is False


class TestCANParserSupportedExtensions:
    """Tests for supported file extensions."""

    def test_supported_extensions(self):
        """Test supported file extensions."""
        assert ".blf" in CANParser.SUPPORTED_EXTENSIONS
        assert ".asc" in CANParser.SUPPORTED_EXTENSIONS

    def test_can_parse_blf(self, tmp_path):
        """Test can_parse method for BLF files."""
        blf_path = tmp_path / "test.blf"
        blf_path.write_bytes(b"test")
        assert CANParser.can_parse(blf_path)

    def test_can_parse_asc(self, tmp_path):
        """Test can_parse method for ASC files."""
        asc_path = tmp_path / "test.asc"
        asc_path.write_text("test")
        assert CANParser.can_parse(asc_path)

    def test_can_parse_unsupported(self, tmp_path):
        """Test can_parse method for unsupported files."""
        bin_path = tmp_path / "test.bin"
        bin_path.write_bytes(b"\x00\x01")
        assert not CANParser.can_parse(bin_path)

    def test_can_parse_uppercase_extension(self, tmp_path):
        """Test can_parse with uppercase extension."""
        blf_path = tmp_path / "test.BLF"
        blf_path.write_bytes(b"test")
        assert CANParser.can_parse(blf_path)


class TestCANParserParse:
    """Tests for parse method."""

    def test_parse_no_file_path(self):
        """Test parsing without file path."""
        parser = CANParser()
        result = parser.parse()

        assert not result.is_success
        assert result.status == ParserStatus.ERROR
        assert "No file path provided" in result.error_message

    def test_parse_nonexistent_file(self, tmp_path):
        """Test parsing non-existent file."""
        parser = CANParser(file_path=tmp_path / "nonexistent.blf")
        result = parser.parse()

        assert not result.is_success
        assert result.status == ParserStatus.ERROR
        assert "not found" in result.error_message.lower()

    def test_parse_directory_instead_of_file(self, tmp_path):
        """Test parsing a directory path."""
        parser = CANParser(file_path=tmp_path)
        result = parser.parse()

        assert not result.is_success
        assert result.status == ParserStatus.ERROR
        assert "not a file" in result.error_message.lower()

    def test_parse_unsupported_extension(self, tmp_path):
        """Test parsing unsupported file extension."""
        bin_path = tmp_path / "test.bin"
        bin_path.write_bytes(b"\x00\x01")
        parser = CANParser(file_path=bin_path)
        result = parser.parse()

        assert not result.is_success
        assert result.status == ParserStatus.ERROR
        assert "Unsupported file type" in result.error_message


class TestCANParserBLF:
    """Tests for BLF file parsing."""

    def _create_mock_can(self):
        """Create a mock can module."""
        mock_can = MagicMock()
        mock_msg = Mock()
        mock_msg.timestamp = 1.5
        mock_msg.arbitration_id = 0x123
        mock_msg.dlc = 8
        mock_msg.data = bytes([1, 2, 3, 4, 5, 6, 7, 8])
        mock_msg.is_extended_id = False
        mock_msg.channel = 1

        mock_reader = Mock()
        mock_reader.__iter__ = Mock(return_value=iter([mock_msg]))
        mock_can.BLFReader.return_value = mock_reader
        return mock_can, mock_msg

    def test_parse_blf_success(self, tmp_path):
        """Test successful BLF parsing."""
        blf_path = tmp_path / "test.blf"
        blf_path.write_bytes(b"test")

        mock_can, _ = self._create_mock_can()
        with patch.dict(sys.modules, {"can": mock_can}):
            parser = CANParser(file_path=blf_path)
            result = parser.parse()

            assert result.is_success
            assert result.status == ParserStatus.SUCCESS
            assert result.data is not None
            assert len(result.data) == 1
            assert "timestamp" in result.data.columns
            assert "can_id" in result.data.columns

    def test_parse_blf_with_multiple_messages(self, tmp_path):
        """Test BLF parsing with multiple messages."""
        blf_path = tmp_path / "test.blf"
        blf_path.write_bytes(b"test")

        mock_can = MagicMock()
        mock_msgs = []
        for i in range(5):
            msg = Mock()
            msg.timestamp = 1.0 + i * 0.1
            msg.arbitration_id = 0x100 + i
            msg.dlc = 8
            msg.data = bytes([i] * 8)
            msg.is_extended_id = False
            msg.channel = 1
            mock_msgs.append(msg)

        mock_reader = Mock()
        mock_reader.__iter__ = Mock(return_value=iter(mock_msgs))
        mock_can.BLFReader.return_value = mock_reader

        with patch.dict(sys.modules, {"can": mock_can}):
            parser = CANParser(file_path=blf_path)
            result = parser.parse()

            assert result.is_success
            assert len(result.data) == 5

    def test_parse_blf_empty_file(self, tmp_path):
        """Test BLF parsing with empty file."""
        blf_path = tmp_path / "test.blf"
        blf_path.write_bytes(b"test")

        mock_can = MagicMock()
        mock_reader = Mock()
        mock_reader.__iter__ = Mock(return_value=iter([]))
        mock_can.BLFReader.return_value = mock_reader

        with patch.dict(sys.modules, {"can": mock_can}):
            parser = CANParser(file_path=blf_path)
            result = parser.parse()

            assert not result.is_success
            assert "empty" in result.error_message.lower() or "failed" in result.error_message.lower()

    def test_parse_blf_extended_id(self, tmp_path):
        """Test BLF parsing with extended CAN ID."""
        blf_path = tmp_path / "test.blf"
        blf_path.write_bytes(b"test")

        mock_can = MagicMock()
        mock_msg = Mock()
        mock_msg.timestamp = 1.0
        mock_msg.arbitration_id = 0x12345678
        mock_msg.dlc = 8
        mock_msg.data = bytes([1, 2, 3, 4, 5, 6, 7, 8])
        mock_msg.is_extended_id = True
        mock_msg.channel = 1

        mock_reader = Mock()
        mock_reader.__iter__ = Mock(return_value=iter([mock_msg]))
        mock_can.BLFReader.return_value = mock_reader

        with patch.dict(sys.modules, {"can": mock_can}):
            parser = CANParser(file_path=blf_path)
            result = parser.parse()

            assert result.is_success
            assert result.data.iloc[0]["is_extended"] == True

    def test_parse_blf_no_data(self, tmp_path):
        """Test BLF parsing with message without data."""
        blf_path = tmp_path / "test.blf"
        blf_path.write_bytes(b"test")

        mock_can = MagicMock()
        mock_msg = Mock()
        mock_msg.timestamp = 1.0
        mock_msg.arbitration_id = 0x123
        mock_msg.dlc = 0
        mock_msg.data = None
        mock_msg.is_extended_id = False
        mock_msg.channel = 1

        mock_reader = Mock()
        mock_reader.__iter__ = Mock(return_value=iter([mock_msg]))
        mock_can.BLFReader.return_value = mock_reader

        with patch.dict(sys.modules, {"can": mock_can}):
            parser = CANParser(file_path=blf_path)
            result = parser.parse()

            assert result.is_success
            assert result.data.iloc[0]["data"] == ""

    def test_parse_blf_runtime_error(self, tmp_path):
        """Test BLF parsing with runtime error."""
        blf_path = tmp_path / "test.blf"
        blf_path.write_bytes(b"test")

        mock_can = MagicMock()
        mock_can.BLFReader.side_effect = RuntimeError("BLF read error")

        with patch.dict(sys.modules, {"can": mock_can}):
            parser = CANParser(file_path=blf_path)
            result = parser.parse()

            assert not result.is_success
            assert result.status == ParserStatus.ERROR


class TestCANParserASC:
    """Tests for ASC file parsing."""

    def test_parse_asc_success(self, tmp_path):
        """Test successful ASC parsing."""
        asc_path = tmp_path / "test.asc"
        asc_path.write_text(
            "date Wed Mar 18 03:00:00 2026\n"
            "base hex timestamps absolute\n"
            "  1.000000 1  123x   Rx   d 8 01 02 03 04 05 06 07 08\n"
        )

        mock_can = MagicMock()
        mock_msg = Mock()
        mock_msg.timestamp = 1.0
        mock_msg.arbitration_id = 0x123
        mock_msg.dlc = 8
        mock_msg.data = bytes([1, 2, 3, 4, 5, 6, 7, 8])
        mock_msg.is_extended_id = False
        mock_msg.channel = 1

        mock_reader = Mock()
        mock_reader.__iter__ = Mock(return_value=iter([mock_msg]))
        mock_can.ASCReader.return_value = mock_reader

        with patch.dict(sys.modules, {"can": mock_can}):
            parser = CANParser(file_path=asc_path)
            result = parser.parse()

            assert result.is_success

    def test_parse_asc_empty_file(self, tmp_path):
        """Test ASC parsing with empty file."""
        asc_path = tmp_path / "test.asc"
        asc_path.write_text("")

        mock_can = MagicMock()
        mock_reader = Mock()
        mock_reader.__iter__ = Mock(return_value=iter([]))
        mock_can.ASCReader.return_value = mock_reader

        with patch.dict(sys.modules, {"can": mock_can}):
            parser = CANParser(file_path=asc_path)
            result = parser.parse()

            assert not result.is_success

    def test_parse_asc_runtime_error(self, tmp_path):
        """Test ASC parsing with runtime error."""
        asc_path = tmp_path / "test.asc"
        asc_path.write_text("test")

        mock_can = MagicMock()
        mock_can.ASCReader.side_effect = RuntimeError("ASC read error")

        with patch.dict(sys.modules, {"can": mock_can}):
            parser = CANParser(file_path=asc_path)
            result = parser.parse()

            assert not result.is_success


class TestCANParserImportError:
    """Tests for import error handling."""

    def test_parse_import_error_can(self, tmp_path):
        """Test parsing when can module is not installed."""
        blf_path = tmp_path / "test.blf"
        blf_path.write_bytes(b"test")

        with patch.dict(sys.modules, {"can": None}):
            parser = CANParser(file_path=blf_path)
            result = parser.parse()

            assert not result.is_success
            assert result.status == ParserStatus.ERROR

    def test_parse_blf_import_error_in_try_block(self, tmp_path):
        """Test BLF parsing when import fails inside try block."""
        blf_path = tmp_path / "test.blf"
        blf_path.write_bytes(b"test")

        mock_can = MagicMock()
        mock_can.BLFReader.side_effect = ModuleNotFoundError("No module named 'can'")

        with patch.dict(sys.modules, {"can": mock_can}):
            parser = CANParser(file_path=blf_path)
            result = parser.parse()

            assert not result.is_success
            assert result.status == ParserStatus.ERROR


class TestCANParserGetSignalList:
    """Tests for get_signal_list method."""

    def test_get_signal_list_after_parse(self, tmp_path):
        """Test get_signal_list after parsing."""
        blf_path = tmp_path / "test.blf"
        blf_path.write_bytes(b"test")

        mock_can = MagicMock()
        mock_msg = Mock()
        mock_msg.timestamp = 1.0
        mock_msg.arbitration_id = 0x123
        mock_msg.dlc = 8
        mock_msg.data = bytes([1, 2, 3, 4, 5, 6, 7, 8])
        mock_msg.is_extended_id = False
        mock_msg.channel = 1

        mock_reader = Mock()
        mock_reader.__iter__ = Mock(return_value=iter([mock_msg]))
        mock_can.BLFReader.return_value = mock_reader

        with patch.dict(sys.modules, {"can": mock_can}):
            parser = CANParser(file_path=blf_path)
            result = parser.parse()
            signals = parser.get_signal_list()

            assert isinstance(signals, list)

    def test_get_signal_list_returns_copy(self, tmp_path):
        """Test that get_signal_list returns a copy."""
        blf_path = tmp_path / "test.blf"
        blf_path.write_bytes(b"test")

        mock_can = MagicMock()
        mock_msg = Mock()
        mock_msg.timestamp = 1.0
        mock_msg.arbitration_id = 0x123
        mock_msg.dlc = 8
        mock_msg.data = bytes([1, 2, 3, 4, 5, 6, 7, 8])
        mock_msg.is_extended_id = False
        mock_msg.channel = 1

        mock_reader = Mock()
        mock_reader.__iter__ = Mock(return_value=iter([mock_msg]))
        mock_can.BLFReader.return_value = mock_reader

        with patch.dict(sys.modules, {"can": mock_can}):
            parser = CANParser(file_path=blf_path)
            parser.parse()
            signals1 = parser.get_signal_list()
            signals2 = parser.get_signal_list()
            assert signals1 is not signals2


class TestCANParserGetData:
    """Tests for get_data method."""

    def test_get_data_after_parse(self, tmp_path):
        """Test get_data after parsing."""
        blf_path = tmp_path / "test.blf"
        blf_path.write_bytes(b"test")

        mock_can = MagicMock()
        mock_msg = Mock()
        mock_msg.timestamp = 1.0
        mock_msg.arbitration_id = 0x123
        mock_msg.dlc = 8
        mock_msg.data = bytes([1, 2, 3, 4, 5, 6, 7, 8])
        mock_msg.is_extended_id = False
        mock_msg.channel = 1

        mock_reader = Mock()
        mock_reader.__iter__ = Mock(return_value=iter([mock_msg]))
        mock_can.BLFReader.return_value = mock_reader

        with patch.dict(sys.modules, {"can": mock_can}):
            parser = CANParser(file_path=blf_path)
            parser.parse()
            data = parser.get_data()

            assert data is not None
            assert isinstance(data, pd.DataFrame)

    def test_get_data_filtered_by_signals(self, tmp_path):
        """Test get_data with signal filter."""
        blf_path = tmp_path / "test.blf"
        blf_path.write_bytes(b"test")

        mock_can = MagicMock()
        mock_msg = Mock()
        mock_msg.timestamp = 1.0
        mock_msg.arbitration_id = 0x123
        mock_msg.dlc = 8
        mock_msg.data = bytes([1, 2, 3, 4, 5, 6, 7, 8])
        mock_msg.is_extended_id = False
        mock_msg.channel = 1

        mock_reader = Mock()
        mock_reader.__iter__ = Mock(return_value=iter([mock_msg]))
        mock_can.BLFReader.return_value = mock_reader

        with patch.dict(sys.modules, {"can": mock_can}):
            parser = CANParser(file_path=blf_path)
            parser.parse()
            data = parser.get_data(signals=["can_id"])

            assert data is not None
            assert "can_id" in data.columns

    def test_get_data_filtered_by_time_range(self, tmp_path):
        """Test get_data with time range filter."""
        blf_path = tmp_path / "test.blf"
        blf_path.write_bytes(b"test")

        mock_can = MagicMock()
        mock_msgs = []
        for i in range(5):
            msg = Mock()
            msg.timestamp = 1.0 + i * 0.5
            msg.arbitration_id = 0x100 + i
            msg.dlc = 8
            msg.data = bytes([i] * 8)
            msg.is_extended_id = False
            msg.channel = 1
            mock_msgs.append(msg)

        mock_reader = Mock()
        mock_reader.__iter__ = Mock(return_value=iter(mock_msgs))
        mock_can.BLFReader.return_value = mock_reader

        with patch.dict(sys.modules, {"can": mock_can}):
            parser = CANParser(file_path=blf_path)
            parser.parse()
            data = parser.get_data(start_time=1.0, end_time=2.0)

            assert data is not None

    def test_get_data_filtered_by_signals_and_time(self, tmp_path):
        """Test get_data with signal and time filters."""
        blf_path = tmp_path / "test.blf"
        blf_path.write_bytes(b"test")

        mock_can = MagicMock()
        mock_msg = Mock()
        mock_msg.timestamp = 1.5
        mock_msg.arbitration_id = 0x123
        mock_msg.dlc = 8
        mock_msg.data = bytes([1, 2, 3, 4, 5, 6, 7, 8])
        mock_msg.is_extended_id = False
        mock_msg.channel = 1

        mock_reader = Mock()
        mock_reader.__iter__ = Mock(return_value=iter([mock_msg]))
        mock_can.BLFReader.return_value = mock_reader

        with patch.dict(sys.modules, {"can": mock_can}):
            parser = CANParser(file_path=blf_path)
            parser.parse()
            data = parser.get_data(signals=["can_id"], start_time=1.0, end_time=2.0)

            assert data is not None


class TestCANParserMetadata:
    """Tests for metadata."""

    def test_metadata_after_parse(self, tmp_path):
        """Test metadata after parsing."""
        blf_path = tmp_path / "test.blf"
        blf_path.write_bytes(b"test")

        mock_can = MagicMock()
        mock_msg = Mock()
        mock_msg.timestamp = 1.0
        mock_msg.arbitration_id = 0x123
        mock_msg.dlc = 8
        mock_msg.data = bytes([1, 2, 3, 4, 5, 6, 7, 8])
        mock_msg.is_extended_id = False
        mock_msg.channel = 1

        mock_reader = Mock()
        mock_reader.__iter__ = Mock(return_value=iter([mock_msg]))
        mock_can.BLFReader.return_value = mock_reader

        with patch.dict(sys.modules, {"can": mock_can}):
            parser = CANParser(file_path=blf_path)
            result = parser.parse()

            assert result.metadata is not None
            assert "file_name" in result.metadata

    def test_metadata_file_type(self, tmp_path):
        """Test metadata file type."""
        blf_path = tmp_path / "test.blf"
        blf_path.write_bytes(b"test")

        mock_can = MagicMock()
        mock_msg = Mock()
        mock_msg.timestamp = 1.0
        mock_msg.arbitration_id = 0x123
        mock_msg.dlc = 8
        mock_msg.data = bytes([1, 2, 3, 4, 5, 6, 7, 8])
        mock_msg.is_extended_id = False
        mock_msg.channel = 1

        mock_reader = Mock()
        mock_reader.__iter__ = Mock(return_value=iter([mock_msg]))
        mock_can.BLFReader.return_value = mock_reader

        with patch.dict(sys.modules, {"can": mock_can}):
            parser = CANParser(file_path=blf_path)
            result = parser.parse()

            assert result.metadata["file_type"] == ".blf"

    def test_metadata_time_range(self, tmp_path):
        """Test metadata time range."""
        blf_path = tmp_path / "test.blf"
        blf_path.write_bytes(b"test")

        mock_can = MagicMock()
        mock_msg = Mock()
        mock_msg.timestamp = 1.5
        mock_msg.arbitration_id = 0x123
        mock_msg.dlc = 8
        mock_msg.data = bytes([1, 2, 3, 4, 5, 6, 7, 8])
        mock_msg.is_extended_id = False
        mock_msg.channel = 1

        mock_reader = Mock()
        mock_reader.__iter__ = Mock(return_value=iter([mock_msg]))
        mock_can.BLFReader.return_value = mock_reader

        with patch.dict(sys.modules, {"can": mock_can}):
            parser = CANParser(file_path=blf_path)
            result = parser.parse()

            assert "time_range" in result.metadata
            assert result.metadata["time_range"]["start"] == 1.5

    def test_metadata_dbc_file(self, tmp_path):
        """Test metadata DBC file."""
        blf_path = tmp_path / "test.blf"
        blf_path.write_bytes(b"test")
        dbc_path = tmp_path / "test.dbc"
        dbc_path.write_text('VERSION ""')

        mock_can = MagicMock()
        mock_msg = Mock()
        mock_msg.timestamp = 1.0
        mock_msg.arbitration_id = 0x123
        mock_msg.dlc = 8
        mock_msg.data = bytes([1, 2, 3, 4, 5, 6, 7, 8])
        mock_msg.is_extended_id = False
        mock_msg.channel = 1

        mock_reader = Mock()
        mock_reader.__iter__ = Mock(return_value=iter([mock_msg]))
        mock_can.BLFReader.return_value = mock_reader

        mock_cantools = MagicMock()
        mock_cantools.database.load_file.return_value = MagicMock()

        with patch.dict(sys.modules, {"can": mock_can, "cantools": mock_cantools}):
            parser = CANParser(file_path=blf_path, dbc_path=dbc_path)
            result = parser.parse()

            assert result.metadata["dbc_file"] is not None


class TestCANParserTimestamp:
    """Tests for timestamp handling."""

    def test_timestamp_relative_time(self, tmp_path):
        """Test timestamp relative time."""
        blf_path = tmp_path / "test.blf"
        blf_path.write_bytes(b"test")

        mock_can = MagicMock()
        mock_msgs = []
        for i in range(3):
            msg = Mock()
            msg.timestamp = 10.0 + i * 0.5
            msg.arbitration_id = 0x100 + i
            msg.dlc = 8
            msg.data = bytes([i] * 8)
            msg.is_extended_id = False
            msg.channel = 1
            mock_msgs.append(msg)

        mock_reader = Mock()
        mock_reader.__iter__ = Mock(return_value=iter(mock_msgs))
        mock_can.BLFReader.return_value = mock_reader

        with patch.dict(sys.modules, {"can": mock_can}):
            parser = CANParser(file_path=blf_path)
            result = parser.parse()

            assert result.is_success
            assert result.data.iloc[0]["timestamp"] == 10.0


class TestCANParserPathOverride:
    """Tests for path override."""

    def test_parse_with_path_override(self, tmp_path):
        """Test parse with path override."""
        blf_path1 = tmp_path / "test1.blf"
        blf_path1.write_bytes(b"test1")
        blf_path2 = tmp_path / "test2.blf"
        blf_path2.write_bytes(b"test2")

        mock_can = MagicMock()
        mock_msg = Mock()
        mock_msg.timestamp = 1.0
        mock_msg.arbitration_id = 0x123
        mock_msg.dlc = 8
        mock_msg.data = bytes([1, 2, 3, 4, 5, 6, 7, 8])
        mock_msg.is_extended_id = False
        mock_msg.channel = 1

        mock_reader = Mock()
        mock_reader.__iter__ = Mock(return_value=iter([mock_msg]))
        mock_can.BLFReader.return_value = mock_reader

        with patch.dict(sys.modules, {"can": mock_can}):
            parser = CANParser(file_path=blf_path1)
            result = parser.parse(file_path=blf_path2)

            assert result.is_success
            assert result.metadata["file_name"] == "test2.blf"


class TestCANParserDBC:
    """Tests for DBC file handling."""

    def test_parse_with_dbc_load_failure(self, tmp_path):
        """Test parsing when DBC file fails to load."""
        blf_path = tmp_path / "test.blf"
        blf_path.write_bytes(b"test")
        dbc_path = tmp_path / "test.dbc"
        dbc_path.write_text("invalid dbc content")

        mock_can = MagicMock()
        mock_msg = Mock()
        mock_msg.timestamp = 1.0
        mock_msg.arbitration_id = 0x123
        mock_msg.dlc = 8
        mock_msg.data = bytes([1, 2, 3, 4, 5, 6, 7, 8])
        mock_msg.is_extended_id = False
        mock_msg.channel = 1

        mock_reader = Mock()
        mock_reader.__iter__ = Mock(return_value=iter([mock_msg]))
        mock_can.BLFReader.return_value = mock_reader

        mock_cantools = MagicMock()
        mock_cantools.database.load_file.side_effect = Exception("DBC parse error")

        with patch.dict(sys.modules, {"can": mock_can, "cantools": mock_cantools}):
            parser = CANParser(file_path=blf_path, dbc_path=dbc_path)
            result = parser.parse()

            # Should succeed with warning
            assert result.is_success
            assert result.warnings is not None
            assert "Failed to load DBC file" in result.warnings[0]

    def test_parse_with_dbc_decode_success(self, tmp_path):
        """Test parsing with DBC decoding."""
        blf_path = tmp_path / "test.blf"
        blf_path.write_bytes(b"test")
        dbc_path = tmp_path / "test.dbc"
        dbc_path.write_text('VERSION ""')

        mock_can = MagicMock()
        mock_msg = Mock()
        mock_msg.timestamp = 1.0
        mock_msg.arbitration_id = 0x123
        mock_msg.dlc = 8
        mock_msg.data = bytes([1, 2, 3, 4, 5, 6, 7, 8])
        mock_msg.is_extended_id = False
        mock_msg.channel = 1

        mock_reader = Mock()
        mock_reader.__iter__ = Mock(return_value=iter([mock_msg]))
        mock_can.BLFReader.return_value = mock_reader

        mock_db = MagicMock()
        mock_db.decode_message.return_value = {"Signal1": 100, "Signal2": 200}

        mock_cantools = MagicMock()
        mock_cantools.database.load_file.return_value = mock_db

        with patch.dict(sys.modules, {"can": mock_can, "cantools": mock_cantools}):
            parser = CANParser(file_path=blf_path, dbc_path=dbc_path)
            result = parser.parse()

            assert result.is_success
            assert "Signal1" in result.data.columns
            assert result.data.iloc[0]["Signal1"] == 100

    def test_parse_with_dbc_decode_failure(self, tmp_path):
        """Test parsing when DBC decode fails for a message."""
        blf_path = tmp_path / "test.blf"
        blf_path.write_bytes(b"test")
        dbc_path = tmp_path / "test.dbc"
        dbc_path.write_text('VERSION ""')

        mock_can = MagicMock()
        mock_msgs = []
        for i in range(2):
            msg = Mock()
            msg.timestamp = 1.0 + i
            msg.arbitration_id = 0x123 + i
            msg.dlc = 8
            msg.data = bytes([i] * 8)
            msg.is_extended_id = False
            msg.channel = 1
            mock_msgs.append(msg)

        mock_reader = Mock()
        mock_reader.__iter__ = Mock(return_value=iter(mock_msgs))
        mock_can.BLFReader.return_value = mock_reader

        mock_db = MagicMock()
        # First call succeeds, second fails
        mock_db.decode_message.side_effect = [
            {"Signal1": 100},
            Exception("Unknown message"),
        ]

        mock_cantools = MagicMock()
        mock_cantools.database.load_file.return_value = mock_db

        with patch.dict(sys.modules, {"can": mock_can, "cantools": mock_cantools}):
            parser = CANParser(file_path=blf_path, dbc_path=dbc_path)
            result = parser.parse()

            assert result.is_success
            assert len(result.data) == 2


class TestCANParserASCManual:
    """Tests for manual ASC parsing fallback."""

    def test_parse_asc_manual_fallback(self, tmp_path):
        """Test ASC parsing with manual fallback when no reader available."""
        asc_path = tmp_path / "test.asc"
        # Write ASC format data that manual parser can handle
        asc_path.write_text(
            "// Comment line\n"
            "1.000000 1  123  Rx   d 8 01 02 03 04 05 06 07 08\n"
            "2.000000 1  1A0  Rx   d 4 AA BB CC DD\n"
        )

        # Directly test the manual parsing method
        parser = CANParser(file_path=asc_path)
        df = parser._parse_asc_manual(asc_path)

        assert df is not None
        assert len(df) == 2
        assert df.iloc[0]["can_id"] == 0x123
        assert df.iloc[1]["can_id"] == 0x1A0

    def test_parse_asc_manual_with_valid_data(self, tmp_path):
        """Test manual ASC parsing with valid data lines."""
        asc_path = tmp_path / "test.asc"
        asc_path.write_text(
            "1.500000 1  1AB  Rx   d 8 11 22 33 44 55 66 77 88\n"
            "2.500000 2  2CD  Rx   d 4 DE AD BE EF\n"
        )

        parser = CANParser(file_path=asc_path)
        df = parser._parse_asc_manual(asc_path)

        assert df is not None
        assert len(df) == 2

    def test_parse_asc_manual_empty_after_parsing(self, tmp_path):
        """Test manual ASC parsing returns None for empty data."""
        asc_path = tmp_path / "test.asc"
        # Only comments and empty lines
        asc_path.write_text(
            "// Just a comment\n"
            "\n"
            "// Another comment\n"
        )

        parser = CANParser(file_path=asc_path)
        df = parser._parse_asc_manual(asc_path)

        assert df is None

    def test_parse_asc_manual_malformed_line(self, tmp_path):
        """Test manual ASC parsing with malformed lines."""
        asc_path = tmp_path / "test.asc"
        asc_path.write_text(
            "1.000000 1  123  Rx   d 8 01 02 03 04 05 06 07 08\n"
            "malformed line that should be skipped\n"
            "2.000000 1  1BC  Rx   d 4 AA BB CC DD\n"
        )

        parser = CANParser(file_path=asc_path)
        df = parser._parse_asc_manual(asc_path)

        # Should skip malformed line and parse valid ones
        assert df is not None
        assert len(df) == 2

    def test_parse_asc_manual_exception_handling(self, tmp_path):
        """Test manual ASC parsing exception handling."""
        asc_path = tmp_path / "test.asc"
        asc_path.write_text(
            "1.000000 1  123  Rx   d 8 01 02 03 04 05 06 07 08\n"
        )

        mock_can = MagicMock()
        del mock_can.ASCReader
        mock_can.io = MagicMock()
        mock_can.io.asc = MagicMock()
        mock_can.io.asc.ASCReader.side_effect = ImportError("No ASCReader")

        with patch.dict(sys.modules, {"can": mock_can}):
            parser = CANParser(file_path=asc_path)
            # Mock _detect_encoding to raise an exception
            with patch.object(parser, "_detect_encoding", side_effect=Exception("Encoding error")):
                result = parser.parse()

                assert not result.is_success
                assert "Error parsing CAN file" in result.error_message


class TestCANParserASCReaderFallback:
    """Tests for ASC reader fallback paths."""

    def test_parse_asc_asc_reader_import_error(self, tmp_path):
        """Test ASC parsing when can.io.asc.ASCReader import fails."""
        asc_path = tmp_path / "test.asc"
        # Write data that manual parser can handle
        asc_path.write_text("1.000000 1  123  Rx   d 8 01 02 03 04 05 06 07 08\n")

        mock_can = MagicMock()
        # No direct ASCReader
        if hasattr(mock_can, "ASCReader"):
            del mock_can.ASCReader

        # Make io.asc.ASCReader raise ImportError when accessed
        mock_can.io = MagicMock()
        mock_can.io.asc = MagicMock()
        # Make the import fail by having ASCReader raise ImportError
        mock_can.io.asc.ASCReader = Mock(side_effect=ImportError("No ASCReader"))

        with patch.dict(sys.modules, {"can": mock_can}):
            parser = CANParser(file_path=asc_path)
            result = parser.parse()

            # Should fall back to manual parsing
            assert result.is_success


class TestCANParserGetDataTimeRange:
    """Tests for get_data with time_range tuple parameter."""

    def test_get_data_with_time_range_tuple(self, tmp_path):
        """Test get_data with time_range tuple parameter."""
        blf_path = tmp_path / "test.blf"
        blf_path.write_bytes(b"test")

        mock_can = MagicMock()
        mock_msgs = []
        for i in range(5):
            msg = Mock()
            msg.timestamp = 1.0 + i * 0.5
            msg.arbitration_id = 0x100 + i
            msg.dlc = 8
            msg.data = bytes([i] * 8)
            msg.is_extended_id = False
            msg.channel = 1
            mock_msgs.append(msg)

        mock_reader = Mock()
        mock_reader.__iter__ = Mock(return_value=iter(mock_msgs))
        mock_can.BLFReader.return_value = mock_reader

        with patch.dict(sys.modules, {"can": mock_can}):
            parser = CANParser(file_path=blf_path)
            parser.parse()
            # Use time_range tuple parameter
            data = parser.get_data(time_range=(1.0, 2.0))

            assert data is not None
            assert len(data) == 3  # timestamps 1.0, 1.5, 2.0

    def test_get_data_with_time_range_tuple_partial(self, tmp_path):
        """Test get_data with time_range tuple filtering."""
        blf_path = tmp_path / "test.blf"
        blf_path.write_bytes(b"test")

        mock_can = MagicMock()
        mock_msgs = []
        for i in range(10):
            msg = Mock()
            msg.timestamp = float(i)
            msg.arbitration_id = 0x100 + i
            msg.dlc = 8
            msg.data = bytes([i] * 8)
            msg.is_extended_id = False
            msg.channel = 1
            mock_msgs.append(msg)

        mock_reader = Mock()
        mock_reader.__iter__ = Mock(return_value=iter(mock_msgs))
        mock_can.BLFReader.return_value = mock_reader

        with patch.dict(sys.modules, {"can": mock_can}):
            parser = CANParser(file_path=blf_path)
            parser.parse()
            data = parser.get_data(time_range=(3.0, 7.0))

            assert data is not None
            assert len(data) == 5  # timestamps 3, 4, 5, 6, 7

    def test_get_data_with_signals_and_time_range(self, tmp_path):
        """Test get_data with signals and time_range tuple."""
        blf_path = tmp_path / "test.blf"
        blf_path.write_bytes(b"test")

        mock_can = MagicMock()
        mock_msgs = []
        for i in range(5):
            msg = Mock()
            msg.timestamp = float(i)
            msg.arbitration_id = 0x100 + i
            msg.dlc = 8
            msg.data = bytes([i] * 8)
            msg.is_extended_id = False
            msg.channel = 1
            mock_msgs.append(msg)

        mock_reader = Mock()
        mock_reader.__iter__ = Mock(return_value=iter(mock_msgs))
        mock_can.BLFReader.return_value = mock_reader

        with patch.dict(sys.modules, {"can": mock_can}):
            parser = CANParser(file_path=blf_path)
            parser.parse()
            data = parser.get_data(signals=["can_id"], time_range=(1.0, 3.0))

            assert data is not None
            assert "can_id" in data.columns
            assert "timestamp" in data.columns


class TestCANParserGetDataNoData:
    """Tests for get_data when no data is parsed."""

    def test_get_data_without_parse(self):
        """Test get_data before parsing."""
        parser = CANParser()
        data = parser.get_data()

        assert data is None

    def test_get_data_with_signals_without_parse(self):
        """Test get_data with signals before parsing."""
        parser = CANParser()
        data = parser.get_data(signals=["signal1"])

        assert data is None

    def test_get_data_with_time_range_without_parse(self):
        """Test get_data with time_range before parsing."""
        parser = CANParser()
        data = parser.get_data(time_range=(0.0, 10.0))

        assert data is None


class TestCANParserEdgeCases:
    """Tests for edge cases."""

    def test_parse_single_message(self, tmp_path):
        """Test parsing single message."""
        blf_path = tmp_path / "test.blf"
        blf_path.write_bytes(b"test")

        mock_can = MagicMock()
        mock_msg = Mock()
        mock_msg.timestamp = 1.0
        mock_msg.arbitration_id = 0x123
        mock_msg.dlc = 8
        mock_msg.data = bytes([1, 2, 3, 4, 5, 6, 7, 8])
        mock_msg.is_extended_id = False
        mock_msg.channel = 1

        mock_reader = Mock()
        mock_reader.__iter__ = Mock(return_value=iter([mock_msg]))
        mock_can.BLFReader.return_value = mock_reader

        with patch.dict(sys.modules, {"can": mock_can}):
            parser = CANParser(file_path=blf_path)
            result = parser.parse()

            assert result.is_success
            assert len(result.data) == 1

    def test_parse_large_dlc(self, tmp_path):
        """Test parsing with large DLC."""
        blf_path = tmp_path / "test.blf"
        blf_path.write_bytes(b"test")

        mock_can = MagicMock()
        mock_msg = Mock()
        mock_msg.timestamp = 1.0
        mock_msg.arbitration_id = 0x123
        mock_msg.dlc = 64  # CAN FD
        mock_msg.data = bytes(range(64))
        mock_msg.is_extended_id = False
        mock_msg.channel = 1

        mock_reader = Mock()
        mock_reader.__iter__ = Mock(return_value=iter([mock_msg]))
        mock_can.BLFReader.return_value = mock_reader

        with patch.dict(sys.modules, {"can": mock_can}):
            parser = CANParser(file_path=blf_path)
            result = parser.parse()

            assert result.is_success

    def test_parse_zero_can_id(self, tmp_path):
        """Test parsing with zero CAN ID."""
        blf_path = tmp_path / "test.blf"
        blf_path.write_bytes(b"test")

        mock_can = MagicMock()
        mock_msg = Mock()
        mock_msg.timestamp = 1.0
        mock_msg.arbitration_id = 0x000
        mock_msg.dlc = 8
        mock_msg.data = bytes([1, 2, 3, 4, 5, 6, 7, 8])
        mock_msg.is_extended_id = False
        mock_msg.channel = 1

        mock_reader = Mock()
        mock_reader.__iter__ = Mock(return_value=iter([mock_msg]))
        mock_can.BLFReader.return_value = mock_reader

        with patch.dict(sys.modules, {"can": mock_can}):
            parser = CANParser(file_path=blf_path)
            result = parser.parse()

            assert result.is_success
            assert result.data.iloc[0]["can_id"] == 0

    def test_parse_max_can_id(self, tmp_path):
        """Test parsing with max CAN ID."""
        blf_path = tmp_path / "test.blf"
        blf_path.write_bytes(b"test")

        mock_can = MagicMock()
        mock_msg = Mock()
        mock_msg.timestamp = 1.0
        mock_msg.arbitration_id = 0x1FFFFFFF  # Max extended ID
        mock_msg.dlc = 8
        mock_msg.data = bytes([1, 2, 3, 4, 5, 6, 7, 8])
        mock_msg.is_extended_id = True
        mock_msg.channel = 1

        mock_reader = Mock()
        mock_reader.__iter__ = Mock(return_value=iter([mock_msg]))
        mock_can.BLFReader.return_value = mock_reader

        with patch.dict(sys.modules, {"can": mock_can}):
            parser = CANParser(file_path=blf_path)
            result = parser.parse()

            assert result.is_success

    def test_get_data_nonexistent_signal(self, tmp_path):
        """Test get_data with nonexistent signal."""
        blf_path = tmp_path / "test.blf"
        blf_path.write_bytes(b"test")

        mock_can = MagicMock()
        mock_msg = Mock()
        mock_msg.timestamp = 1.0
        mock_msg.arbitration_id = 0x123
        mock_msg.dlc = 8
        mock_msg.data = bytes([1, 2, 3, 4, 5, 6, 7, 8])
        mock_msg.is_extended_id = False
        mock_msg.channel = 1

        mock_reader = Mock()
        mock_reader.__iter__ = Mock(return_value=iter([mock_msg]))
        mock_can.BLFReader.return_value = mock_reader

        with patch.dict(sys.modules, {"can": mock_can}):
            parser = CANParser(file_path=blf_path)
            parser.parse()
            data = parser.get_data(signals=["nonexistent_signal"])

            # Should return empty dataframe or handle gracefully
            assert data is not None

    def test_get_data_invalid_time_range(self, tmp_path):
        """Test get_data with invalid time range."""
        blf_path = tmp_path / "test.blf"
        blf_path.write_bytes(b"test")

        mock_can = MagicMock()
        mock_msg = Mock()
        mock_msg.timestamp = 1.0
        mock_msg.arbitration_id = 0x123
        mock_msg.dlc = 8
        mock_msg.data = bytes([1, 2, 3, 4, 5, 6, 7, 8])
        mock_msg.is_extended_id = False
        mock_msg.channel = 1

        mock_reader = Mock()
        mock_reader.__iter__ = Mock(return_value=iter([mock_msg]))
        mock_can.BLFReader.return_value = mock_reader

        with patch.dict(sys.modules, {"can": mock_can}):
            parser = CANParser(file_path=blf_path)
            parser.parse()
            # Request time range outside data
            data = parser.get_data(start_time=100.0, end_time=200.0)

            # Should return empty dataframe
            assert data is not None
            assert len(data) == 0
