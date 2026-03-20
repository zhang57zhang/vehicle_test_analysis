"""
DBC (Database Container) file parser for CAN message definitions.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

from src.parsers.base_parser import BaseParser, ParseResult, ParserStatus


@dataclass
class SignalDefinition:
    """Definition of a CAN signal."""

    name: str
    start_bit: int
    length: int
    byte_order: str  # "little" or "big" (Motorola)
    is_signed: bool
    scale: float = 1.0
    offset: float = 0.0
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    unit: Optional[str] = None
    receivers: List[str] = field(default_factory=list)
    multiplexer: Optional[str] = None
    multiplexer_value: Optional[int] = None


@dataclass
class MessageDefinition:
    """Definition of a CAN message."""

    name: str
    can_id: int
    length: int
    signals: Dict[str, SignalDefinition] = field(default_factory=dict)
    senders: List[str] = field(default_factory=list)
    cycle_time: Optional[int] = None
    is_extended: bool = False


@dataclass
class NodeDefinition:
    """Definition of a CAN node."""

    name: str
    comments: Optional[str] = None


class DBCParser(BaseParser):
    """
    Parser for DBC (Database Container) files.
    
    DBC files define the structure of CAN messages and signals.
    """

    SUPPORTED_EXTENSIONS = [".dbc"]

    def __init__(self, file_path: Optional[Path] = None):
        """
        Initialize DBC parser.

        Args:
            file_path: Path to the DBC file.
        """
        super().__init__(file_path)
        self._messages: Dict[int, MessageDefinition] = {}
        self._nodes: Dict[str, NodeDefinition] = {}
        self._signals: List[str] = []
        self._value_tables: Dict[str, Dict[int, str]] = {}
        self._attributes: Dict[str, Any] = {}

    def parse(self, file_path: Optional[Path] = None) -> ParseResult:
        """
        Parse DBC file.

        Args:
            file_path: Optional path override.

        Returns:
            ParseResult with parsed definitions.
        """
        path = Path(file_path) if file_path else self.file_path
        if not path:
            return ParseResult(
                status=ParserStatus.ERROR,
                error_message="No file path provided",
            )

        try:
            self._validate_file(path)
        except (FileNotFoundError, PermissionError, ValueError) as e:
            return ParseResult(
                status=ParserStatus.ERROR,
                error_message=str(e),
            )

        warnings = []

        try:
            # Try using cantools first, fallback to manual parsing on any error
            # or if cantools fails to parse signals (e.g., empty units)
            use_manual = False
            try:
                import cantools

                db = cantools.database.load_file(str(path))
                self._parse_with_cantools(db)
                
                # Check if any signals were parsed - if not, fall back to manual
                total_signals = sum(len(msg.signals) for msg in self._messages.values())
                if total_signals == 0:
                    # cantools may have failed to parse signals due to format issues
                    use_manual = True
            except (ImportError, Exception):
                # Fallback to manual parsing
                use_manual = True
            
            if use_manual:
                self._parse_manual(path)

            # Collect all signal names
            self._signals = []
            for msg in self._messages.values():
                self._signals.extend(msg.signals.keys())

            # Build metadata
            self._metadata = {
                "file_name": path.name,
                "file_size": path.stat().st_size,
                "message_count": len(self._messages),
                "signal_count": len(self._signals),
                "node_count": len(self._nodes),
                "messages": {
                    msg_id: msg.name for msg_id, msg in self._messages.items()
                },
                "signals": self._signals,
                "nodes": list(self._nodes.keys()),
            }

            return ParseResult(
                status=ParserStatus.SUCCESS,
                data=None,  # DBC files don't have time-series data
                metadata=self._metadata,
                signals=[{"name": s, "type": "float"} for s in self._signals],
                warnings=warnings if warnings else None,
            )

        except Exception as e:
            return ParseResult(
                status=ParserStatus.ERROR,
                error_message=f"Error parsing DBC file: {e}",
            )

    def _parse_with_cantools(self, db) -> None:
        """
        Parse DBC using cantools library.

        Args:
            db: cantools database object.
        """
        # Parse messages
        for msg in db.messages:
            signals = {}
            for sig in msg.signals:
                signals[sig.name] = SignalDefinition(
                    name=sig.name,
                    start_bit=sig.start,
                    length=sig.length,
                    byte_order="little" if sig.byte_order == "little_endian" else "big",
                    is_signed=sig.is_signed,
                    scale=sig.scale,
                    offset=sig.offset,
                    min_value=sig.minimum,
                    max_value=sig.maximum,
                    unit=sig.unit,
                    receivers=sig.receivers or [],
                    multiplexer=sig.multiplexer_signal,
                    multiplexer_value=sig.multiplexer_ids[0] if sig.multiplexer_ids else None,
                )

            self._messages[msg.frame_id] = MessageDefinition(
                name=msg.name,
                can_id=msg.frame_id,
                length=msg.length,
                signals=signals,
                senders=[msg.senders] if isinstance(msg.senders, str) else msg.senders,
                cycle_time=msg.cycle_time,
                is_extended=msg.is_extended_frame,
            )

        # Parse nodes
        if hasattr(db, "nodes"):
            for node in db.nodes:
                self._nodes[node.name] = NodeDefinition(
                    name=node.name,
                    comments=node.comment,
                )

    def _parse_manual(self, path: Path) -> None:
        """
        Manual parsing of DBC file.

        Args:
            path: Path to DBC file.
        """
        encoding = self._detect_encoding(path)

        with open(path, "r", encoding=encoding, errors="replace") as f:
            content = f.read()

        lines = content.split("\n")
        current_msg = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Parse nodes
            if line.startswith("BU_:"):
                nodes = line[4:].split()
                for node in nodes:
                    if node:
                        self._nodes[node] = NodeDefinition(name=node)

            # Parse messages
            elif line.startswith("BO_ "):
                current_msg = self._parse_message_line(line)

            # Parse signals
            elif line.startswith("SG_ ") and current_msg is not None:
                sig = self._parse_signal_line(line)
                if sig:
                    current_msg.signals[sig.name] = sig

            # Parse value tables
            elif line.startswith("VAL_ "):
                self._parse_value_table_line(line)

            # Parse attributes
            elif line.startswith("BA_ "):
                self._parse_attribute_line(line)

            # Parse message comments
            elif line.startswith("CM_ BO_"):
                self._parse_message_comment(line, current_msg)

            # Parse signal comments
            elif line.startswith("CM_ SG_"):
                self._parse_signal_comment(line, current_msg)

    def _parse_message_line(self, line: str) -> MessageDefinition:
        """
        Parse a message definition line.

        Format: BO_ <can_id> <name>: <length> <sender>
        """
        parts = line.split()
        # Support both decimal and hex format CAN IDs (e.g., 100 or 0x100)
        can_id_str = parts[1]
        can_id = int(can_id_str, 16) if can_id_str.lower().startswith('0x') else int(can_id_str)
        name = parts[2].rstrip(":")
        length = int(parts[3])
        sender = parts[4] if len(parts) > 4 else ""

        msg = MessageDefinition(
            name=name,
            can_id=can_id,
            length=length,
            senders=[sender] if sender else [],
        )
        self._messages[can_id] = msg
        return msg

    def _parse_signal_line(self, line: str) -> Optional[SignalDefinition]:
        """
        Parse a signal definition line.

        Format: SG_ <name> : <start_bit>|<length>@<byte_order><sign> (<scale>,<offset>) [<min>|<max>] "<unit>" <receivers>
        """
        try:
            # Strip leading/trailing whitespace first
            line = line.strip()
            
            # Remove SG_ prefix
            if not line.startswith("SG_"):
                return None
            line = line[3:].strip()

            # Split by spaces, but keep quoted strings together
            parts = []
            current = ""
            in_quotes = False

            for char in line:
                if char == '"':
                    in_quotes = not in_quotes
                    current += char
                elif char == " " and not in_quotes:
                    if current:
                        parts.append(current)
                    current = ""
                else:
                    current += char
            if current:
                parts.append(current)

            if len(parts) < 2:
                return None

            name = parts[0]

            # Skip colon separator if present (SG_ Name : format)
            bit_index = 1
            if parts[1] == ":":
                bit_index = 2

            if len(parts) <= bit_index:
                return None

            # Parse bit position and length
            bit_info = parts[bit_index].split("@")
            start_bit, length = map(int, bit_info[0].split("|"))

            # Parse byte order and sign
            byte_order_sign = bit_info[1]
            byte_order = "little" if byte_order_sign[0] == "1" else "big"
            is_signed = byte_order_sign[1] == "-"

            # Parse scale and offset
            scale_offset = parts[bit_index + 1].strip("()").split(",")
            scale = float(scale_offset[0])
            offset = float(scale_offset[1])

            # Parse min and max
            min_max = parts[bit_index + 2].strip("[]").split("|")
            min_val = float(min_max[0]) if min_max[0] else None
            max_val = float(min_max[1]) if len(min_max) > 1 and min_max[1] else None

            # Parse unit - it's quoted, so we need to handle empty strings ""
            unit = None
            if len(parts) > bit_index + 3:
                unit = parts[bit_index + 3].strip('"')
                # Empty string unit is valid, keep as empty string

            # Parse receivers
            receivers = []
            if len(parts) > bit_index + 4:
                receivers = [r.strip() for r in parts[bit_index + 4].split(",") if r.strip()]

            return SignalDefinition(
                name=name,
                start_bit=start_bit,
                length=length,
                byte_order=byte_order,
                is_signed=is_signed,
                scale=scale,
                offset=offset,
                min_value=min_val,
                max_value=max_val,
                unit=unit,
                receivers=receivers,
            )

        except Exception:
            return None

    def _parse_value_table_line(self, line: str) -> None:
        """
        Parse a value table line.

        Format: VAL_ <can_id> <signal_name> <value1> "<description1>" ... ;
        """
        # Remove VAL_ prefix and trailing semicolon
        line = line[5:].rstrip(";").strip()
        parts = line.split()

        if len(parts) < 3:
            return

        try:
            can_id = int(parts[0])
            signal_name = parts[1]

            # Parse value-description pairs
            values = {}
            i = 2
            while i < len(parts):
                if i + 1 < len(parts):
                    value = int(parts[i])
                    desc = parts[i + 1].strip('"')
                    values[value] = desc
                    i += 2
                else:
                    break

            key = f"{can_id}_{signal_name}"
            self._value_tables[key] = values

        except (ValueError, IndexError):
            pass

    def _parse_attribute_line(self, line: str) -> None:
        """
        Parse an attribute line.

        Format: BA_ "<attribute_name>" <object_type> <object_id> <value>;
        """
        line = line[4:].rstrip(";").strip()
        parts = line.split()

        if len(parts) >= 4:
            attr_name = parts[0].strip('"')
            attr_value = parts[-1]
            self._attributes[attr_name] = attr_value

    def _parse_message_comment(self, line: str, current_msg: Optional[MessageDefinition]) -> None:
        """Parse message comment line."""
        pass  # Comments are optional, not critical for parsing

    def _parse_signal_comment(self, line: str, current_msg: Optional[MessageDefinition]) -> None:
        """Parse signal comment line."""
        pass  # Comments are optional, not critical for parsing

    def get_signal_list(self) -> List[str]:
        """
        Get list of all signals.

        Returns:
            List of signal names.
        """
        return self._signals.copy()

    def get_message(self, can_id: int) -> Optional[MessageDefinition]:
        """
        Get message definition by CAN ID.

        Args:
            can_id: CAN message ID.

        Returns:
            MessageDefinition or None.
        """
        return self._messages.get(can_id)

    def get_message_by_name(self, name: str) -> Optional[MessageDefinition]:
        """
        Get message definition by name.

        Args:
            name: Message name.

        Returns:
            MessageDefinition or None.
        """
        for msg in self._messages.values():
            if msg.name == name:
                return msg
        return None

    def get_signal(self, can_id: int, signal_name: str) -> Optional[SignalDefinition]:
        """
        Get signal definition.

        Args:
            can_id: CAN message ID.
            signal_name: Signal name.

        Returns:
            SignalDefinition or None.
        """
        msg = self._messages.get(can_id)
        if msg:
            return msg.signals.get(signal_name)
        return None

    def get_all_messages(self) -> Dict[int, MessageDefinition]:
        """
        Get all message definitions.

        Returns:
            Dictionary of CAN ID to MessageDefinition.
        """
        return self._messages.copy()

    def get_all_nodes(self) -> Dict[str, NodeDefinition]:
        """
        Get all node definitions.

        Returns:
            Dictionary of node name to NodeDefinition.
        """
        return self._nodes.copy()

    def decode_signal(
        self,
        can_id: int,
        data: bytes,
        signal_name: str,
    ) -> Optional[float]:
        """
        Decode a signal value from raw CAN data.

        Args:
            can_id: CAN message ID.
            data: Raw CAN data bytes.
            signal_name: Signal name to decode.

        Returns:
            Decoded signal value or None.
        """
        msg = self._messages.get(can_id)
        if not msg:
            return None

        sig = msg.signals.get(signal_name)
        if not sig:
            return None

        return self._decode_signal_value(data, sig)

    def _decode_signal_value(
        self,
        data: bytes,
        signal: SignalDefinition,
    ) -> float:
        """
        Decode signal value from raw bytes.

        Args:
            data: Raw CAN data bytes.
            signal: Signal definition.

        Returns:
            Decoded and scaled value.
        """
        # Convert bytes to integer
        raw_value = 0
        data_array = bytearray(data)

        if signal.byte_order == "little":
            # Little endian (Intel)
            for i, byte in enumerate(data_array):
                bit_offset = i * 8
                if signal.start_bit >= bit_offset and signal.start_bit < bit_offset + 8:
                    # Signal starts in this byte
                    pass

            # Simple extraction for aligned signals
            start_byte = signal.start_bit // 8
            bit_offset = signal.start_bit % 8

            value = 0
            for i in range((signal.length + bit_offset + 7) // 8):
                if start_byte + i < len(data_array):
                    value |= data_array[start_byte + i] << (i * 8)

            # Extract bits
            value = (value >> bit_offset) & ((1 << signal.length) - 1)

        else:
            # Big endian (Motorola)
            start_byte = signal.start_bit // 8
            bit_offset = signal.start_bit % 8

            value = 0
            for i in range((signal.length + 7) // 8):
                if start_byte + i < len(data_array):
                    value = (value << 8) | data_array[start_byte + i]

            # Extract bits
            value = (value >> (8 - bit_offset - signal.length % 8)) & ((1 << signal.length) - 1)

        # Handle signed values
        if signal.is_signed and value >= (1 << (signal.length - 1)):
            value -= 1 << signal.length

        # Apply scale and offset
        return float(value * signal.scale + signal.offset)

    def get_value_description(
        self,
        can_id: int,
        signal_name: str,
        value: int,
    ) -> Optional[str]:
        """
        Get description for a signal value.

        Args:
            can_id: CAN message ID.
            signal_name: Signal name.
            value: Signal value.

        Returns:
            Description string or None.
        """
        key = f"{can_id}_{signal_name}"
        value_table = self._value_tables.get(key, {})
        return value_table.get(value)
