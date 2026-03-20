"""
MDF/MF4 file parser using asammdf.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd

from src.parsers.base_parser import BaseParser, ParseResult, ParserStatus


class MDFParser(BaseParser):
    """
    Parser for MDF (Measurement Data Format) files (.mdf, .mf4).
    """

    SUPPORTED_EXTENSIONS = [".mdf", ".mf4", ".dat"]

    def __init__(
        self,
        file_path: Optional[Path] = None,
        channels: Optional[List[str]] = None,
        time_from_zero: bool = True,
        raster: Optional[float] = None,
    ):
        """
        Initialize MDF parser.

        Args:
            file_path: Path to the MDF file.
            channels: List of channels to extract (all if None).
            time_from_zero: Whether to start time from zero.
            raster: Resample raster in seconds (None for original).
        """
        super().__init__(file_path)
        self.channels = channels
        self.time_from_zero = time_from_zero
        self.raster = raster
        self._data: Optional[pd.DataFrame] = None
        self._signals: List[str] = []
        self._mdf = None

    def parse(self, file_path: Optional[Path] = None) -> ParseResult:
        """
        Parse MDF file.

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
            # Import asammdf
            try:
                from asammdf import MDF
            except ImportError:
                return ParseResult(
                    status=ParserStatus.ERROR,
                    error_message="asammdf is required for MDF parsing. Install with: pip install asammdf",
                )

            # Open MDF file
            self._mdf = MDF(str(path))

            # Get available channels
            all_channels = self._mdf.channels_db.keys()
            
            # Filter channels if specified
            if self.channels:
                channels_to_extract = [
                    ch for ch in self.channels if ch in all_channels
                ]
                missing = set(self.channels) - set(channels_to_extract)
                if missing:
                    warnings.append(f"Channels not found: {missing}")
            else:
                # Exclude internal channels
                excluded_prefixes = ("time", "Time", "timestamp", "Timestamp")
                channels_to_extract = [
                    ch for ch in all_channels
                    if not any(ch.startswith(p) for p in excluded_prefixes)
                    and not ch.startswith("<")
                ]

            if not channels_to_extract:
                return ParseResult(
                    status=ParserStatus.ERROR,
                    error_message="No valid channels found to extract",
                )

            # Extract data
            df = self._extract_channels(channels_to_extract)

            if df is None or df.empty:
                return ParseResult(
                    status=ParserStatus.ERROR,
                    error_message="Failed to extract data from MDF file",
                )

            self._data = df
            self._signals = [col for col in df.columns if col != "time"]

            # Build metadata
            self._metadata = {
                "file_name": path.name,
                "file_size": path.stat().st_size,
                "version": self._mdf.version,
                "channels_count": len(all_channels),
                "extracted_channels": len(channels_to_extract),
                "row_count": len(df),
                "signals": self._signals,
                "time_range": {
                    "start": float(df["time"].min()),
                    "end": float(df["time"].max()),
                },
            }

            return ParseResult(
                status=ParserStatus.SUCCESS,
                data=df,
                metadata=self._metadata,
                signals=[{"name": s, "type": "float"} for s in self._signals],
                warnings=warnings if warnings else None,
            )

        except Exception as e:
            return ParseResult(
                status=ParserStatus.ERROR,
                error_message=f"Error parsing MDF file: {e}",
            )

    def _extract_channels(self, channels: List[str]) -> Optional[pd.DataFrame]:
        """
        Extract specified channels from MDF.

        Args:
            channels: List of channel names to extract.

        Returns:
            DataFrame with extracted data.
        """
        try:
            from asammdf import MDF

            # Resample if raster specified
            if self.raster:
                mdf_resampled = self._mdf.resample(self.raster)
            else:
                mdf_resampled = self._mdf

            # Extract each channel
            data_dict = {}
            time_array = None

            for channel in channels:
                try:
                    sig = mdf_resampled.get(channel)
                    if sig is not None:
                        if time_array is None and hasattr(sig, "timestamps"):
                            time_array = sig.timestamps
                        if hasattr(sig, "samples"):
                            data_dict[channel] = sig.samples
                except Exception:
                    continue

            if not data_dict:
                return None

            # Create time array if not available
            if time_array is None:
                # Use first channel's length to create time
                first_channel = list(data_dict.keys())[0]
                time_array = np.arange(len(data_dict[first_channel]))

            # Create DataFrame
            df = pd.DataFrame(data_dict, index=time_array)
            df.index.name = "time"
            df = df.reset_index()

            # Normalize time to start from zero
            if self.time_from_zero and "time" in df.columns:
                df["time"] = df["time"] - df["time"].iloc[0]

            return df

        except Exception as e:
            raise RuntimeError(f"Error extracting channels: {e}")

    def get_signal_list(self) -> List[str]:
        """
        Get list of available signals.

        Returns:
            List of signal names.
        """
        return self._signals.copy()

    def get_all_channels(self) -> List[str]:
        """
        Get list of all available channels in the MDF file.

        Returns:
            List of channel names.
        """
        if self._mdf is not None:
            return list(self._mdf.channels_db.keys())
        return []

    def get_data(
        self,
        signals: Optional[List[str]] = None,
        time_range: Optional[tuple] = None,
    ) -> Optional[pd.DataFrame]:
        """
        Get parsed data, optionally filtered.

        Args:
            signals: List of signals to include.
            time_range: (start, end) time range to filter.

        Returns:
            Filtered DataFrame or None.
        """
        if self._data is None:
            return None

        df = self._data.copy()

        if time_range and "time" in df.columns:
            start, end = time_range
            mask = (df["time"] >= start) & (df["time"] <= end)
            df = df[mask]

        if signals:
            columns = ["time"] + signals
            columns = [c for c in columns if c in df.columns]
            df = df[columns]

        return df

    def close(self) -> None:
        """Close the MDF file."""
        if self._mdf is not None:
            self._mdf.close()
            self._mdf = None

    def __del__(self):
        """Destructor to ensure file is closed."""
        self.close()
