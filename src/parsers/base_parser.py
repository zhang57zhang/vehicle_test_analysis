"""
Base parser interface for all data format parsers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd


class ParserStatus(Enum):
    """Status of parser operation."""

    SUCCESS = "success"
    PARTIAL = "partial"
    ERROR = "error"


@dataclass
class ParseResult:
    """Result of a parsing operation."""

    status: ParserStatus
    data: Optional[pd.DataFrame] = None
    metadata: Optional[Dict[str, Any]] = None
    signals: Optional[List[Dict[str, Any]]] = None
    error_message: Optional[str] = None
    warnings: Optional[List[str]] = None

    @property
    def is_success(self) -> bool:
        """Check if parsing was successful."""
        return self.status in (ParserStatus.SUCCESS, ParserStatus.PARTIAL)


class BaseParser(ABC):
    """
    Abstract base class for all data format parsers.
    """

    # Supported file extensions (override in subclasses)
    SUPPORTED_EXTENSIONS: List[str] = []

    def __init__(self, file_path: Optional[Path] = None):
        """
        Initialize parser.

        Args:
            file_path: Path to the file to parse.
        """
        self.file_path = Path(file_path) if file_path else None
        self._metadata: Dict[str, Any] = {}

    @classmethod
    def can_parse(cls, file_path: Path) -> bool:
        """
        Check if this parser can handle the given file.

        Args:
            file_path: Path to the file.

        Returns:
            True if the parser can handle this file type.
        """
        return file_path.suffix.lower() in cls.SUPPORTED_EXTENSIONS

    @abstractmethod
    def parse(self, file_path: Optional[Path] = None) -> ParseResult:
        """
        Parse the file and return results.

        Args:
            file_path: Optional path override.

        Returns:
            ParseResult with parsed data and metadata.
        """
        pass

    @abstractmethod
    def get_signal_list(self) -> List[str]:
        """
        Get list of available signals in the parsed file.

        Returns:
            List of signal names.
        """
        pass

    def get_metadata(self) -> Dict[str, Any]:
        """
        Get metadata about the parsed file.

        Returns:
            Dictionary of metadata.
        """
        return self._metadata.copy()

    def _validate_file(self, file_path: Path) -> None:
        """
        Validate that file exists and is readable.

        Args:
            file_path: Path to validate.

        Raises:
            FileNotFoundError: If file doesn't exist.
            PermissionError: If file is not readable.
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if not file_path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")

    def _detect_encoding(self, file_path: Path) -> str:
        """
        Detect file encoding for text files.

        Args:
            file_path: Path to the file.

        Returns:
            Detected encoding string.
        """
        try:
            import chardet

            with open(file_path, "rb") as f:
                raw_data = f.read(10000)
                result = chardet.detect(raw_data)
                return result.get("encoding", "utf-8")
        except ImportError:
            return "utf-8"
        except Exception:
            return "utf-8"
