"""
Performance test analyzer.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from scipy import stats


@dataclass
class PerformanceTestResult:
    """Result of a performance test analysis."""

    test_name: str
    metric_name: str
    metric_value: float
    unit: Optional[str]
    passed: bool
    details: Dict[str, Any]
    message: Optional[str] = None


class PerformanceAnalyzer:
    """
    Analyzer for performance tests.

    Supports:
    - Response time analysis
    - Statistical distribution calculation
    - Trend analysis
    - Performance bottleneck identification
    """

    def __init__(self):
        """Initialize performance analyzer."""
        self._results: List[PerformanceTestResult] = []

    def analyze_response_time(
        self,
        data: pd.DataFrame,
        time_column: str,
        signal_name: str,
        threshold_percent: float = 90.0,
        target_value: Optional[float] = None,
        test_name: Optional[str] = None,
    ) -> PerformanceTestResult:
        """
        Analyze response time of a signal.

        Args:
            data: DataFrame containing signal data.
            time_column: Name of the time column.
            signal_name: Name of the signal to analyze.
            threshold_percent: Percentage of target to measure response time.
            target_value: Target value (auto-detected if None).
            test_name: Optional test name.

        Returns:
            PerformanceTestResult with response time analysis.
        """
        if signal_name not in data.columns or time_column not in data.columns:
            return PerformanceTestResult(
                test_name=test_name or f"response_time_{signal_name}",
                metric_name="response_time",
                metric_value=0.0,
                unit="s",
                passed=False,
                details={},
                message="Required columns not found",
            )

        time_data = data[time_column].values
        signal_data = data[signal_name].values

        # Auto-detect target value
        if target_value is None:
            target_value = float(np.max(signal_data))

        # Calculate threshold
        initial_value = float(signal_data[0])
        threshold = initial_value + (target_value - initial_value) * (
            threshold_percent / 100.0
        )

        # Find response time
        response_time = None
        for i, (t, v) in enumerate(zip(time_data, signal_data)):
            if v >= threshold:
                response_time = float(t - time_data[0])
                break

        if response_time is None:
            response_time = float(time_data[-1] - time_data[0])

        result = PerformanceTestResult(
            test_name=test_name or f"response_time_{signal_name}",
            metric_name="response_time",
            metric_value=response_time,
            unit="s",
            passed=True,  # No pass/fail criteria defined
            details={
                "signal": signal_name,
                "target_value": target_value,
                "threshold_percent": threshold_percent,
                "threshold_value": threshold,
            },
        )

        self._results.append(result)
        return result

    def calculate_statistics(
        self,
        data: pd.DataFrame,
        signal_name: str,
        test_name: Optional[str] = None,
    ) -> PerformanceTestResult:
        """
        Calculate statistical metrics for a signal.

        Args:
            data: DataFrame containing signal data.
            signal_name: Name of the signal to analyze.
            test_name: Optional test name.

        Returns:
            PerformanceTestResult with statistical analysis.
        """
        if signal_name not in data.columns:
            return PerformanceTestResult(
                test_name=test_name or f"statistics_{signal_name}",
                metric_name="statistics",
                metric_value=0.0,
                unit=None,
                passed=False,
                details={},
                message=f"Signal '{signal_name}' not found",
            )

        signal_data = data[signal_name].dropna().values

        stats_dict = {
            "mean": float(np.mean(signal_data)),
            "std": float(np.std(signal_data)),
            "min": float(np.min(signal_data)),
            "max": float(np.max(signal_data)),
            "median": float(np.median(signal_data)),
            "p5": float(np.percentile(signal_data, 5)),
            "p95": float(np.percentile(signal_data, 95)),
            "count": len(signal_data),
        }

        result = PerformanceTestResult(
            test_name=test_name or f"statistics_{signal_name}",
            metric_name="statistics",
            metric_value=stats_dict["mean"],
            unit=None,
            passed=True,
            details=stats_dict,
        )

        self._results.append(result)
        return result

    def analyze_trend(
        self,
        data: pd.DataFrame,
        time_column: str,
        signal_name: str,
        test_name: Optional[str] = None,
    ) -> PerformanceTestResult:
        """
        Analyze trend of a signal over time.

        Args:
            data: DataFrame containing signal data.
            time_column: Name of the time column.
            signal_name: Name of the signal to analyze.
            test_name: Optional test name.

        Returns:
            PerformanceTestResult with trend analysis.
        """
        if signal_name not in data.columns or time_column not in data.columns:
            return PerformanceTestResult(
                test_name=test_name or f"trend_{signal_name}",
                metric_name="trend_slope",
                metric_value=0.0,
                unit=None,
                passed=False,
                details={},
                message="Required columns not found",
            )

        time_data = data[time_column].values
        signal_data = data[signal_name].values

        # Linear regression for trend
        slope, intercept, r_value, p_value, std_err = stats.linregress(
            time_data, signal_data
        )

        trend_direction = (
            "increasing"
            if slope > 0
            else "decreasing"
            if slope < 0
            else "stable"
        )

        result = PerformanceTestResult(
            test_name=test_name or f"trend_{signal_name}",
            metric_name="trend_slope",
            metric_value=float(slope),
            unit="units/s",
            passed=True,
            details={
                "signal": signal_name,
                "slope": float(slope),
                "intercept": float(intercept),
                "r_squared": float(r_value**2),
                "p_value": float(p_value),
                "trend_direction": trend_direction,
            },
        )

        self._results.append(result)
        return result

    def get_results(self) -> List[PerformanceTestResult]:
        """Get all test results."""
        return self._results.copy()

    def clear_results(self) -> None:
        """Clear all test results."""
        self._results.clear()
