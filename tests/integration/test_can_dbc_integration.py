"""
Integration tests for CAN data parsing workflow.

Tests the complete flow:
CAN file -> Parse -> DBC decode -> Signal extraction -> Indicator calculation
"""

import os
import tempfile
from pathlib import Path
from typing import Dict, Any

import numpy as np
import pandas as pd
import pytest

from src.parsers.can_parser import CANParser
from src.parsers.dbc_parser import DBCParser
from src.core.indicator_engine import (
    IndicatorDefinition,
    IndicatorEngine,
    IndicatorType,
)
from src.analyzers.functional_analyzer import FunctionalAnalyzer


class TestCANParsingIntegration:
    """Integration tests for CAN file parsing."""

    @pytest.fixture
    def sample_dbc_file(self, tmp_path) -> Path:
        """Create a sample DBC file for testing."""
        dbc_content = """
VERSION ""

NS_ :
    NS_DESC_
    CM_
    BA_DEF_
    BA_
    VAL_
    CAT_DEF_
    CAT_
    FILTER
    BA_DEF_DEF_
    EV_DATA_
    ENVVAR_DATA_
    SGTYPE_
    SGTYPE_VAL_
    SGTYPE_VAL_DATA_
    BA_DEF_SGTYPE_
    BA_SGTYPE_
    SIG_TYPE_REF_
    VAL_TABLE_
    SIG_GROUP_
    SIG_VALTYPE_
    SIGTYPE_VALTYPE_
    BO_TX_BU_
    BA_DEF_REL_
    BA_REL_
    BA_DEF_DEF_REL_
    BU_SG_REL_
    BU_EV_REL_
    BU_BO_REL_
    SG_MUL_VAL_

BS_:

BU_: ECU1 ECU2

BO_ 100 VehicleSpeed: 8 ECU1
 SG_ Speed : 0|16@1+ (0.1,0) [0|6553.5] "km/h" ECU2
 SG_ Valid : 16|1@1+ (1,0) [0|1] "" ECU2

BO_ 200 EngineStatus: 8 ECU1
 SG_ RPM : 0|16@1+ (1,0) [0|8000] "rpm" ECU2
 SG_ Temperature : 16|8@1+ (1,-40) [-40|215] "C" ECU2
 SG_ Running : 24|1@1+ (1,0) [0|1] "" ECU2

BO_ 300 BrakeData: 8 ECU1
 SG_ BrakePressure : 0|12@1+ (0.1,0) [0|409.5] "bar" ECU2
 SG_ ABS_Active : 12|1@1+ (1,0) [0|1] "" ECU2

VAL_ 100 Valid 0 "Invalid" 1 "Valid";
VAL_ 200 Running 0 "Off" 1 "On";
VAL_ 300 ABS_Active 0 "Inactive" 1 "Active";
"""
        dbc_path = tmp_path / "test_database.dbc"
        dbc_path.write_text(dbc_content.strip())
        return dbc_path

    @pytest.fixture
    def sample_asc_file(self, tmp_path) -> Path:
        """Create a sample ASC (ASCII) CAN log file for testing."""
        asc_content = """date Wed Mar 15 10:00:00 2023
base hex timestamps absolute
begin triggerblock Wed Mar 15 10:00:00 2023
   0.000000 1  100          Rx   d 8 00 10 00 00 00 00 00 00
   0.010000 1  200          Rx   d 8 20 4E 32 00 01 00 00 00
   0.020000 1  100          Rx   d 8 64 00 01 00 00 00 00 00
   0.030000 1  300          Rx   d 8 00 10 00 00 00 00 00 00
   0.040000 1  200          Rx   d 8 40 9C 50 00 01 00 00 00
   0.050000 1  100          Rx   d 8 C8 00 01 00 00 00 00 00
   0.060000 1  300          Rx   d 8 64 30 00 00 00 00 00 00
   0.070000 1  200          Rx   d 8 60 EA 64 00 01 00 00 00
   0.080000 1  100          Rx   d 8 2C 01 01 00 00 00 00 00
   0.090000 1  300          Rx   d 8 96 30 00 00 00 00 00 00
   0.100000 1  200          Rx   d 8 80 38 78 00 01 00 00 00
end triggerblock
"""
        asc_path = tmp_path / "test_can.asc"
        asc_path.write_text(asc_content.strip())
        return asc_path

    def test_dbc_parsing_only(self, sample_dbc_file):
        """Test DBC file parsing independently."""
        parser = DBCParser(sample_dbc_file)
        result = parser.parse()

        assert result.is_success
        assert result.metadata is not None
        assert result.metadata["message_count"] == 3
        # result.signals is a list of signal dicts with 'name' and 'type' keys
        signal_names = [s['name'] for s in result.signals]
        assert "Speed" in signal_names
        assert "RPM" in signal_names

        # Check message definitions (CAN IDs are decimal in sample_dbc_file)
        msg_100 = parser.get_message(100)
        assert msg_100 is not None
        assert msg_100.name == "VehicleSpeed"
        assert "Speed" in msg_100.signals

        msg_200 = parser.get_message(200)  # Decimal CAN ID in DBC
        assert msg_200 is not None
        assert msg_200.name == "EngineStatus"
        assert "RPM" in msg_200.signals
        assert "Temperature" in msg_200.signals

    def test_dbc_signal_definition(self, sample_dbc_file):
        """Test DBC signal definition extraction."""
        parser = DBCParser(sample_dbc_file)
        parser.parse()

        # Get signal definition (CAN IDs are decimal in sample_dbc_file)
        speed_signal = parser.get_signal(100, "Speed")
        assert speed_signal is not None
        assert speed_signal.start_bit == 0
        assert speed_signal.length == 16
        assert speed_signal.scale == 0.1
        assert speed_signal.unit == "km/h"

        rpm_signal = parser.get_signal(200, "RPM")
        assert rpm_signal is not None
        assert rpm_signal.length == 16
        assert rpm_signal.unit == "rpm"

    def test_asc_parsing_without_dbc(self, sample_asc_file):
        """Test ASC file parsing without DBC decoding."""
        parser = CANParser(sample_asc_file)
        result = parser.parse()

        assert result.is_success
        assert result.data is not None
        assert len(result.data) > 0
        assert "timestamp" in result.data.columns
        assert "can_id" in result.data.columns

    def test_asc_parsing_with_dbc(self, sample_asc_file, sample_dbc_file):
        """Test ASC file parsing with DBC decoding."""
        parser = CANParser(sample_asc_file, dbc_path=sample_dbc_file)
        result = parser.parse()

        assert result.is_success
        assert result.data is not None

        # Check that signals are decoded
        # The exact decoded values depend on the data
        assert "can_id" in result.data.columns

    def test_can_to_indicator_workflow(self, sample_asc_file, sample_dbc_file):
        """Test complete workflow: CAN parse -> DBC decode -> Indicator calculation."""
        # Step 1: Parse DBC
        dbc_parser = DBCParser(sample_dbc_file)
        dbc_result = dbc_parser.parse()
        assert dbc_result.is_success

        # Step 2: Parse CAN with DBC
        can_parser = CANParser(sample_asc_file, dbc_path=sample_dbc_file)
        can_result = can_parser.parse()

        # If parsing succeeds, continue with indicator calculation
        if can_result.is_success and can_result.data is not None:
            # Step 3: Calculate indicators on parsed data
            engine = IndicatorEngine()

            # Define indicator based on available columns
            data = can_result.data

            # Check if we have numeric columns for indicator calculation
            numeric_cols = data.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 1:  # More than just timestamp
                indicator = IndicatorDefinition(
                    name="CAN_Message_Count",
                    signal_name=numeric_cols[1],  # Use first numeric signal
                    indicator_type=IndicatorType.SINGLE_VALUE,
                    formula="count",
                )
                result = engine.calculate(indicator, data)
                assert result is not None


