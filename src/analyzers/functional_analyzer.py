"""
Functional test analyzer.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pandas as pd


@dataclass
class FunctionalTestResult:
    """Result of a functional test analysis."""

    test_name: str
    passed: bool
    details: Dict[str, Any]
    message: Optional[str] = None


class FunctionalAnalyzer:
    """
    Analyzer for functional tests.

    Supports:
    - Signal value range checks
    - Signal state transition validation
    - Signal timing relationship verification
    - Logic consistency checks
    """

    def __init__(self):
        """Initialize functional analyzer."""
        self._results: List[FunctionalTestResult] = []

    def check_value_range(
        self,
        data: pd.DataFrame,
        signal_name: str,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        test_name: Optional[str] = None,
    ) -> FunctionalTestResult:
        """
        Check if signal values are within specified range.

        Args:
            data: DataFrame containing signal data.
            signal_name: Name of the signal to check.
            min_value: Minimum allowed value (None for no limit).
            max_value: Maximum allowed value (None for no limit).
            test_name: Optional test name.

        Returns:
            FunctionalTestResult with pass/fail status.
        """
        if signal_name not in data.columns:
            return FunctionalTestResult(
                test_name=test_name or f"range_check_{signal_name}",
                passed=False,
                details={},
                message=f"Signal '{signal_name}' not found in data",
            )

        signal_data = data[signal_name].dropna()
        violations = []

        if min_value is not None:
            below_min = signal_data[signal_data < min_value]
            if len(below_min) > 0:
                violations.append(
                    f"{len(below_min)} values below minimum {min_value}"
                )

        if max_value is not None:
            above_max = signal_data[signal_data > max_value]
            if len(above_max) > 0:
                violations.append(
                    f"{len(above_max)} values above maximum {max_value}"
                )

        passed = len(violations) == 0
        message = "; ".join(violations) if violations else "All values within range"

        result = FunctionalTestResult(
            test_name=test_name or f"range_check_{signal_name}",
            passed=passed,
            details={
                "signal": signal_name,
                "min_value": min_value,
                "max_value": max_value,
                "actual_min": float(signal_data.min()),
                "actual_max": float(signal_data.max()),
                "data_points": len(signal_data),
            },
            message=message,
        )

        self._results.append(result)
        return result

    def check_state_transition(
        self,
        data: pd.DataFrame,
        signal_name: str,
        expected_states: List[Any],
        test_name: Optional[str] = None,
    ) -> FunctionalTestResult:
        """
        Check if signal transitions through expected states.

        Args:
            data: DataFrame containing signal data.
            signal_name: Name of the signal to check.
            expected_states: List of expected state values in order.
            test_name: Optional test name.

        Returns:
            FunctionalTestResult with pass/fail status.
        """
        if signal_name not in data.columns:
            return FunctionalTestResult(
                test_name=test_name or f"state_transition_{signal_name}",
                passed=False,
                details={},
                message=f"Signal '{signal_name}' not found in data",
            )

        signal_data = data[signal_name].dropna()

        # Find actual transitions
        actual_states = []
        prev_value = None
        for value in signal_data:
            if value != prev_value:
                actual_states.append(value)
                prev_value = value

        # Check if expected states appear in order
        expected_idx = 0
        for state in actual_states:
            if expected_idx < len(expected_states) and state == expected_states[expected_idx]:
                expected_idx += 1

        passed = expected_idx == len(expected_states)

        result = FunctionalTestResult(
            test_name=test_name or f"state_transition_{signal_name}",
            passed=passed,
            details={
                "signal": signal_name,
                "expected_states": expected_states,
                "actual_states": actual_states,
            },
            message="All expected states found in order"
            if passed
            else f"Only {expected_idx}/{len(expected_states)} expected states found",
        )

        self._results.append(result)
        return result

    def get_results(self) -> List[FunctionalTestResult]:
        """Get all test results."""
        return self._results.copy()

    def clear_results(self) -> None:
        """Clear all test results."""
        self._results.clear()
