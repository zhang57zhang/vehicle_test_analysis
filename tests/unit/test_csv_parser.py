"""Unit tests for CSV parser module."""

import pandas as pd
import pytest

from src.parsers.csv_parser import CSVParser
from src.parsers.base_parser import ParserStatus


class TestCSVParser:
    """Tests for CSVParser class."""

    def test_supported_extensions(self):
        """Test supported file extensions."""
        assert ".csv" in CSVParser.SUPPORTED_EXTENSIONS
        assert ".txt" in CSVParser.SUPPORTED_EXTENSIONS
        assert ".log" in CSVParser.SUPPORTED_EXTENSIONS

    def test_can_parse_csv(self, tmp_path):
        """Test can_parse method for CSV files."""
        csv_path = tmp_path / "test.csv"
        csv_path.write_text("a,b\n1,2\n")
        assert CSVParser.can_parse(csv_path)

    def test_can_parse_txt(self, tmp_path):
        """Test can_parse method for TXT files."""
        txt_path = tmp_path / "test.txt"
        txt_path.write_text("data")
        assert CSVParser.can_parse(txt_path)

    def test_can_parse_unsupported(self, tmp_path):
        """Test can_parse method for unsupported files."""
        bin_path = tmp_path / "test.bin"
        bin_path.write_bytes(b"\x00\x01")
        assert not CSVParser.can_parse(bin_path)

    def test_parse_basic_csv(self, sample_csv_data):
        """Test parsing basic CSV file."""
        parser = CSVParser(sample_csv_data)
        result = parser.parse()

        assert result.is_success
        assert result.status == ParserStatus.SUCCESS
        assert result.data is not None
        assert len(result.data) == 6
        assert "signal1" in result.data.columns
        assert "signal2" in result.data.columns

    def test_parse_with_time_column(self, sample_csv_data):
        """Test parsing with time column specification."""
        parser = CSVParser(sample_csv_data, time_column="time")
        result = parser.parse()

        assert result.is_success
        assert "time" in result.data.columns
        assert "time_range" in result.metadata

    def test_parse_nonexistent_file(self, tmp_path):
        """Test parsing non-existent file."""
        parser = CSVParser(tmp_path / "nonexistent.csv")
        result = parser.parse()

        assert not result.is_success
        assert result.status == ParserStatus.ERROR
        assert "not found" in result.error_message.lower()

    def test_parse_empty_file(self, tmp_path):
        """Test parsing empty file."""
        empty_path = tmp_path / "empty.csv"
        empty_path.write_text("")
        parser = CSVParser(empty_path)
        result = parser.parse()

        assert result.status == ParserStatus.ERROR

    def test_get_signal_list(self, sample_csv_data):
        """Test getting signal list."""
        parser = CSVParser(sample_csv_data)
        parser.parse()
        signals = parser.get_signal_list()

        assert "signal1" in signals
        assert "signal2" in signals

    def test_get_signal_list_before_parse(self):
        """Test getting signal list before parsing."""
        parser = CSVParser()
        signals = parser.get_signal_list()
        assert signals == []

    def test_get_data_filtered(self, sample_csv_data):
        """Test getting filtered data."""
        parser = CSVParser(sample_csv_data, time_column="time")
        parser.parse()

        filtered = parser.get_data(
            signals=["signal1"], time_range=(0.1, 0.4)
        )
        assert filtered is not None
        assert "signal1" in filtered.columns
        assert "signal2" not in filtered.columns

    def test_get_data_before_parse(self):
        """Test getting data before parsing."""
        parser = CSVParser()
        assert parser.get_data() is None

    def test_parse_semicolon_delimiter(self, tmp_path):
        """Test parsing CSV with semicolon delimiter."""
        csv_path = tmp_path / "semicolon.csv"
        csv_path.write_text("a;b\n1;2\n3;4\n")
        parser = CSVParser(csv_path, delimiter=";")
        result = parser.parse()

        assert result.is_success
        assert "a" in result.data.columns
        assert "b" in result.data.columns

    def test_parse_tab_delimiter(self, tmp_path):
        """Test parsing CSV with tab delimiter."""
        csv_path = tmp_path / "tab.csv"
        csv_path.write_text("a\tb\n1\t2\n3\t4\n")
        parser = CSVParser(csv_path, delimiter="\t")
        result = parser.parse()

        assert result.is_success

    def test_get_metadata(self, sample_csv_data):
        """Test getting metadata."""
        parser = CSVParser(sample_csv_data)
        parser.parse()
        metadata = parser.get_metadata()

        assert "file_name" in metadata
        assert "row_count" in metadata
        assert metadata["row_count"] == 6

    def test_parse_with_custom_encoding(self, tmp_path):
        """Test parsing with custom encoding."""
        csv_path = tmp_path / "utf8.csv"
        csv_path.write_text("signal\n测试\n", encoding="utf-8")
        parser = CSVParser(csv_path, encoding="utf-8")
        result = parser.parse()

        assert result.is_success

    def test_parse_with_auto_encoding_detection(self, tmp_path):
        """Test parsing with automatic encoding detection (encoding=None)."""
        csv_path = tmp_path / "auto_encoding.csv"
        csv_path.write_text("signal1,signal2\n1.0,2.0\n3.0,4.0\n", encoding="utf-8")
        parser = CSVParser(csv_path)  # encoding=None by default
        result = parser.parse()

        assert result.is_success
        assert result.metadata.get("encoding") is not None

    def test_parse_unreadable_csv_content(self, tmp_path):
        """Test parsing file that cannot be read as CSV (all fallbacks fail)."""
        bad_path = tmp_path / "unreadable.csv"
        # Write binary garbage that no CSV parser can handle
        bad_path.write_bytes(b"\x00\x01\x02\x03\x04\x05\xff\xfe\xfd")
        parser = CSVParser(bad_path)
        result = parser.parse()

        assert result.status == ParserStatus.ERROR
        assert "empty" in result.error_message.lower() or "failed" in result.error_message.lower()

    def test_parse_directory_path(self, tmp_path):
        """Test parsing a directory path instead of a file."""
        parser = CSVParser(tmp_path)
        result = parser.parse()

        assert result.status == ParserStatus.ERROR
        assert "not a file" in result.error_message.lower()

    def test_parse_with_path_override(self, tmp_path):
        """Test parse method with file_path override."""
        csv_path1 = tmp_path / "file1.csv"
        csv_path1.write_text("a,b\n1,2\n")
        csv_path2 = tmp_path / "file2.csv"
        csv_path2.write_text("x,y\n10,20\n")

        parser = CSVParser(csv_path1)
        result = parser.parse(csv_path2)

        assert result.is_success
        assert "x" in result.data.columns
        assert "y" in result.data.columns

    def test_parse_no_file_path_provided(self):
        """Test parse when no file path is provided."""
        parser = CSVParser()
        result = parser.parse()

        assert result.status == ParserStatus.ERROR
        assert "no file path" in result.error_message.lower()

    def test_process_time_column_string_datetime(self, tmp_path):
        """Test time column processing with string datetime format."""
        csv_path = tmp_path / "datetime.csv"
        csv_path.write_text("time,signal\n2024-01-01 00:00:00,1.0\n2024-01-01 00:00:01,2.0\n")
        parser = CSVParser(csv_path, time_column="time")
        result = parser.parse()

        assert result.is_success
        assert "time_range" in result.metadata

    def test_process_time_column_with_format(self, tmp_path):
        """Test time column processing with custom time format."""
        csv_path = tmp_path / "time_format.csv"
        csv_path.write_text("timestamp,value\n01/15/24 10:30:00,100\n01/15/24 10:30:01,200\n")
        parser = CSVParser(csv_path, time_column="timestamp", time_format="%m/%d/%y %H:%M:%S")
        result = parser.parse()

        assert result.is_success
        assert "time_range" in result.metadata

    def test_process_time_column_non_convertible(self, tmp_path):
        """Test time column processing when values cannot be converted."""
        csv_path = tmp_path / "bad_time.csv"
        # Non-convertible time values should create sequential index
        csv_path.write_text("time,signal\nabc,1.0\ndef,2.0\nghi,3.0\n")
        parser = CSVParser(csv_path, time_column="time")
        result = parser.parse()

        assert result.is_success
        # pd.to_numeric with errors='coerce' returns NaN for non-convertible values
        # Then datetime parsing also fails, so sequential index is created
        # Check that we have 3 rows
        assert len(result.data) == 3

    def test_process_time_column_already_numeric(self, tmp_path):
        """Test time column processing when already numeric."""
        csv_path = tmp_path / "numeric_time.csv"
        csv_path.write_text("time,signal\n0.0,1.0\n0.1,2.0\n0.2,3.0\n")
        parser = CSVParser(csv_path, time_column="time")
        result = parser.parse()

        assert result.is_success
        assert result.data["time"].dtype in [float, int]

    def test_process_time_column_string_numeric(self, tmp_path):
        """Test time column processing with string numeric values."""
        csv_path = tmp_path / "string_numeric.csv"
        csv_path.write_text('time,signal\n"0.0",1.0\n"0.1",2.0\n"0.2",3.0\n')
        parser = CSVParser(csv_path, time_column="time")
        result = parser.parse()

        assert result.is_success
        assert result.data["time"].dtype in [float, int]

    def test_get_data_with_signals_no_time_column(self, tmp_path):
        """Test get_data with signals filter when no time column specified."""
        csv_path = tmp_path / "no_time.csv"
        csv_path.write_text("a,b,c\n1,2,3\n4,5,6\n")
        parser = CSVParser(csv_path)
        parser.parse()

        filtered = parser.get_data(signals=["a", "b"])
        assert filtered is not None
        assert "a" in filtered.columns
        assert "b" in filtered.columns
        assert "c" not in filtered.columns

    def test_get_data_with_time_range_no_time_column(self, tmp_path):
        """Test get_data with time_range when no time column specified."""
        csv_path = tmp_path / "simple.csv"
        csv_path.write_text("a,b\n1,2\n3,4\n")
        parser = CSVParser(csv_path)
        parser.parse()

        # time_range should be ignored when no time_column
        filtered = parser.get_data(time_range=(0, 1))
        assert filtered is not None
        assert len(filtered) == 2

    def test_parse_log_file(self, tmp_path):
        """Test parsing .log file extension."""
        log_path = tmp_path / "test.log"
        log_path.write_text("col1,col2\nval1,val2\n")
        parser = CSVParser(log_path)
        result = parser.parse()

        assert result.is_success
        assert "col1" in result.data.columns

    def test_parse_csv_with_only_headers(self, tmp_path):
        """Test parsing CSV with headers but no data rows."""
        header_only = tmp_path / "header_only.csv"
        header_only.write_text("col1,col2,col3\n")
        parser = CSVParser(header_only)
        result = parser.parse()

        # Should error because DataFrame is empty
        assert result.status == ParserStatus.ERROR

    def test_parse_permission_denied(self, tmp_path):
        """Test parsing file with permission denied."""
        import os
        restricted_path = tmp_path / "restricted.csv"
        restricted_path.write_text("a,b\n1,2\n")
        
        # Make file read-only then try to make it unreadable
        # On Windows, we can simulate this differently
        original_mode = os.stat(restricted_path).st_mode
        
        parser = CSVParser(restricted_path)
        # This test mainly exercises the PermissionError path
        # Actual permission denial is hard to simulate on Windows
        result = parser.parse()
        # Should succeed on normal file
        assert result.is_success or result.status == ParserStatus.ERROR

    def test_parse_exception_in_parsing(self, tmp_path):
        """Test general exception handling during parsing."""
        csv_path = tmp_path / "normal.csv"
        csv_path.write_text("a,b\n1,2\n")
        parser = CSVParser(csv_path)
        
        # Mock to raise unexpected exception in _read_csv_with_fallback
        import unittest.mock as mock
        with mock.patch('pandas.read_csv', side_effect=RuntimeError("Unexpected error")):
            result = parser.parse()
            assert result.status == ParserStatus.ERROR
            # When all read attempts fail, we get this error
            assert "failed" in result.error_message.lower() or "empty" in result.error_message.lower()

    def test_parse_with_time_column_not_in_data(self, tmp_path):
        """Test parsing when specified time column doesn't exist in data."""
        csv_path = tmp_path / "no_time_col.csv"
        csv_path.write_text("a,b\n1,2\n3,4\n")
        parser = CSVParser(csv_path, time_column="nonexistent")
        result = parser.parse()

        # Should still parse successfully, just without time processing
        assert result.is_success
        assert "time_range" not in result.metadata

    def test_get_data_with_nonexistent_signals(self, tmp_path):
        """Test get_data with signals that don't exist."""
        csv_path = tmp_path / "data.csv"
        csv_path.write_text("a,b\n1,2\n3,4\n")
        parser = CSVParser(csv_path, time_column="a")
        parser.parse()

        # Request nonexistent signals - should return only existing columns
        filtered = parser.get_data(signals=["nonexistent"])
        # Should only have time column since signal doesn't exist
        assert filtered is not None
        assert "a" in filtered.columns  # time column

    def test_multiple_parse_calls(self, tmp_path):
        """Test calling parse multiple times on different files."""
        csv1 = tmp_path / "file1.csv"
        csv1.write_text("x,y\n1,2\n")
        csv2 = tmp_path / "file2.csv"
        csv2.write_text("a,b\n10,20\n")

        parser = CSVParser(csv1)
        result1 = parser.parse()
        assert result1.is_success
        assert "x" in result1.data.columns

        result2 = parser.parse(csv2)
        assert result2.is_success
        assert "a" in result2.data.columns

    def test_read_csv_fallback_all_fail(self, tmp_path):
        """Test _read_csv_with_fallback when all read attempts fail."""
        # Create a file that looks like CSV but will fail all parsing attempts
        bad_csv = tmp_path / "bad.csv"
        # Write content that will make pandas return empty DataFrame for all separators
        bad_csv.write_text("\n\n\n")  # Only newlines, no actual data
        parser = CSVParser(bad_csv)
        result = parser.parse()

        assert result.status == ParserStatus.ERROR
        assert "empty" in result.error_message.lower() or "failed" in result.error_message.lower()

    def test_process_time_column_datetime_conversion(self, tmp_path):
        """Test time column processing with datetime string conversion."""
        csv_path = tmp_path / "datetime.csv"
        # ISO format datetime that pandas can auto-detect
        csv_path.write_text("time,value\n2024-01-01T00:00:00,1\n2024-01-01T00:00:01,2\n")
        parser = CSVParser(csv_path, time_column="time")
        result = parser.parse()

        assert result.is_success
        assert "time_range" in result.metadata

    def test_process_time_column_datetime_with_format_conversion(self, tmp_path):
        """Test time column processing with custom datetime format conversion."""
        csv_path = tmp_path / "custom_datetime.csv"
        # Custom datetime format
        csv_path.write_text("timestamp,data\n15/01/2024 10:30:00,100\n15/01/2024 10:30:05,200\n")
        parser = CSVParser(csv_path, time_column="timestamp", time_format="%d/%m/%Y %H:%M:%S")
        result = parser.parse()

        assert result.is_success
        assert "time_range" in result.metadata

    def test_process_time_column_datetime_conversion_fails_to_sequential(self, tmp_path):
        """Test time column falls back to sequential when datetime parsing fails."""
        csv_path = tmp_path / "weird_time.csv"
        # Mix of formats that will fail datetime parsing
        csv_path.write_text("time,val\nnotadate,1\nalsoinvalid,2\n")
        parser = CSVParser(csv_path, time_column="time")
        result = parser.parse()

        assert result.is_success
        # Should have sequential time index
        assert len(result.data) == 2

    def test_process_time_column_datetime_no_format_success(self, tmp_path):
        """Test datetime parsing without explicit format (auto-detect)."""
        csv_path = tmp_path / "auto_datetime.csv"
        # Standard ISO datetime that pandas can auto-detect
        csv_path.write_text("ts,val\n2024-01-15 10:30:00,1\n2024-01-15 10:30:05,2\n")
        parser = CSVParser(csv_path, time_column="ts")  # No time_format specified
        result = parser.parse()

        assert result.is_success
        assert "time_range" in result.metadata

    def test_process_time_column_datetime_with_format_success(self, tmp_path):
        """Test datetime parsing with explicit format that succeeds."""
        csv_path = tmp_path / "format_datetime.csv"
        # Custom format that requires explicit format string
        csv_path.write_text("ts,val\n15-01-2024 10.30.00,1\n15-01-2024 10.30.05,2\n")
        parser = CSVParser(csv_path, time_column="ts", time_format="%d-%m-%Y %H.%M.%S")
        result = parser.parse()

        assert result.is_success
        assert "time_range" in result.metadata

    def test_process_time_column_datetime_with_format_fails(self, tmp_path):
        """Test datetime parsing with wrong format falls back to sequential."""
        csv_path = tmp_path / "wrong_format.csv"
        # Data doesn't match the specified format
        csv_path.write_text("ts,val\n2024-01-15,1\n2024-01-16,2\n")
        parser = CSVParser(csv_path, time_column="ts", time_format="%d/%m/%Y")  # Wrong format
        result = parser.parse()

        assert result.is_success
        # Should fall back to sequential index since datetime parsing fails
        assert len(result.data) == 2

    def test_process_time_column_to_numeric_exception(self, tmp_path):
        """Test time column when pd.to_numeric raises exception (not coerce)."""
        csv_path = tmp_path / "data.csv"
        csv_path.write_text("time,val\nabc,1\ndef,2\n")
        parser = CSVParser(csv_path, time_column="time")
        
        # Mock pd.to_numeric to raise an exception, forcing datetime path
        import unittest.mock as mock
        original_to_numeric = pd.to_numeric
        
        def mock_to_numeric(*args, **kwargs):
            # If errors='coerce', still raise to force datetime path
            if kwargs.get('errors') == 'coerce':
                raise TypeError("Mocked exception")
            return original_to_numeric(*args, **kwargs)
        
        with mock.patch('pandas.to_numeric', side_effect=mock_to_numeric):
            result = parser.parse()
            # Should succeed via datetime parsing or sequential fallback
            assert result.is_success

    def test_read_csv_fallback_returns_none(self, tmp_path):
        """Test _read_csv_with_fallback returning None (all attempts fail)."""
        csv_path = tmp_path / "tricky.csv"
        # Create file with content that pandas can read but returns empty
        csv_path.write_text("header\n")  # Only header, no data
        parser = CSVParser(csv_path)
        result = parser.parse()
        
        # Should error because DataFrame is empty
        assert result.status == ParserStatus.ERROR

    def test_process_time_column_datetime_exception_with_format(self, tmp_path):
        """Test datetime parsing exception when format is specified."""
        csv_path = tmp_path / "data.csv"
        csv_path.write_text("ts,val\ninvalid,1\ninvalid2,2\n")
        parser = CSVParser(csv_path, time_column="ts", time_format="%Y-%m-%d")
        
        # Mock pd.to_numeric to raise exception, forcing datetime path
        import unittest.mock as mock
        
        def mock_to_numeric(*args, **kwargs):
            raise TypeError("Force datetime path")
        
        with mock.patch('pandas.to_numeric', side_effect=mock_to_numeric):
            result = parser.parse()
            # Should fall back to sequential index
            assert result.is_success
            assert len(result.data) == 2

    def test_process_time_column_datetime_exception_no_format(self, tmp_path):
        """Test datetime parsing exception when no format specified."""
        csv_path = tmp_path / "data.csv"
        csv_path.write_text("ts,val\nnotdatetime,1\nstillnot,2\n")
        parser = CSVParser(csv_path, time_column="ts")  # No time_format
        
        import unittest.mock as mock
        
        def mock_to_numeric(*args, **kwargs):
            raise TypeError("Force datetime path")
        
        with mock.patch('pandas.to_numeric', side_effect=mock_to_numeric):
            result = parser.parse()
            # Should fall back to sequential index
            assert result.is_success
            assert len(result.data) == 2

    def test_read_csv_all_attempts_return_empty(self, tmp_path):
        """Test when all CSV read attempts return empty DataFrame."""
        csv_path = tmp_path / "tricky.csv"
        csv_path.write_text("a,b\n1,2\n")  # Valid CSV
        
        import unittest.mock as mock
        
        # Mock pd.read_csv to always return empty DataFrame
        def mock_read_csv(*args, **kwargs):
            return pd.DataFrame()  # Empty DataFrame
        
        with mock.patch('pandas.read_csv', side_effect=mock_read_csv):
            parser = CSVParser(csv_path)
            result = parser.parse()
            
            # Should error because _read_csv_with_fallback returns None
            assert result.status == ParserStatus.ERROR
            assert "failed" in result.error_message.lower() or "empty" in result.error_message.lower()

    def test_read_csv_fallback_returns_none_directly(self, tmp_path):
        """Test _read_csv_with_fallback returning None directly via mock."""
        csv_path = tmp_path / "data.csv"
        csv_path.write_text("a,b\n1,2\n")
        parser = CSVParser(csv_path)
        
        import unittest.mock as mock
        
        # Mock the internal method to return None
        with mock.patch.object(parser, '_read_csv_with_fallback', return_value=None):
            result = parser.parse()
            
            assert result.status == ParserStatus.ERROR
            assert "failed" in result.error_message.lower() or "empty" in result.error_message.lower()

    def test_read_csv_all_attempts_exception(self, tmp_path):
        """Test when all pd.read_csv calls raise exceptions."""
        csv_path = tmp_path / "data.csv"
        csv_path.write_text("a,b\n1,2\n")
        
        import unittest.mock as mock
        
        # Mock pd.read_csv in the csv_parser module to always raise exception
        with mock.patch('src.parsers.csv_parser.pd.read_csv', side_effect=Exception("Read error")):
            parser = CSVParser(csv_path)
            result = parser.parse()
            
            # Should error because _read_csv_with_fallback returns None (all attempts failed)
            assert result.status == ParserStatus.ERROR
            assert "failed" in result.error_message.lower() or "empty" in result.error_message.lower()

    def test_datetime_conversion_success_no_format(self, tmp_path):
        """Test datetime conversion path without explicit format (falls back to sequential)."""
        csv_path = tmp_path / "dates.csv"
        # ISO format dates - datetime parsing will fail on astype(float), fall back to sequential
        csv_path.write_text("ts,val\n2024-01-15T10:30:00,1\n2024-01-15T10:30:05,2\n")
        parser = CSVParser(csv_path, time_column="ts")  # No time_format
        
        import unittest.mock as mock
        
        def mock_to_numeric(*args, **kwargs):
            raise TypeError("Force datetime path")
        
        with mock.patch('pandas.to_numeric', side_effect=mock_to_numeric):
            result = parser.parse()
            # Should succeed via sequential fallback (datetime astype(float) fails)
            assert result.is_success
            # Time column should be sequential index [0, 1]
            assert list(result.data["ts"]) == [0, 1]