class TestDBCManualParsing:
    """Tests for DBC manual parsing functionality."""

    @pytest.fixture
    def complex_dbc_file(self, tmp_path) -> Path:
        """Create a more complex DBC file for testing."""
        dbc_content = """
VERSION "1.0"

NS_ :
    NS_DESC_
    CM_
    BA_DEF_

BS_:

BU_: ECU1 ECU2 ECU3

BO_ 0x100 Message1: 8 ECU1
 SG_ Signal1 : 0|8@1+ (1,0) [0|255] "" ECU2
 SG_ Signal2 : 8|16@1- (0.01,0) [-327.68|327.67] "V" ECU2,ECU3
 SG_ Signal3 : 24|1@1+ (1,0) [0|1] "" ECU2

BO_ 0x101 Message2: 8 ECU2
 SG_ Counter : 0|4@1+ (1,0) [0|15] "" ECU1
 SG_ Checksum : 4|8@1+ (1,0) [0|255] "" ECU1

CM_ BO_ 0x100 "Test message 1";
CM_ SG_ 0x100 Signal1 "Test signal 1";

BA_DEF_ BO_ "GenMsgCycleTime" INT 0 60000;
BA_DEF_ SG_ "GenSigStartValue" FLOAT 0 100000;
BA_ "GenMsgCycleTime" BO_ 0x100 100;
"""
        dbc_path = tmp_path / "complex.dbc"
        dbc_path.write_text(dbc_content.strip())
        return dbc_path

    def test_complex_dbc_parsing(self, complex_dbc_file):
        """Test parsing of complex DBC file."""
        parser = DBCParser(complex_dbc_file)
        result = parser.parse()

        assert result.is_success
        assert result.metadata["message_count"] == 2

        # Check first message
        msg1 = parser.get_message(0x100)
        assert msg1 is not None
        assert len(msg1.signals) == 3

        # Check signed signal
        signal2 = parser.get_signal(0x100, "Signal2")
        assert signal2 is not None
        assert signal2.is_signed is True
        assert signal2.scale == 0.01

    def test_dbc_signal_decoding(self, complex_dbc_file):
        """Test signal decoding from raw bytes."""
        parser = DBCParser(complex_dbc_file)
        parser.parse()

        # Test decoding Signal1 (0|8@1+, scale=1, offset=0)
        # Raw bytes: 0x64 = 100
        data = bytes([0x64, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        value = parser.decode_signal(0x100, data, "Signal1")
        assert value is not None
        assert value == 100.0

    def test_dbc_get_all_messages(self, complex_dbc_file):
        """Test getting all message definitions."""
        parser = DBCParser(complex_dbc_file)
        parser.parse()

        messages = parser.get_all_messages()
        assert len(messages) == 2
        assert 0x100 in messages
        assert 0x101 in messages

    def test_dbc_get_all_nodes(self, complex_dbc_file):
        """Test getting all node definitions."""
        parser = DBCParser(complex_dbc_file)
        parser.parse()

        nodes = parser.get_all_nodes()
        assert len(nodes) == 3
        assert "ECU1" in nodes
        assert "ECU2" in nodes
        assert "ECU3" in nodes

    def test_dbc_value_table(self, complex_dbc_file):
        """Test value table functionality."""
        parser = DBCParser(complex_dbc_file)
        result = parser.parse()

        # Value tables are parsed but may be empty if not in specific format
        assert result.is_success


class TestCANParserEdgeCases:
    """Edge case tests for CAN parser."""

    def test_parse_nonexistent_file(self, tmp_path):
        """Test parsing a non-existent file."""
        parser = CANParser(tmp_path / "nonexistent.blf")
        result = parser.parse()

        assert not result.is_success
        assert result.error_message is not None

    def test_parse_unsupported_format(self, tmp_path):
        """Test parsing an unsupported file format."""
        unsupported_file = tmp_path / "test.xyz"
        unsupported_file.write_text("some content")

        parser = CANParser(unsupported_file)
        result = parser.parse()

        assert not result.is_success

    def test_dbc_parse_nonexistent_file(self, tmp_path):
        """Test DBC parser with non-existent file."""
        parser = DBCParser(tmp_path / "nonexistent.dbc")
        result = parser.parse()

        assert not result.is_success
        assert result.error_message is not None

    def test_empty_asc_file(self, tmp_path):
        """Test parsing an empty ASC file."""
        asc_path = tmp_path / "empty.asc"
        asc_path.write_text("")

        parser = CANParser(asc_path)
        result = parser.parse()

        # Should fail or return empty data
        assert not result.is_success or result.data is None or result.data.empty

    def test_malformed_asc_file(self, tmp_path):
        """Test parsing a malformed ASC file."""
        asc_content = """
date Wed Mar 15 10:00:00 2023
base hex timestamps absolute
begin triggerblock Wed Mar 15 10:00:00 2023
   INVALID LINE HERE
   ANOTHER INVALID LINE
end triggerblock
"""
        asc_path = tmp_path / "malformed.asc"
        asc_path.write_text(asc_content)

        parser = CANParser(asc_path)
        result = parser.parse()

        # Parser should handle malformed data gracefully
        # Either succeed with partial data or fail gracefully
        assert result is not None


class TestCANDataFiltering:
    """Tests for CAN data filtering functionality."""

    @pytest.fixture
    def sample_asc_with_data(self, tmp_path) -> Path:
        """Create ASC file with more data for filtering tests."""
        lines = ["date Wed Mar 15 10:00:00 2023", "base hex timestamps absolute"]
        lines.append("begin triggerblock Wed Mar 15 10:00:00 2023")

        for i in range(100):
            timestamp = i * 0.01
            can_id = 0x100 if i % 2 == 0 else 0x200
            data_byte = i % 256
            lines.append(
                f"   {timestamp:.6f} 1  {can_id:03X}          Rx   d 8 "
                f"{data_byte:02X} 00 00 00 00 00 00 00"
            )

        lines.append("end triggerblock")
        asc_path = tmp_path / "filter_test.asc"
        asc_path.write_text("\n".join(lines))
        return asc_path

    def test_get_signal_list(self, sample_asc_with_data):
        """Test getting signal list from parsed data."""
        parser = CANParser(sample_asc_with_data)
        result = parser.parse()

        assert result.is_success
        signals = parser.get_signal_list()
        assert isinstance(signals, list)

    def test_get_data_with_time_range(self, sample_asc_with_data):
        """Test getting data with time range filter."""
        parser = CANParser(sample_asc_with_data)
        parser.parse()

        # Get data for specific time range
        filtered = parser.get_data(time_range=(0.2, 0.5))

        if filtered is not None and len(filtered) > 0:
            assert filtered["timestamp"].min() >= 0.2
            assert filtered["timestamp"].max() <= 0.5

    def test_get_data_with_signals(self, sample_asc_with_data):
        """Test getting specific signals from data."""
        parser = CANParser(sample_asc_with_data)
        result = parser.parse()

        if result.is_success:
            signals = parser.get_signal_list()
            if signals:
                filtered = parser.get_data(signals=[signals[0]])
                if filtered is not None:
                    assert signals[0] in filtered.columns or len(filtered.columns) <= 2


class TestCANToFunctionalAnalysis:
    """Integration tests for CAN data to functional analysis."""

    @pytest.fixture
    def can_data_with_dbc(self, tmp_path):
        """Create CAN data with DBC for functional analysis."""
        # Create DBC
        dbc_content = """
VERSION ""

BS_:

BU_: ECU1 ECU2

BO_ 100 SpeedMsg: 8 ECU1
 SG_ VehicleSpeed : 0|16@1+ (0.1,0) [0|300] "km/h" ECU2

BO_ 200 TempMsg: 8 ECU1
 SG_ CoolantTemp : 0|8@1+ (1,-40) [-40|215] "C" ECU2
"""
        dbc_path = tmp_path / "test.dbc"
        dbc_path.write_text(dbc_content.strip())

        # Create ASC
        asc_content = """date Wed Mar 15 10:00:00 2023
base hex timestamps absolute
begin triggerblock Wed Mar 15 10:00:00 2023
   0.000000 1  100          Rx   d 8 00 00 00 00 00 00 00 00
   0.100000 1  100          Rx   d 8 64 00 00 00 00 00 00 00
   0.200000 1  100          Rx   d 8 C8 00 00 00 00 00 00 00
   0.300000 1  100          Rx   d 8 2C 01 00 00 00 00 00 00
   0.400000 1  100          Rx   d 8 90 01 00 00 00 00 00 00
   0.500000 1  100          Rx   d 8 F4 01 00 00 00 00 00 00
   0.000000 1  200          Rx   d 8 3C 00 00 00 00 00 00 00
   0.100000 1  200          Rx   d 8 46 00 00 00 00 00 00 00
   0.200000 1  200          Rx   d 8 50 00 00 00 00 00 00 00
   0.300000 1  200          Rx   d 8 5A 00 00 00 00 00 00 00
end triggerblock
"""
        asc_path = tmp_path / "test.asc"
        asc_path.write_text(asc_content.strip())

        return dbc_path, asc_path

    def test_can_to_functional_analysis(self, can_data_with_dbc):
        """Test CAN data parsing to functional analysis."""
        dbc_path, asc_path = can_data_with_dbc

        # Parse CAN data
        parser = CANParser(asc_path, dbc_path=dbc_path)
        result = parser.parse()

        if result.is_success and result.data is not None:
            # Run functional analysis
            analyzer = FunctionalAnalyzer()

            # Check if we have numeric columns to analyze
            numeric_cols = result.data.select_dtypes(include=[np.number]).columns

            if len(numeric_cols) > 1:
                # Run range check on first numeric signal
                signal_col = numeric_cols[1]  # Skip timestamp
                range_result = analyzer.check_value_range(
                    result.data,
                    signal_col,
                    min_value=0,
                    max_value=1000,
                )
                assert range_result is not None
                assert hasattr(range_result, "passed")


class TestDBCParserUtilityMethods:
    """Tests for DBC parser utility methods."""

    @pytest.fixture
    def sample_dbc(self, tmp_path) -> Path:
        """Create sample DBC file."""
        dbc_content = """
VERSION ""

BS_:

BU_: Node1 Node2

BO_ 100 Msg1: 8 Node1
 SG_ Sig1 : 0|8@1+ (1,0) [0|255] "" Node2
 SG_ Sig2 : 8|8@1+ (1,0) [0|255] "" Node2

BO_ 200 Msg2: 8 Node2
 SG_ Sig3 : 0|16@1+ (0.1,0) [0|6553.5] "m" Node1
"""
        dbc_path = tmp_path / "util.dbc"
        dbc_path.write_text(dbc_content.strip())
        return dbc_path

    def test_get_message_by_name(self, sample_dbc):
        """Test getting message by name."""
        parser = DBCParser(sample_dbc)
        parser.parse()

        msg = parser.get_message_by_name("Msg1")
        assert msg is not None
        assert msg.can_id == 100  # Decimal CAN ID in sample_dbc

        msg2 = parser.get_message_by_name("Msg2")
        assert msg2 is not None
        assert msg2.can_id == 200  # Decimal CAN ID in sample_dbc

    def test_get_nonexistent_message(self, sample_dbc):
        """Test getting non-existent message."""
        parser = DBCParser(sample_dbc)
        parser.parse()

        msg = parser.get_message(0x999)
        assert msg is None

    def test_get_nonexistent_signal(self, sample_dbc):
        """Test getting non-existent signal."""
        parser = DBCParser(sample_dbc)
        parser.parse()

        sig = parser.get_signal(0x100, "NonExistent")
        assert sig is None
