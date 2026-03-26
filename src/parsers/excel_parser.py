# -*- coding: utf-8 -*-
"""
Excel test case parser.

Parses test cases from Excel files (.xlsx, .xls) and extracts
test case definitions, indicators, and judgment criteria.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd


@dataclass
class ParsedTestCase:
    """Parsed test case from Excel."""
    case_id: str
    name: str
    description: Optional[str] = None
    test_type: str = "functional"
    priority: str = "P2"
    preconditions: Optional[str] = None
    test_steps: Optional[str] = None
    expected_result: Optional[str] = None
    indicators: List[Dict[str, Any]] = field(default_factory=list)
    row_number: int = 0


@dataclass
class ParsedIndicator:
    """Parsed indicator from Excel."""
    name: str
    signal_name: Optional[str] = None
    indicator_type: str = "single_value"
    formula: Optional[str] = None
    unit: Optional[str] = None
    lower_limit: Optional[float] = None
    upper_limit: Optional[float] = None
    target_value: Optional[float] = None
    tolerance: Optional[float] = None
    description: Optional[str] = None


class ExcelTestCaseParser:
    """
    Parser for Excel test case files.

    Supports multiple Excel formats and configurable column mappings.
    """

    DEFAULT_COLUMN_MAPPINGS = {
        "case_id": ["case_id", "用例编号", "编号", "ID", "TestCase ID"],
        "name": ["name", "用例名称", "名称", "标题", "TestCase Name"],
        "description": ["description", "描述", "用例描述", "说明"],
        "test_type": ["test_type", "测试类型", "类型", "Type"],
        "priority": ["priority", "优先级", "级别", "Priority"],
        "preconditions": ["preconditions", "前置条件", "前提", "Preconditions"],
        "test_steps": ["test_steps", "测试步骤", "步骤", "Steps"],
        "expected_result": ["expected_result", "预期结果", "期望结果", "Expected"],
        "signal_name": ["signal", "信号", "信号名", "Signal"],
        "indicator_name": ["indicator", "指标", "指标名", "Indicator"],
        "unit": ["unit", "单位", "Unit"],
        "lower_limit": ["lower", "下限", "最小值", "Lower Limit"],
        "upper_limit": ["upper", "上限", "最大值", "Upper Limit"],
        "target": ["target", "目标值", "Target"],
        "tolerance": ["tolerance", "容差", "公差", "Tolerance"],
    }

    def __init__(
        self,
        file_path: Optional[Path] = None,
        sheet_name: Optional[str] = None,
        column_mappings: Optional[Dict[str, List[str]]] = None,
        header_row: int = 0,
    ):
        """
        Initialize Excel parser.

        Args:
            file_path: Path to Excel file.
            sheet_name: Sheet name to parse (first sheet if None).
            column_mappings: Custom column name mappings.
            header_row: Row number containing headers (0-indexed).
        """
        self.file_path = Path(file_path) if file_path else None
        self.sheet_name = sheet_name
        self.column_mappings = column_mappings or self.DEFAULT_COLUMN_MAPPINGS
        self.header_row = header_row
        self._data: Optional[pd.DataFrame] = None
        self._test_cases: List[ParsedTestCase] = []
        self._column_indices: Dict[str, int] = {}

    def parse(self, file_path: Optional[Path] = None) -> List[ParsedTestCase]:
        """
        Parse Excel file and extract test cases.

        Args:
            file_path: Optional path override.

        Returns:
            List of ParsedTestCase objects.
        """
        path = Path(file_path) if file_path else self.file_path
        if not path or not path.exists():
            return []

        try:
            if self.sheet_name:
                self._data = pd.read_excel(path, sheet_name=self.sheet_name, header=self.header_row)
            else:
                self._data = pd.read_excel(path, header=self.header_row)

            if self._data is None or self._data.empty:
                return []

            self._map_columns()
            self._test_cases = self._extract_test_cases()

            return self._test_cases

        except Exception:
            return []

    def _map_columns(self) -> None:
        """Map column names to standardized names."""
        self._column_indices = {}

        if self._data is None:
            return

        columns = list(self._data.columns)

        for standard_name, possible_names in self.column_mappings.items():
            for col_idx, col_name in enumerate(columns):
                col_str = str(col_name).strip()
                if col_str in possible_names or col_str.lower() in [n.lower() for n in possible_names]:
                    self._column_indices[standard_name] = col_idx
                    break

    def _extract_test_cases(self) -> List[ParsedTestCase]:
        """Extract test cases from parsed data."""
        test_cases = []

        if self._data is None:
            return test_cases

        for idx, row in self._data.iterrows():
            test_case = self._parse_row(row, idx + 1)
            if test_case:
                test_cases.append(test_case)

        return test_cases

    def _parse_row(self, row: pd.Series, row_number: int) -> Optional[ParsedTestCase]:
        """Parse a single row into a test case."""
        case_id = self._get_value(row, "case_id")
        name = self._get_value(row, "name")

        if not case_id or not name:
            return None

        test_case = ParsedTestCase(
            case_id=str(case_id),
            name=str(name),
            description=self._get_value(row, "description"),
            test_type=self._get_value(row, "test_type") or "functional",
            priority=self._get_value(row, "priority") or "P2",
            preconditions=self._get_value(row, "preconditions"),
            test_steps=self._get_value(row, "test_steps"),
            expected_result=self._get_value(row, "expected_result"),
            row_number=row_number,
        )

        indicator = self._parse_indicator(row)
        if indicator:
            test_case.indicators.append({
                "name": indicator.name,
                "signal_name": indicator.signal_name,
                "indicator_type": indicator.indicator_type,
                "formula": indicator.formula,
                "unit": indicator.unit,
                "lower_limit": indicator.lower_limit,
                "upper_limit": indicator.upper_limit,
                "target_value": indicator.target_value,
                "tolerance": indicator.tolerance,
                "description": indicator.description,
            })

        return test_case

    def _parse_indicator(self, row: pd.Series) -> Optional[ParsedIndicator]:
        """Parse indicator information from row."""
        indicator_name = self._get_value(row, "indicator_name")
        signal_name = self._get_value(row, "signal_name")

        if not indicator_name and not signal_name:
            return None

        lower = self._get_numeric_value(row, "lower_limit")
        upper = self._get_numeric_value(row, "upper_limit")
        target = self._get_numeric_value(row, "target")
        tolerance = self._get_numeric_value(row, "tolerance")

        return ParsedIndicator(
            name=indicator_name or signal_name or "Unknown",
            signal_name=signal_name,
            indicator_type="single_value",
            unit=self._get_value(row, "unit"),
            lower_limit=lower,
            upper_limit=upper,
            target_value=target,
            tolerance=tolerance,
            description=None,
        )

    def _get_value(self, row: pd.Series, key: str) -> Optional[str]:
        """Get string value from row by mapped column name."""
        if key not in self._column_indices:
            return None

        col_idx = self._column_indices[key]
        if col_idx >= len(row):
            return None

        value = row.iloc[col_idx]

        if pd.isna(value):
            return None

        return str(value).strip()

    def _get_numeric_value(self, row: pd.Series, key: str) -> Optional[float]:
        """Get numeric value from row by mapped column name."""
        if key not in self._column_indices:
            return None

        col_idx = self._column_indices[key]
        if col_idx >= len(row):
            return None

        value = row.iloc[col_idx]

        if pd.isna(value):
            return None

        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def get_sheet_names(self) -> List[str]:
        """Get list of sheet names in the Excel file."""
        if not self.file_path or not self.file_path.exists():
            return []

        try:
            xl = pd.ExcelFile(self.file_path)
            return xl.sheet_names
        except Exception:
            return []

    def get_test_cases(self) -> List[ParsedTestCase]:
        """Get parsed test cases."""
        return self._test_cases

    def get_summary(self) -> Dict[str, Any]:
        """Get parsing summary."""
        return {
            "total_test_cases": len(self._test_cases),
            "test_cases_with_indicators": sum(1 for tc in self._test_cases if tc.indicators),
            "test_types": list(set(tc.test_type for tc in self._test_cases)),
            "priorities": list(set(tc.priority for tc in self._test_cases)),
        }
