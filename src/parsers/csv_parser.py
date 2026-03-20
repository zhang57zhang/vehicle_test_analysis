"""
CSV and text log file parser.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from src.parsers.base_parser import BaseParser, ParseResult, ParserStatus


class CSVParser(BaseParser):
    """
    Parser for CSV and text log files.
    """

    SUPPORTED_EXTENSIONS = [".csv", ".txt", ".log"]

    def __init__(
        self,
        file_path: Optional[Path] = None,
        delimiter: str = ",",
        time_column: Optional[str] = None,
        time_format: Optional[str] = None,
        encoding: Optional[str] = None,
    ):
        """
        Initialize CSV parser.

        Args:
            file_path: Path to the file.
            delimiter: Column delimiter character.
            time_column: Name of the time column.
            time_format: Strptime format for time column.
            encoding: File encoding (auto-detected if None).
        """
        super().__init__(file_path)
        self.delimiter = delimiter
        self.time_column = time_column
        self.time_format = time_format
        self.encoding = encoding
        self._data: Optional[pd.DataFrame] = None
        self._signals: List[str] = []

    def parse(self, file_path: Optional[Path] = None) -> ParseResult:
        """
        Parse CSV file.

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
            # Detect encoding if not specified
            encoding = self.encoding or self._detect_encoding(path)

            # Try to read CSV with various options
            df = self._read_csv_with_fallback(path, encoding)

            if df is None or df.empty:
                return ParseResult(
                    status=ParserStatus.ERROR,
                    error_message="Failed to read CSV file or file is empty",
                )

            # Process time column if specified
            if self.time_column and self.time_column in df.columns:
                df = self._process_time_column(df)

            # Store data and signals
            self._data = df
            self._signals = [col for col in df.columns if col != self.time_column]

            # Build metadata
            self._metadata = {
                "file_name": path.name,
                "file_size": path.stat().st_size,
                "encoding": encoding,
                "delimiter": self.delimiter,
                "row_count": len(df),
                "column_count": len(df.columns),
                "columns": list(df.columns),
            }

            if self.time_column and self.time_column in df.columns:
                time_col = df[self.time_column]
                self._metadata["time_range"] = {
                    "start": float(time_col.min()),
                    "end": float(time_col.max()),
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
                error_message=f"Error parsing CSV: {e}",
            )

    def _read_csv_with_fallback(
        self, path: Path, encoding: str
    ) -> Optional[pd.DataFrame]:
        """
        Try reading CSV with various options.

        Args:
            path: File path.
            encoding: File encoding.

        Returns:
            DataFrame or None if all attempts fail.
        """
        read_options = [
            {"sep": self.delimiter, "encoding": encoding},
            {"sep": ";", "encoding": encoding},
            {"sep": "\t", "encoding": encoding},
            {"sep": ",", "encoding": encoding},
            {"sep": self.delimiter, "encoding": "utf-8"},
            {"sep": self.delimiter, "encoding": "latin-1"},
        ]

        for options in read_options:
            try:
                df = pd.read_csv(path, **options)
                if not df.empty:
                    return df
            except Exception:
                continue

        return None

    def _process_time_column(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Process time column to convert to numeric.

        Args:
            df: Input DataFrame.

        Returns:
            DataFrame with processed time column.
        """
        time_col = df[self.time_column]

        # If already numeric, return as-is
        if pd.api.types.is_numeric_dtype(time_col):
            return df

        # Try to convert to numeric
        try:
            df[self.time_column] = pd.to_numeric(time_col, errors="coerce")
            return df
        except Exception:
            pass

        # Try to parse as datetime
        try:
            if self.time_format:
                df[self.time_column] = pd.to_datetime(
                    time_col, format=self.time_format
                ).astype(float)
            else:
                df[self.time_column] = pd.to_datetime(time_col).astype(float)
            return df
        except Exception:
            pass

        # If all else fails, create a sequential time index
        df[self.time_column] = range(len(df))
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
    ) -> Optional[pd.DataFrame]:
        """
        Get parsed data, optionally filtered.

        Args:
            signals: List of signals to include (all if None).
            time_range: (start, end) time range to filter.

        Returns:
            Filtered DataFrame or None if not parsed.
        """
        if self._data is None:
            return None

        df = self._data.copy()

        if time_range and self.time_column and self.time_column in df.columns:
            start, end = time_range
            mask = (df[self.time_column] >= start) & (df[self.time_column] <= end)
            df = df[mask]

        if signals:
            columns = [self.time_column] + signals if self.time_column else signals
            columns = [c for c in columns if c in df.columns]
            df = df[columns]

        return df
