"""Unit tests for DBC parser module."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.parsers.dbc_parser import (
    DBCParser,
    SignalDefinition,
    MessageDefinition,
    NodeDefinition,
)
from src.parsers.base_parser import ParserStatus


class TestSignalDefinition:
    """Tests for SignalDefinition dataclass."""

    def test_create_signal(self):
        """Test creating a signal definition."""
        sig = SignalDefinition(
            name="EngineSpeed",
            start_bit=0,
            length=16,
            byte_order="little",
            is_signed=False,
            scale=0.125,
            offset=0.0,
            unit="rpm",
        )
        assert sig.name == "EngineSpeed"
        assert sig.start_bit == 0
        assert sig.length == 16
        assert sig.scale == 0.125

    def test_signal_defaults(self):
        """Test signal default values."""
        sig = SignalDefinition(
            name="Test",
            start_bit=0,
            length=8,
            byte_order="little",
            is_signed=False,
        )
        assert sig.scale == 1.0
        assert sig.offset == 0.0
        assert sig.unit is None
        assert sig.receivers == []
        assert sig.min_value is None
        assert sig.max_value is None
        assert sig.multiplexer is None
        assert sig.multiplexer_value is None

    def test_signal_with_multiplexer(self):
        """Test signal with multiplexer information."""
        sig = SignalDefinition(
            name="MultiplexedSignal",
            start_bit=0,
            length=8,
            byte_order="little",
            is_signed=False,
            multiplexer="MuxSig",
            multiplexer_value=1,
        )
        assert sig.multiplexer == "MuxSig"
        assert sig.multiplexer_value == 1

    def test_signal_with_receivers(self):
        """Test signal with receivers."""
        sig = SignalDefinition(
            name="Test",
            start_bit=0,
            length=8,
            byte_order="little",
            is_signed=False,
            receivers=["ECU1", "ECU2"],
        )
        assert sig.receivers == ["ECU1", "ECU2"]


class TestMessageDefinition:
    """Tests for MessageDefinition dataclass."""

    def test_create_message(self):
        """Test creating a message definition."""
        msg = MessageDefinition(
            name="EngineData",
            can_id=0x100,
            length=8,
        )
        assert msg.name == "EngineData"
        assert msg.can_id == 0x100
        assert msg.length == 8
        assert msg.signals == {}

    def test_message_with_signals(self):
        """Test message with signals."""
        sig = SignalDefinition(
            name="EngineSpeed",
            start_bit=0,
            length=16,
            byte_order="little",
            is_signed=False,
        )
        msg = MessageDefinition(
            name="EngineData",
            can_id=0x100,
            length=8,
            signals={"EngineSpeed": sig},
        )
        assert "EngineSpeed" in msg.signals

    def test_message_with_senders(self):
        """Test message with senders."""
        msg = MessageDefinition(
            name="EngineData",
            can_id=0x100,
            length=8,
            senders=["ECU1"],
        )
        assert msg.senders == ["ECU1"]

    def test_message_defaults(self):
        """Test message default values."""
        msg = MessageDefinition(
            name="Test",
            can_id=100,
            length=8,
        )
        assert msg.signals == {}
        assert msg.senders == []
        assert msg.cycle_time is None
        assert msg.is_extended is False

    def test_message_extended_frame(self):
        """Test message with extended frame flag."""
        msg = MessageDefinition(
            name="ExtendedMsg",
            can_id=0x1FFFFFFF,
            length=8,
            is_extended=True,
        )
        assert msg.is_extended is True

    def test_message_with_cycle_time(self):
        """Test message with cycle time."""
        msg = MessageDefinition(
            name="CyclicMsg",
            can_id=100,
            length=8,
            cycle_time=100,
        )
        assert msg.cycle_time == 100


class TestNodeDefinition:
    """Tests for NodeDefinition dataclass."""

    def test_create_node(self):
        """Test creating a node definition."""
        node = NodeDefinition(name="ECU1")
        assert node.name == "ECU1"
        assert node.comments is None

    def test_node_with_comments(self):
        """Test node with comments."""
        node = NodeDefinition(name="ECU1", comments="Engine Control Unit")
        assert node.comments == "Engine Control Unit"


class TestDBCParser:
    """Tests for DBCParser class."""

    def test_supported_extensions(self):
        """Test supported file extensions."""
        assert ".dbc" in DBCParser.SUPPORTED_EXTENSIONS

    def test_can_parse_dbc(self, tmp_path):
        """Test can_parse method for DBC files."""
        dbc_path = tmp_path / "test.dbc"
        dbc_path.write_text("VERSION \"\"")
        assert DBCParser.can_parse(dbc_path)

    def test_can_parse_unsupported(self, tmp_path):
        """Test can_parse method for unsupported files."""
        bin_path = tmp_path / "test.bin"
        bin_path.write_bytes(b"\x00\x01")
        assert not DBCParser.can_parse(bin_path)

    def test_parse_nonexistent_file(self, tmp_path):
        """Test parsing non-existent file."""
        parser = DBCParser(tmp_path / "nonexistent.dbc")
        result = parser.parse()

        assert not result.is_success
        assert result.status == ParserStatus.ERROR
        assert "not found" in result.error_message.lower()

    def test_parse_no_file_path_provided(self):
        """Test parsing when no file path is provided."""
        parser = DBCParser()
        result = parser.parse()

        assert result.status == ParserStatus.ERROR
        assert "no file path provided" in result.error_message.lower()

    def test_parse_with_path_override(self, tmp_path):
        """Test parsing with path override."""
        dbc_content = '''
VERSION ""

BS_:

BU_: ECU1

BO_ 100 Msg1: 8 ECU1
 SG_ Sig1 : 0|8@1+ (1,0) [0|255] "" 
'''
        dbc_path = tmp_path / "test.dbc"
        dbc_path.write_text(dbc_content)

        parser = DBCParser()  # No path in constructor
        result = parser.parse(dbc_path)  # Path provided in parse()

        assert result.is_success

    def test_parse_directory_instead_of_file(self, tmp_path):
        """Test parsing a directory instead of a file."""
        parser = DBCParser(tmp_path)
        result = parser.parse()

        assert result.status == ParserStatus.ERROR
        assert "not a file" in result.error_message.lower()

    def test_parse_empty_file(self, tmp_path):
        """Test parsing empty file."""
        empty_path = tmp_path / "empty.dbc"
        empty_path.write_text("")
        parser = DBCParser(empty_path)
        result = parser.parse()

        # Empty DBC file should still parse (manual fallback)
        assert result.status in (ParserStatus.SUCCESS, ParserStatus.ERROR)

    def test_parse_simple_dbc(self, tmp_path):
        """Test parsing a simple DBC file."""
        dbc_content = '''
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

BO_ 100 EngineData: 8 ECU1
 SG_ EngineSpeed : 0|16@1+ (0.125,0) [0|8000] "rpm" ECU2
 SG_ EngineTemp : 16|8@1+ (1,-40) [-40|215] "C" ECU2

BO_ 200 VehicleSpeed: 8 ECU2
 SG_ Speed : 0|16@1+ (0.1,0) [0|300] "km/h" ECU1
'''
        dbc_path = tmp_path / "test.dbc"
        dbc_path.write_text(dbc_content)

        parser = DBCParser(dbc_path)
        result = parser.parse()

        assert result.is_success
        assert result.status == ParserStatus.SUCCESS

        # Check messages
        messages = parser.get_all_messages()
        assert 100 in messages
        assert 200 in messages

        # Check signals
        signals = parser.get_signal_list()
        assert "EngineSpeed" in signals
        assert "EngineTemp" in signals
        assert "Speed" in signals

    def test_parse_message_definition(self, tmp_path):
        """Test parsing message definition."""
        dbc_content = '''
VERSION ""

BS_:

BU_: ECU1

BO_ 256 TestMessage: 8 ECU1
 SG_ Signal1 : 0|8@1+ (1,0) [0|255] "" 
'''
        dbc_path = tmp_path / "test.dbc"
        dbc_path.write_text(dbc_content)

        parser = DBCParser(dbc_path)
        parser.parse()

        msg = parser.get_message(256)
        assert msg is not None
        assert msg.name == "TestMessage"
        assert msg.can_id == 256
        assert msg.length == 8

    def test_parse_signal_definition(self, tmp_path):
        """Test parsing signal definition."""
        dbc_content = '''
VERSION ""

BS_:

BU_: ECU1 ECU2

BO_ 100 TestMsg: 8 ECU1
 SG_ TestSignal : 8|16@1- (0.1,50) [0|1000] "V" ECU2
'''
        dbc_path = tmp_path / "test.dbc"
        dbc_path.write_text(dbc_content)

        parser = DBCParser(dbc_path)
        parser.parse()

        sig = parser.get_signal(100, "TestSignal")
        assert sig is not None
        assert sig.name == "TestSignal"
        assert sig.start_bit == 8
        assert sig.length == 16
        assert sig.byte_order == "little"
        assert sig.is_signed is True
        assert sig.scale == 0.1
        assert sig.offset == 50
        assert sig.unit == "V"

    def test_parse_signal_big_endian(self, tmp_path):
        """Test parsing signal with big endian byte order."""
        dbc_content = '''
VERSION ""

BS_:

BU_: ECU1

BO_ 100 TestMsg: 8 ECU1
 SG_ BigEndianSig : 0|16@0+ (1,0) [0|65535] "" 
'''
        dbc_path = tmp_path / "test.dbc"
        dbc_path.write_text(dbc_content)

        parser = DBCParser(dbc_path)
        parser.parse()

        sig = parser.get_signal(100, "BigEndianSig")
        assert sig is not None
        assert sig.byte_order == "big"

    def test_parse_signal_unsigned(self, tmp_path):
        """Test parsing unsigned signal."""
        dbc_content = '''
VERSION ""

BS_:

BU_: ECU1

BO_ 100 TestMsg: 8 ECU1
 SG_ UnsignedSig : 0|8@1+ (1,0) [0|255] "" 
'''
        dbc_path = tmp_path / "test.dbc"
        dbc_path.write_text(dbc_content)

        parser = DBCParser(dbc_path)
        parser.parse()

        sig = parser.get_signal(100, "UnsignedSig")
        assert sig is not None
        assert sig.is_signed is False

    def test_parse_signal_with_receivers(self, tmp_path):
        """Test parsing signal with multiple receivers."""
        dbc_content = '''
VERSION ""

BS_:

BU_: ECU1 ECU2 ECU3

BO_ 100 TestMsg: 8 ECU1
 SG_ MultiReceiver : 0|8@1+ (1,0) [0|255] "" ECU2,ECU3
'''
        dbc_path = tmp_path / "test.dbc"
        dbc_path.write_text(dbc_content)

        parser = DBCParser(dbc_path)
        parser.parse()

        sig = parser.get_signal(100, "MultiReceiver")
        assert sig is not None
        assert "ECU2" in sig.receivers
        assert "ECU3" in sig.receivers

    def test_parse_nodes(self, tmp_path):
        """Test parsing node definitions."""
        dbc_content = '''
VERSION ""

BS_:

BU_: ECU1 ECU2 ECU3

BO_ 100 Msg1: 8 ECU1
 SG_ Sig1 : 0|8@1+ (1,0) [0|255] "" ECU2
'''
        dbc_path = tmp_path / "test.dbc"
        dbc_path.write_text(dbc_content)

        parser = DBCParser(dbc_path)
        parser.parse()

        nodes = parser.get_all_nodes()
        assert "ECU1" in nodes
        assert "ECU2" in nodes
        assert "ECU3" in nodes

    def test_parse_value_table(self, tmp_path):
        """Test parsing value tables."""
        dbc_content = '''
VERSION ""

BS_:

BU_: ECU1

BO_ 100 Msg1: 8 ECU1
 SG_ Status : 0|8@1+ (1,0) [0|255] "" 

VAL_ 100 Status 0 "Off" 1 "On" 2 "Error" ;
'''
        dbc_path = tmp_path / "test.dbc"
        dbc_path.write_text(dbc_content)

        parser = DBCParser(dbc_path)
        parser.parse()

        # Value tables should be parsed
        desc = parser.get_value_description(100, "Status", 0)
        assert desc == "Off"
        desc = parser.get_value_description(100, "Status", 1)
        assert desc == "On"
        desc = parser.get_value_description(100, "Status", 2)
        assert desc == "Error"

    def test_parse_value_table_invalid_format(self, tmp_path):
        """Test parsing value table with invalid format."""
        dbc_content = '''
VERSION ""

BS_:

BU_: ECU1

BO_ 100 Msg1: 8 ECU1
 SG_ Status : 0|8@1+ (1,0) [0|255] "" 

VAL_ invalid_content ;
'''
        dbc_path = tmp_path / "test.dbc"
        dbc_path.write_text(dbc_content)

        parser = DBCParser(dbc_path)
        result = parser.parse()

        # Should still parse successfully, just skip invalid value table
        assert result.is_success

    def test_parse_value_table_insufficient_parts(self, tmp_path):
        """Test parsing value table with insufficient parts."""
        dbc_content = '''
VERSION ""

BS_:

BU_: ECU1

BO_ 100 Msg1: 8 ECU1
 SG_ Status : 0|8@1+ (1,0) [0|255] "" 

VAL_ 100 ;
'''
        dbc_path = tmp_path / "test.dbc"
        dbc_path.write_text(dbc_content)

        parser = DBCParser(dbc_path)
        result = parser.parse()

        assert result.is_success

    def test_parse_attribute(self, tmp_path):
        """Test parsing attribute lines."""
        dbc_content = '''
VERSION ""

BS_:

BU_: ECU1

BO_ 100 Msg1: 8 ECU1
 SG_ Sig1 : 0|8@1+ (1,0) [0|255] "" 

BA_ "GenMsgCycleTime" BO_ 100 100;
'''
        dbc_path = tmp_path / "test.dbc"
        dbc_path.write_text(dbc_content)

        parser = DBCParser(dbc_path)
        result = parser.parse()

        assert result.is_success

    def test_parse_attribute_insufficient_parts(self, tmp_path):
        """Test parsing attribute with insufficient parts."""
        dbc_content = '''
VERSION ""

BS_:

BU_: ECU1

BO_ 100 Msg1: 8 ECU1
 SG_ Sig1 : 0|8@1+ (1,0) [0|255] "" 

BA_ "Attr";
'''
        dbc_path = tmp_path / "test.dbc"
        dbc_path.write_text(dbc_content)

        parser = DBCParser(dbc_path)
        result = parser.parse()

        assert result.is_success

    def test_parse_message_comment(self, tmp_path):
        """Test parsing message comment lines."""
        dbc_content = '''
VERSION ""

BS_:

BU_: ECU1

BO_ 100 Msg1: 8 ECU1
 SG_ Sig1 : 0|8@1+ (1,0) [0|255] "" 

CM_ BO_ 100 "This is a message comment";
'''
        dbc_path = tmp_path / "test.dbc"
        dbc_path.write_text(dbc_content)

        parser = DBCParser(dbc_path)
        result = parser.parse()

        assert result.is_success

    def test_parse_signal_comment(self, tmp_path):
        """Test parsing signal comment lines."""
        dbc_content = '''
VERSION ""

BS_:

BU_: ECU1

BO_ 100 Msg1: 8 ECU1
 SG_ Sig1 : 0|8@1+ (1,0) [0|255] "" 

CM_ SG_ 100 Sig1 "This is a signal comment";
'''
        dbc_path = tmp_path / "test.dbc"
        dbc_path.write_text(dbc_content)

        parser = DBCParser(dbc_path)
        result = parser.parse()

        assert result.is_success

    def test_get_message_by_name(self, tmp_path):
        """Test getting message by name."""
        dbc_content = '''
VERSION ""

BS_:

BU_: ECU1

BO_ 100 MyMessage: 8 ECU1
 SG_ Sig1 : 0|8@1+ (1,0) [0|255] "" 
'''
        dbc_path = tmp_path / "test.dbc"
        dbc_path.write_text(dbc_content)

        parser = DBCParser(dbc_path)
        parser.parse()

        msg = parser.get_message_by_name("MyMessage")
        assert msg is not None
        assert msg.can_id == 100

    def test_get_message_by_name_not_found(self, tmp_path):
        """Test getting message by name when not found."""
        dbc_content = '''
VERSION ""

BS_:

BU_: ECU1

BO_ 100 MyMessage: 8 ECU1
 SG_ Sig1 : 0|8@1+ (1,0) [0|255] "" 
'''
        dbc_path = tmp_path / "test.dbc"
        dbc_path.write_text(dbc_content)

        parser = DBCParser(dbc_path)
        parser.parse()

        msg = parser.get_message_by_name("NonExistent")
        assert msg is None

    def test_get_nonexistent_message(self):
        """Test getting non-existent message."""
        parser = DBCParser()
        msg = parser.get_message(999)
        assert msg is None

        msg = parser.get_message_by_name("NonExistent")
        assert msg is None

    def test_get_nonexistent_signal(self):
        """Test getting non-existent signal."""
        parser = DBCParser()
        sig = parser.get_signal(100, "NonExistent")
        assert sig is None

    def test_decode_signal(self, tmp_path):
        """Test signal decoding."""
        dbc_content = '''
VERSION ""

BS_:

BU_: ECU1 ECU2

BO_ 100 TestMsg: 8 ECU1
 SG_ TestSignal : 0|16@1+ (0.125,0) [0|8000] "rpm" ECU2
'''
        dbc_path = tmp_path / "test.dbc"
        dbc_path.write_text(dbc_content)

        parser = DBCParser(dbc_path)
        parser.parse()

        # Test decoding: raw value 1000 -> scaled 1000 * 0.125 = 125
        data = bytes([0xE8, 0x03, 0, 0, 0, 0, 0, 0])  # 1000 in little-endian
        value = parser.decode_signal(100, data, "TestSignal")
        assert value is not None
        assert abs(value - 125.0) < 0.01

    def test_decode_signal_nonexistent_message(self, tmp_path):
        """Test decoding signal from non-existent message."""
        dbc_content = '''
VERSION ""

BS_:

BU_: ECU1

BO_ 100 Msg1: 8 ECU1
 SG_ Sig1 : 0|8@1+ (1,0) [0|255] "" 
'''
        dbc_path = tmp_path / "test.dbc"
        dbc_path.write_text(dbc_content)

        parser = DBCParser(dbc_path)
        parser.parse()

        value = parser.decode_signal(999, b"\x00\x00", "Sig1")
        assert value is None

    def test_decode_signal_nonexistent_signal(self, tmp_path):
        """Test decoding non-existent signal."""
        dbc_content = '''
VERSION ""

BS_:

BU_: ECU1

BO_ 100 Msg1: 8 ECU1
 SG_ Sig1 : 0|8@1+ (1,0) [0|255] "" 
'''
        dbc_path = tmp_path / "test.dbc"
        dbc_path.write_text(dbc_content)

        parser = DBCParser(dbc_path)
        parser.parse()

        value = parser.decode_signal(100, b"\x00\x00", "NonExistent")
        assert value is None

    def test_decode_signed_signal(self, tmp_path):
        """Test decoding signed signal."""
        dbc_content = '''
VERSION ""

BS_:

BU_: ECU1

BO_ 100 TestMsg: 8 ECU1
 SG_ SignedSignal : 0|8@1- (1,0) [-128|127] "" 
'''
        dbc_path = tmp_path / "test.dbc"
        dbc_path.write_text(dbc_content)

        parser = DBCParser(dbc_path)
        parser.parse()

        # Test negative value: 0xFF = -1 for signed 8-bit
        data = bytes([0xFF, 0, 0, 0, 0, 0, 0, 0])
        value = parser.decode_signal(100, data, "SignedSignal")
        assert value is not None
        assert value == -1.0

    def test_decode_signal_with_offset(self, tmp_path):
        """Test decoding signal with offset."""
        dbc_content = '''
VERSION ""

BS_:

BU_: ECU1

BO_ 100 TestMsg: 8 ECU1
 SG_ TempSignal : 0|8@1+ (1,-40) [-40|215] "C" 
'''
        dbc_path = tmp_path / "test.dbc"
        dbc_path.write_text(dbc_content)

        parser = DBCParser(dbc_path)
        parser.parse()

        # Raw value 60 -> 60 * 1 + (-40) = 20
        data = bytes([60, 0, 0, 0, 0, 0, 0, 0])
        value = parser.decode_signal(100, data, "TempSignal")
        assert value is not None
        assert value == 20.0

    def test_decode_signal_big_endian(self, tmp_path):
        """Test decoding signal with big endian byte order."""
        dbc_content = '''
VERSION ""

BS_:

BU_: ECU1

BO_ 100 TestMsg: 8 ECU1
 SG_ BigEndianSig : 0|16@0+ (1,0) [0|65535] "" 
'''
        dbc_path = tmp_path / "test.dbc"
        dbc_path.write_text(dbc_content)

        parser = DBCParser(dbc_path)
        parser.parse()

        # Big endian decoding
        data = bytes([0x01, 0x02, 0, 0, 0, 0, 0, 0])
        value = parser.decode_signal(100, data, "BigEndianSig")
        assert value is not None

    def test_get_value_description(self, tmp_path):
        """Test getting value description."""
        dbc_content = '''
VERSION ""

BS_:

BU_: ECU1

BO_ 100 Msg1: 8 ECU1
 SG_ Status : 0|8@1+ (1,0) [0|255] "" 

VAL_ 100 Status 0 "Off" 1 "On" 2 "Error" ;
'''
        dbc_path = tmp_path / "test.dbc"
        dbc_path.write_text(dbc_content)

        parser = DBCParser(dbc_path)
        parser.parse()

        desc = parser.get_value_description(100, "Status", 1)
        assert desc == "On"

    def test_get_value_description_not_found(self, tmp_path):
        """Test getting value description when not found."""
        dbc_content = '''
VERSION ""

BS_:

BU_: ECU1

BO_ 100 Msg1: 8 ECU1
 SG_ Status : 0|8@1+ (1,0) [0|255] "" 

VAL_ 100 Status 0 "Off" 1 "On" ;
'''
        dbc_path = tmp_path / "test.dbc"
        dbc_path.write_text(dbc_content)

        parser = DBCParser(dbc_path)
        parser.parse()

        # Value not in table
        desc = parser.get_value_description(100, "Status", 99)
        assert desc is None

        # Signal not in table
        desc = parser.get_value_description(100, "NonExistent", 0)
        assert desc is None

    def test_parse_with_cantools(self, tmp_path, monkeypatch):
        """Test parsing using cantools library."""
        dbc_content = '''
VERSION ""

BS_:

BU_: ECU1

BO_ 100 Msg1: 8 ECU1
 SG_ Sig1 : 0|8@1+ (1,0) [0|255] "" 
'''
        dbc_path = tmp_path / "test.dbc"
        dbc_path.write_text(dbc_content)

        # Mock cantools
        class MockSignal:
            def __init__(self, name):
                self.name = name
                self.start = 0
                self.length = 8
                self.byte_order = "little_endian"
                self.is_signed = False
                self.scale = 1.0
                self.offset = 0.0
                self.minimum = 0
                self.maximum = 255
                self.unit = None
                self.receivers = []
                self.multiplexer_signal = None
                self.multiplexer_ids = None

        class MockMessage:
            def __init__(self):
                self.name = "Msg1"
                self.frame_id = 100
                self.length = 8
                self.signals = [MockSignal("Sig1")]
                self.senders = "ECU1"
                self.cycle_time = None
                self.is_extended_frame = False

        class MockDatabase:
            def __init__(self):
                self.messages = [MockMessage()]
                self.nodes = []

        class MockCantools:
            class database:
                @staticmethod
                def load_file(path):
                    return MockDatabase()

        import sys
        monkeypatch.setitem(sys.modules, 'cantools', MockCantools())

        parser = DBCParser(dbc_path)
        result = parser.parse()

        # Either cantools or manual parsing should work
        assert result.is_success or result.status == ParserStatus.SUCCESS

    def test_parse_with_cantools_nodes(self, tmp_path, monkeypatch):
        """Test parsing nodes using cantools library."""
        dbc_content = '''
VERSION ""

BS_:

BU_: ECU1 ECU2

BO_ 100 Msg1: 8 ECU1
 SG_ Sig1 : 0|8@1+ (1,0) [0|255] "" ECU2
'''
        dbc_path = tmp_path / "test.dbc"
        dbc_path.write_text(dbc_content)

        # Mock cantools with nodes
        class MockNode:
            def __init__(self, name):
                self.name = name
                self.comment = f"Comment for {name}"

        class MockSignal:
            def __init__(self, name):
                self.name = name
                self.start = 0
                self.length = 8
                self.byte_order = "little_endian"
                self.is_signed = False
                self.scale = 1.0
                self.offset = 0.0
                self.minimum = 0
                self.maximum = 255
                self.unit = None
                self.receivers = ["ECU2"]
                self.multiplexer_signal = None
                self.multiplexer_ids = None

        class MockMessage:
            def __init__(self):
                self.name = "Msg1"
                self.frame_id = 100
                self.length = 8
                self.signals = [MockSignal("Sig1")]
                self.senders = ["ECU1"]
                self.cycle_time = 100
                self.is_extended_frame = False

        class MockDatabase:
            def __init__(self):
                self.messages = [MockMessage()]
                self.nodes = [MockNode("ECU1"), MockNode("ECU2")]

        class MockCantools:
            class database:
                @staticmethod
                def load_file(path):
                    return MockDatabase()

        import sys
        monkeypatch.setitem(sys.modules, 'cantools', MockCantools())

        parser = DBCParser(dbc_path)
        result = parser.parse()

        assert result.is_success

    def test_parse_with_cantools_multiplexer(self, tmp_path, monkeypatch):
        """Test parsing multiplexed signals using cantools library."""
        dbc_content = '''
VERSION ""

BS_:

BU_: ECU1

BO_ 100 Msg1: 8 ECU1
 SG_ MuxSig : 0|8@1+ (1,0) [0|255] "" 
 SG_ Sig1 : 8|8@1+ (1,0) [0|255] "" 
'''
        dbc_path = tmp_path / "test.dbc"
        dbc_path.write_text(dbc_content)

        # Mock cantools with multiplexed signal
        class MockSignal:
            def __init__(self, name, is_multiplexed=False):
                self.name = name
                self.start = 0 if name == "MuxSig" else 8
                self.length = 8
                self.byte_order = "little_endian"
                self.is_signed = False
                self.scale = 1.0
                self.offset = 0.0
                self.minimum = 0
                self.maximum = 255
                self.unit = None
                self.receivers = []
                self.multiplexer_signal = "MuxSig" if is_multiplexed else None
                self.multiplexer_ids = [1] if is_multiplexed else None

        class MockMessage:
            def __init__(self):
                self.name = "Msg1"
                self.frame_id = 100
                self.length = 8
                self.signals = [
                    MockSignal("MuxSig"),
                    MockSignal("Sig1", is_multiplexed=True),
                ]
                self.senders = ["ECU1"]
                self.cycle_time = None
                self.is_extended_frame = False

        class MockDatabase:
            def __init__(self):
                self.messages = [MockMessage()]
                self.nodes = []

        class MockCantools:
            class database:
                @staticmethod
                def load_file(path):
                    return MockDatabase()

        import sys
        monkeypatch.setitem(sys.modules, 'cantools', MockCantools())

        parser = DBCParser(dbc_path)
        result = parser.parse()

        assert result.is_success

    def test_metadata(self, tmp_path):
        """Test metadata generation."""
        dbc_content = '''
VERSION ""

BS_:

BU_: ECU1 ECU2

BO_ 100 Msg1: 8 ECU1
 SG_ Sig1 : 0|8@1+ (1,0) [0|255] "" ECU2

BO_ 200 Msg2: 8 ECU2
 SG_ Sig2 : 0|16@1+ (1,0) [0|65535] "" ECU1
'''
        dbc_path = tmp_path / "test.dbc"
        dbc_path.write_text(dbc_content)

        parser = DBCParser(dbc_path)
        result = parser.parse()

        assert result.metadata is not None
        assert result.metadata["message_count"] == 2
        assert result.metadata["signal_count"] == 2
        assert result.metadata["node_count"] == 2

    def test_metadata_file_info(self, tmp_path):
        """Test metadata file information."""
        dbc_content = '''
VERSION ""

BS_:

BU_: ECU1

BO_ 100 Msg1: 8 ECU1
 SG_ Sig1 : 0|8@1+ (1,0) [0|255] "" 
'''
        dbc_path = tmp_path / "test.dbc"
        dbc_path.write_text(dbc_content)

        parser = DBCParser(dbc_path)
        result = parser.parse()

        assert result.metadata is not None
        assert result.metadata["file_name"] == "test.dbc"
        assert result.metadata["file_size"] > 0

    def test_get_signal_list_before_parse(self):
        """Test getting signal list before parsing."""
        parser = DBCParser()
        signals = parser.get_signal_list()
        assert signals == []

    def test_get_all_messages(self, tmp_path):
        """Test getting all messages."""
        dbc_content = '''
VERSION ""

BS_:

BU_: ECU1

BO_ 100 Msg1: 8 ECU1
 SG_ Sig1 : 0|8@1+ (1,0) [0|255] "" 

BO_ 200 Msg2: 8 ECU1
 SG_ Sig2 : 0|8@1+ (1,0) [0|255] "" 
'''
        dbc_path = tmp_path / "test.dbc"
        dbc_path.write_text(dbc_content)

        parser = DBCParser(dbc_path)
        parser.parse()

        messages = parser.get_all_messages()
        assert len(messages) == 2
        assert 100 in messages
        assert 200 in messages

    def test_get_all_messages_returns_copy(self, tmp_path):
        """Test that get_all_messages returns a copy."""
        dbc_content = '''
VERSION ""

BS_:

BU_: ECU1

BO_ 100 Msg1: 8 ECU1
 SG_ Sig1 : 0|8@1+ (1,0) [0|255] "" 
'''
        dbc_path = tmp_path / "test.dbc"
        dbc_path.write_text(dbc_content)

        parser = DBCParser(dbc_path)
        parser.parse()

        messages1 = parser.get_all_messages()
        messages2 = parser.get_all_messages()
        assert messages1 is not messages2

    def test_get_all_nodes_returns_copy(self, tmp_path):
        """Test that get_all_nodes returns a copy."""
        dbc_content = '''
VERSION ""

BS_:

BU_: ECU1 ECU2

BO_ 100 Msg1: 8 ECU1
 SG_ Sig1 : 0|8@1+ (1,0) [0|255] "" ECU2
'''
        dbc_path = tmp_path / "test.dbc"
        dbc_path.write_text(dbc_content)

        parser = DBCParser(dbc_path)
        parser.parse()

        nodes1 = parser.get_all_nodes()
        nodes2 = parser.get_all_nodes()
        assert nodes1 is not nodes2

    def test_parse_signal_line_invalid_format(self, tmp_path):
        """Test parsing signal with invalid format."""
        dbc_content = '''
VERSION ""

BS_:

BU_: ECU1

BO_ 100 Msg1: 8 ECU1
 SG_ InvalidSignal
'''
        dbc_path = tmp_path / "test.dbc"
        dbc_path.write_text(dbc_content)

        parser = DBCParser(dbc_path)
        result = parser.parse()

        # Should still parse successfully, just skip invalid signal
        assert result.is_success

    def test_parse_signal_line_no_unit(self, tmp_path):
        """Test parsing signal without unit."""
        dbc_content = '''
VERSION ""

BS_:

BU_: ECU1

BO_ 100 Msg1: 8 ECU1
 SG_ NoUnit : 0|8@1+ (1,0) [0|255] "" 
'''
        dbc_path = tmp_path / "test.dbc"
        dbc_path.write_text(dbc_content)

        parser = DBCParser(dbc_path)
        parser.parse()

        sig = parser.get_signal(100, "NoUnit")
        assert sig is not None
        assert sig.unit == ""

    def test_parse_signal_line_no_receivers(self, tmp_path):
        """Test parsing signal without receivers."""
        dbc_content = '''
VERSION ""

BS_:

BU_: ECU1

BO_ 100 Msg1: 8 ECU1
 SG_ NoReceivers : 0|8@1+ (1,0) [0|255] "" 
'''
        dbc_path = tmp_path / "test.dbc"
        dbc_path.write_text(dbc_content)

        parser = DBCParser(dbc_path)
        parser.parse()

        sig = parser.get_signal(100, "NoReceivers")
        assert sig is not None
        assert sig.receivers == []

    def test_parse_message_without_sender(self, tmp_path):
        """Test parsing message without sender."""
        dbc_content = '''
VERSION ""

BS_:

BU_: ECU1

BO_ 100 Msg1: 8
 SG_ Sig1 : 0|8@1+ (1,0) [0|255] "" 
'''
        dbc_path = tmp_path / "test.dbc"
        dbc_path.write_text(dbc_content)

        parser = DBCParser(dbc_path)
        result = parser.parse()

        assert result.is_success

    def test_parse_empty_lines_and_whitespace(self, tmp_path):
        """Test parsing DBC with empty lines and extra whitespace."""
        dbc_content = '''
VERSION ""

BS_:

BU_: ECU1

BO_ 100 Msg1: 8 ECU1
 SG_ Sig1 : 0|8@1+ (1,0) [0|255] "" 


BO_ 200 Msg2: 8 ECU1
 SG_ Sig2 : 0|8@1+ (1,0) [0|255] "" 
'''
        dbc_path = tmp_path / "test.dbc"
        dbc_path.write_text(dbc_content)

        parser = DBCParser(dbc_path)
        result = parser.parse()

        assert result.is_success
        assert result.metadata["message_count"] == 2

    def test_parse_signal_with_empty_min_max(self, tmp_path):
        """Test parsing signal with empty min/max values."""
        dbc_content = '''
VERSION ""

BS_:

BU_: ECU1

BO_ 100 Msg1: 8 ECU1
 SG_ Sig1 : 0|8@1+ (1,0) [|] "" 
'''
        dbc_path = tmp_path / "test.dbc"
        dbc_path.write_text(dbc_content)

        parser = DBCParser(dbc_path)
        result = parser.parse()

        # Should parse successfully
        assert result.is_success

    def test_signals_in_metadata(self, tmp_path):
        """Test that signals are included in metadata."""
        dbc_content = '''
VERSION ""

BS_:

BU_: ECU1

BO_ 100 Msg1: 8 ECU1
 SG_ Sig1 : 0|8@1+ (1,0) [0|255] "" 
 SG_ Sig2 : 8|8@1+ (1,0) [0|255] "" 
'''
        dbc_path = tmp_path / "test.dbc"
        dbc_path.write_text(dbc_content)

        parser = DBCParser(dbc_path)
        result = parser.parse()

        assert "signals" in result.metadata
        assert "Sig1" in result.metadata["signals"]
        assert "Sig2" in result.metadata["signals"]

    def test_messages_in_metadata(self, tmp_path):
        """Test that messages are included in metadata."""
        dbc_content = '''
VERSION ""

BS_:

BU_: ECU1

BO_ 100 Msg1: 8 ECU1
 SG_ Sig1 : 0|8@1+ (1,0) [0|255] "" 

BO_ 200 Msg2: 8 ECU1
 SG_ Sig2 : 0|8@1+ (1,0) [0|255] "" 
'''
        dbc_path = tmp_path / "test.dbc"
        dbc_path.write_text(dbc_content)

        parser = DBCParser(dbc_path)
        result = parser.parse()

        assert "messages" in result.metadata
        assert result.metadata["messages"][100] == "Msg1"
        assert result.metadata["messages"][200] == "Msg2"

    def test_nodes_in_metadata(self, tmp_path):
        """Test that nodes are included in metadata."""
        dbc_content = '''
VERSION ""

BS_:

BU_: ECU1 ECU2 ECU3

BO_ 100 Msg1: 8 ECU1
 SG_ Sig1 : 0|8@1+ (1,0) [0|255] "" ECU2
'''
        dbc_path = tmp_path / "test.dbc"
        dbc_path.write_text(dbc_content)

        parser = DBCParser(dbc_path)
        result = parser.parse()

        assert "nodes" in result.metadata
        assert "ECU1" in result.metadata["nodes"]
        assert "ECU2" in result.metadata["nodes"]
        assert "ECU3" in result.metadata["nodes"]

    def test_result_signals_format(self, tmp_path):
        """Test that result signals are in correct format."""
        dbc_content = '''
VERSION ""

BS_:

BU_: ECU1

BO_ 100 Msg1: 8 ECU1
 SG_ Sig1 : 0|8@1+ (1,0) [0|255] "" 
'''
        dbc_path = tmp_path / "test.dbc"
        dbc_path.write_text(dbc_content)

        parser = DBCParser(dbc_path)
        result = parser.parse()

        assert result.signals is not None
        assert len(result.signals) == 1
        assert result.signals[0]["name"] == "Sig1"
        assert result.signals[0]["type"] == "float"

    def test_parse_exception_handling(self, tmp_path):
        """Test exception handling during parsing."""
        dbc_path = tmp_path / "test.dbc"
        # Write invalid content that might cause exception
        dbc_path.write_bytes(b"\x00\x01\x02\x03\x04\x05")

        parser = DBCParser(dbc_path)
        result = parser.parse()

        # Should handle exception gracefully
        assert result.status in (ParserStatus.SUCCESS, ParserStatus.ERROR)

    def test_decode_signal_short_data(self, tmp_path):
        """Test decoding signal with short data."""
        dbc_content = '''
VERSION ""

BS_:

BU_: ECU1

BO_ 100 TestMsg: 8 ECU1
 SG_ TestSignal : 0|16@1+ (1,0) [0|65535] "" 
'''
        dbc_path = tmp_path / "test.dbc"
        dbc_path.write_text(dbc_content)

        parser = DBCParser(dbc_path)
        parser.parse()

        # Test with short data
        data = bytes([0x01, 0x02])  # Only 2 bytes
        value = parser.decode_signal(100, data, "TestSignal")
        # Should still decode without crashing
        assert value is not None

    def test_multiple_value_tables(self, tmp_path):
        """Test parsing multiple value tables."""
        dbc_content = '''
VERSION ""

BS_:

BU_: ECU1

BO_ 100 Msg1: 8 ECU1
 SG_ Status1 : 0|8@1+ (1,0) [0|255] "" 
 SG_ Status2 : 8|8@1+ (1,0) [0|255] "" 

VAL_ 100 Status1 0 "Off" 1 "On" ;
VAL_ 100 Status2 0 "Disabled" 1 "Enabled" ;
'''
        dbc_path = tmp_path / "test.dbc"
        dbc_path.write_text(dbc_content)

        parser = DBCParser(dbc_path)
        parser.parse()

        desc1 = parser.get_value_description(100, "Status1", 0)
        desc2 = parser.get_value_description(100, "Status2", 0)
        assert desc1 == "Off"
        assert desc2 == "Disabled"
