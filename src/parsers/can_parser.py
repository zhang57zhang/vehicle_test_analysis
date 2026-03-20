"""
CAN log file parser for BLF and ASC formats.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from src.parsers.base_parser import BaseParser, ParseResult, ParserStatus


class CANParser(BaseParser):
    """
    Parser for CAN log files (.blf, .asc).
    """

    SUPPORTED_EXTENSIONS = [".blf", ".asc"]

    def __init__(
        self,
        file_path: Optional[Path] = None,
        dbc_path: Optional[Path] = None,
        ignore_invalid_frames: bool = True,
    ):
        """
        Initialize CAN parser.

        Args:
            file_path: Path to the CAN log file.
            dbc_path: Path to the DBC database file.
            ignore_invalid_frames: Whether to ignore invalid frames.
        """
        super().__init__(file_path)
        self.dbc_path = Path(dbc_path) if dbc_path else None
        self.ignore_invalid_frames = ignore_invalid_frames
        self._data: Optional[pd.DataFrame] = None
        self._signals: List[str] = []
        self._dbc_db = None

    def parse(self, file_path: Optional[Path] = None) -> ParseResult:
        """
        Parse CAN log file.

        Args:
            file_path: Optional path override.

        Returns:
            ParseResult with parsed data.
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
            # Load DBC if provided
            if self.dbc_path:
                try:
                    import cantools

                    self._dbc_db = cantools.database.load_file(str(self.dbc_path))
                except Exception as e:
                    warnings.append(f"Failed to load DBC file: {e}")

            # Parse based on file type
            suffix = path.suffix.lower()
            if suffix == ".blf":
                df = self._parse_blf(path)
            elif suffix == ".asc":
                df = self._parse_asc(path)
            else:
                return ParseResult(
                    status=ParserStatus.ERROR,
                    error_message=f"Unsupported file type: {suffix}",
                )

            if df is None or df.empty:
                return ParseResult(
                    status=ParserStatus.ERROR,
                    error_message="Failed to parse CAN file or file is empty",
                )

            self._data = df
            self._signals = [col for col in df.columns if col != "timestamp"]

            # Build metadata
            self._metadata = {
                "file_name": path.name,
                "file_size": path.stat().st_size,
                "file_type": suffix,
                "row_count": len(df),
                "signal_count": len(self._signals),
                "signals": self._signals,
                "time_range": {
                    "start": float(df["timestamp"].min()),
                    "end": float(df["timestamp"].max()),
                },
                "dbc_file": str(self.dbc_path) if self.dbc_path else None,
            }

            return ParseResult(
                status=ParserStatus.SUCCESS,
                data=df,
                metadata=self._metadata,
                signals=[{"name": s, "type": "float"} for s in self._signals],
                warnings=warnings if warnings else None,
            )

        except ImportError as e:
            return ParseResult(
                status=ParserStatus.ERROR,
                error_message=f"Required library not installed: {e}. Install python-can and cantools.",
            )
        except Exception as e:
            return ParseResult(
                status=ParserStatus.ERROR,
                error_message=f"Error parsing CAN file: {e}",
            )

    def _parse_blf(self, path: Path) -> Optional[pd.DataFrame]:
        """
        Parse BLF (Binary Log Format) file.

        Args:
            path: Path to BLF file.

        Returns:
            DataFrame with parsed signals.
        """
        try:
            import can

            # Read BLF file
            log = can.BLFReader(str(path))

            # Extract messages
            records = []
            for msg in log:
                record = {
                    "timestamp": msg.timestamp,
                    "can_id": msg.arbitration_id,
                    "dlc": msg.dlc,
                    "data": msg.data.hex() if msg.data else "",
                    "is_extended": msg.is_extended_id,
                    "channel": msg.channel,
                }

                # Decode with DBC if available
                if self._dbc_db:
                    try:
                        decoded = self._dbc_db.decode_message(
                            msg.arbitration_id, msg.data
                        )
                        for sig_name, sig_value in decoded.items():
                            record[sig_name] = sig_value
                    except Exception:
                        pass

                records.append(record)

            if not records:
                return None

            df = pd.DataFrame(records)

            return df

        except Exception as e:
            raise RuntimeError(f"Error parsing BLF file: {e}")

    def _parse_asc(self, path: Path) -> Optional[pd.DataFrame]:
        """
        Parse ASC (ASCII) format file.

        Args:
            path: Path to ASC file.

        Returns:
            DataFrame with parsed signals.
        """
        try:
            import can

            records = []
            reader = None

            # Try can.ASCReader first (python-can >= 4.0)
            if hasattr(can, "ASCReader"):
                reader = can.ASCReader(str(path))
            else:
                # Try can.io.asc.ASCReader (older versions)
                try:
                    from can.io.asc import ASCReader
                    reader = ASCReader(str(path))
                except ImportError:
                    pass

            if reader is not None:
                for msg in reader:
                    record = {
                        "timestamp": msg.timestamp,
                        "can_id": msg.arbitration_id,
                        "dlc": msg.dlc,
                        "data": msg.data.hex() if msg.data else "",
                        "is_extended": msg.is_extended_id,
                        "channel": msg.channel,
                    }

                    # Decode with DBC if available
                    if self._dbc_db:
                        try:
                            decoded = self._dbc_db.decode_message(
                                msg.arbitration_id, msg.data
                            )
                            for sig_name, sig_value in decoded.items():
                                record[sig_name] = sig_value
                        except Exception:
                            pass

                    records.append(record)

            if not records:
                # Fallback: manual parsing
                return self._parse_asc_manual(path)

            df = pd.DataFrame(records)

            return df

        except Exception as e:
            raise RuntimeError(f"Error parsing ASC file: {e}")

    def _parse_asc_manual(self, path: Path) -> Optional[pd.DataFrame]:
        """
        Manual parsing of ASC file (fallback).

        Args:
            path: Path to ASC file.

        Returns:
            DataFrame with parsed data.
        """
        records = []
        encoding = self._detect_encoding(path)

        with open(path, "r", encoding=encoding, errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("//"):
                    continue

                # Basic ASC format parsing
                # Format: timestamp channel CAN_ID Rx d DLC DATA
                parts = line.split()
                if len(parts) >= 6:
                    try:
                        timestamp = float(parts[0])
                        can_id = int(parts[2], 16)
                        dlc = int(parts[5])
                        data_hex = "".join(parts[6 : 6 + dlc])

                        records.append(
                            {
                                "timestamp": timestamp,
                                "can_id": can_id,
                                "dlc": dlc,
                                "data": data_hex,
                            }
                        )
                    except (ValueError, IndexError):
                        continue

        if not records:
            return None

        df = pd.DataFrame(records)

        return df

    def get_signal_list(self) -> List[str]:
        """
        Get list of available signals.

        Returns:
            List of signal names.
        """
        return self._signals.copy()

    def get_data(
        self,
        signals: Optional[List[str]] = None,
        time_range: Optional[tuple] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
    ) -> Optional[pd.DataFrame]:
        """
        Get parsed data, optionally filtered.

        Args:
            signals: List of signals to include.
            time_range: (start, end) time range to filter (deprecated, use start_time/end_time).
            start_time: Start time for filtering.
            end_time: End time for filtering.

        Returns:
            Filtered DataFrame or None.
        """
        if self._data is None:
            return None

        df = self._data.copy()

        # Support both time_range tuple and start_time/end_time parameters
        if time_range is not None:
            start, end = time_range
        else:
            start = start_time
            end = end_time

        if start is not None and end is not None and "timestamp" in df.columns:
            mask = (df["timestamp"] >= start) & (df["timestamp"] <= end)
            df = df[mask]

        if signals:
            columns = ["timestamp"] + signals
            columns = [c for c in columns if c in df.columns]
            df = df[columns]

        return df
