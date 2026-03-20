"""Unit tests for analyzer modules."""

import numpy as np
import pandas as pd
import pytest

from src.analyzers.functional_analyzer import (
    FunctionalAnalyzer,
    FunctionalTestResult,
)
from src.analyzers.performance_analyzer import (
    PerformanceAnalyzer,
    PerformanceTestResult,
)


class TestFunctionalAnalyzer:
    """Tests for FunctionalAnalyzer class."""

    def test_init(self):
        """Test initialization."""
        analyzer = FunctionalAnalyzer()
        assert len(analyzer.get_results()) == 0

    def test_check_value_range_pass(self):
        """Test value range check that passes."""
        analyzer = FunctionalAnalyzer()
        data = pd.DataFrame(
            {
                "signal": [1.0, 2.0, 3.0, 4.0, 5.0],
            }
        )
        result = analyzer.check_value_range(
            data, "signal", min_value=0.0, max_value=10.0
        )

        assert result.passed
        assert result.details["actual_min"] == 1.0
        assert result.details["actual_max"] == 5.0

    def test_check_value_range_fail_below_min(self):
        """Test value range check that fails (below min)."""
        analyzer = FunctionalAnalyzer()
        data = pd.DataFrame(
            {
                "signal": [0.5, 1.0, 2.0, 3.0],
            }
        )
        result = analyzer.check_value_range(
            data, "signal", min_value=1.0, max_value=10.0
        )

        assert not result.passed
        assert "below minimum" in result.message

    def test_check_value_range_fail_above_max(self):
        """Test value range check that fails (above max)."""
        analyzer = FunctionalAnalyzer()
        data = pd.DataFrame(
            {
                "signal": [5.0, 10.0, 15.0],
            }
        )
        result = analyzer.check_value_range(
            data, "signal", min_value=0.0, max_value=10.0
        )

        assert not result.passed
        assert "above maximum" in result.message

    def test_check_value_range_missing_signal(self):
        """Test value range check with missing signal."""
        analyzer = FunctionalAnalyzer()
        data = pd.DataFrame({"other_signal": [1.0, 2.0, 3.0]})
        result = analyzer.check_value_range(
            data, "signal", min_value=0.0, max_value=10.0
        )

        assert not result.passed
        assert "not found" in result.message

    def test_check_value_range_no_limits(self):
        """Test value range check with no limits."""
        analyzer = FunctionalAnalyzer()
        data = pd.DataFrame({"signal": [1.0, 2.0, 3.0]})
        result = analyzer.check_value_range(data, "signal")

        assert result.passed

    def test_check_value_range_only_min(self):
        """Test value range check with only min limit."""
        analyzer = FunctionalAnalyzer()
        data = pd.DataFrame({"signal": [5.0, 6.0, 7.0]})
        result = analyzer.check_value_range(data, "signal", min_value=0.0)

        assert result.passed

    def test_check_value_range_only_max(self):
        """Test value range check with only max limit."""
        analyzer = FunctionalAnalyzer()
        data = pd.DataFrame({"signal": [5.0, 6.0, 7.0]})
        result = analyzer.check_value_range(data, "signal", max_value=10.0)

        assert result.passed

    def test_check_state_transition_pass(self):
        """Test state transition check that passes."""
        analyzer = FunctionalAnalyzer()
        data = pd.DataFrame(
            {
                "state": [0, 0, 1, 1, 2, 2, 3, 3],
            }
        )
        result = analyzer.check_state_transition(
            data, "state", expected_states=[0, 1, 2, 3]
        )

        assert result.passed
        assert result.details["expected_states"] == [0, 1, 2, 3]

    def test_check_state_transition_fail(self):
        """Test state transition check that fails."""
        analyzer = FunctionalAnalyzer()
        data = pd.DataFrame(
            {
                "state": [0, 0, 2, 2, 3, 3],  # Missing state 1
            }
        )
        result = analyzer.check_state_transition(
            data, "state", expected_states=[0, 1, 2, 3]
        )

        assert not result.passed

    def test_check_state_transition_missing_signal(self):
        """Test state transition check with missing signal."""
        analyzer = FunctionalAnalyzer()
        data = pd.DataFrame({"other": [1, 2, 3]})
        result = analyzer.check_state_transition(
            data, "state", expected_states=[0, 1, 2]
        )

        assert not result.passed
        assert "not found" in result.message

    def test_get_results(self):
        """Test getting results."""
        analyzer = FunctionalAnalyzer()
        data = pd.DataFrame({"signal": [1.0, 2.0, 3.0]})

        analyzer.check_value_range(data, "signal", min_value=0.0)
        analyzer.check_value_range(data, "signal", max_value=10.0)

        results = analyzer.get_results()
        assert len(results) == 2

    def test_clear_results(self):
        """Test clearing results."""
        analyzer = FunctionalAnalyzer()
        data = pd.DataFrame({"signal": [1.0, 2.0, 3.0]})

        analyzer.check_value_range(data, "signal")
        assert len(analyzer.get_results()) == 1

        analyzer.clear_results()
        assert len(analyzer.get_results()) == 0

    def test_custom_test_name(self):
        """Test custom test name."""
        analyzer = FunctionalAnalyzer()
        data = pd.DataFrame({"signal": [1.0, 2.0, 3.0]})
        result = analyzer.check_value_range(
            data, "signal", test_name="custom_test_name"
        )

        assert result.test_name == "custom_test_name"


class TestPerformanceAnalyzer:
    """Tests for PerformanceAnalyzer class."""

    def test_init(self):
        """Test initialization."""
        analyzer = PerformanceAnalyzer()
        assert len(analyzer.get_results()) == 0

    def test_analyze_response_time(self):
        """Test response time analysis."""
        analyzer = PerformanceAnalyzer()
        data = pd.DataFrame(
            {
                "time": [0.0, 0.1, 0.2, 0.3, 0.4, 0.5],
                "signal": [0.0, 20.0, 40.0, 60.0, 80.0, 100.0],
            }
        )
        result = analyzer.analyze_response_time(
            data, "time", "signal", threshold_percent=90.0, target_value=100.0
        )

        assert result.passed
        assert result.metric_name == "response_time"
        assert result.unit == "s"
        assert result.metric_value > 0

    def test_analyze_response_time_missing_columns(self):
        """Test response time analysis with missing columns."""
        analyzer = PerformanceAnalyzer()
        data = pd.DataFrame({"other": [1.0, 2.0, 3.0]})
        result = analyzer.analyze_response_time(data, "time", "signal")

        assert not result.passed
        assert "not found" in result.message

    def test_analyze_response_time_auto_target(self):
        """Test response time analysis with auto-detected target."""
        analyzer = PerformanceAnalyzer()
        data = pd.DataFrame(
            {
                "time": [0.0, 0.05, 0.1, 0.15, 0.2],
                "signal": [0.0, 25.0, 50.0, 75.0, 100.0],
            }
        )
        result = analyzer.analyze_response_time(
            data, "time", "signal", threshold_percent=50.0
        )

        assert result.passed
        assert "target_value" in result.details

    def test_calculate_statistics(self):
        """Test statistical calculation."""
        analyzer = PerformanceAnalyzer()
        data = pd.DataFrame(
            {
                "signal": [1.0, 2.0, 3.0, 4.0, 5.0],
            }
        )
        result = analyzer.calculate_statistics(data, "signal")

        assert result.passed
        assert result.details["mean"] == 3.0
        assert result.details["min"] == 1.0
        assert result.details["max"] == 5.0
        assert result.details["count"] == 5

    def test_calculate_statistics_missing_signal(self):
        """Test statistical calculation with missing signal."""
        analyzer = PerformanceAnalyzer()
        data = pd.DataFrame({"other": [1.0, 2.0, 3.0]})
        result = analyzer.calculate_statistics(data, "signal")

        assert not result.passed
        assert "not found" in result.message

    def test_analyze_trend_increasing(self):
        """Test trend analysis for increasing signal."""
        analyzer = PerformanceAnalyzer()
        data = pd.DataFrame(
            {
                "time": [0.0, 1.0, 2.0, 3.0, 4.0],
                "signal": [0.0, 1.0, 2.0, 3.0, 4.0],
            }
        )
        result = analyzer.analyze_trend(data, "time", "signal")

        assert result.passed
        assert result.details["trend_direction"] == "increasing"
        assert result.metric_value > 0

    def test_analyze_trend_decreasing(self):
        """Test trend analysis for decreasing signal."""
        analyzer = PerformanceAnalyzer()
        data = pd.DataFrame(
            {
                "time": [0.0, 1.0, 2.0, 3.0, 4.0],
                "signal": [4.0, 3.0, 2.0, 1.0, 0.0],
            }
        )
        result = analyzer.analyze_trend(data, "time", "signal")

        assert result.passed
        assert result.details["trend_direction"] == "decreasing"
        assert result.metric_value < 0

    def test_analyze_trend_stable(self):
        """Test trend analysis for stable signal."""
        analyzer = PerformanceAnalyzer()
        data = pd.DataFrame(
            {
                "time": [0.0, 1.0, 2.0, 3.0, 4.0],
                "signal": [5.0, 5.0, 5.0, 5.0, 5.0],
            }
        )
        result = analyzer.analyze_trend(data, "time", "signal")

        assert result.passed
        assert result.details["trend_direction"] == "stable"
        assert abs(result.metric_value) < 0.001

    def test_analyze_trend_missing_columns(self):
        """Test trend analysis with missing columns."""
        analyzer = PerformanceAnalyzer()
        data = pd.DataFrame({"other": [1.0, 2.0, 3.0]})
        result = analyzer.analyze_trend(data, "time", "signal")

        assert not result.passed
        assert "not found" in result.message

    def test_get_results(self):
        """Test getting results."""
        analyzer = PerformanceAnalyzer()
        data = pd.DataFrame(
            {
                "time": [0.0, 1.0, 2.0],
                "signal": [0.0, 1.0, 2.0],
            }
        )

        analyzer.analyze_response_time(data, "time", "signal")
        analyzer.calculate_statistics(data, "signal")

        results = analyzer.get_results()
        assert len(results) == 2

    def test_clear_results(self):
        """Test clearing results."""
        analyzer = PerformanceAnalyzer()
        data = pd.DataFrame({"signal": [1.0, 2.0, 3.0]})

        analyzer.calculate_statistics(data, "signal")
        assert len(analyzer.get_results()) == 1

        analyzer.clear_results()
        assert len(analyzer.get_results()) == 0

    def test_custom_test_name(self):
        """Test custom test name."""
        analyzer = PerformanceAnalyzer()
        data = pd.DataFrame({"signal": [1.0, 2.0, 3.0]})
        result = analyzer.calculate_statistics(
            data, "signal", test_name="custom_stats"
        )

        assert result.test_name == "custom_stats"


class TestFunctionalTestResult:
    """Tests for FunctionalTestResult dataclass."""

    def test_create_result(self):
        """Test creating a test result."""
        result = FunctionalTestResult(
            test_name="test1",
            passed=True,
            details={"value": 1.0},
            message="Test passed",
        )
        assert result.test_name == "test1"
        assert result.passed
        assert result.details == {"value": 1.0}
        assert result.message == "Test passed"

    def test_result_defaults(self):
        """Test result default values."""
        result = FunctionalTestResult(
            test_name="test1",
            passed=True,
            details={},
        )
        assert result.message is None


class TestPerformanceTestResult:
    """Tests for PerformanceTestResult dataclass."""

    def test_create_result(self):
        """Test creating a test result."""
        result = PerformanceTestResult(
            test_name="test1",
            metric_name="response_time",
            metric_value=0.5,
            unit="s",
            passed=True,
            details={"threshold": 90.0},
            message="Good response",
        )
        assert result.test_name == "test1"
        assert result.metric_value == 0.5
        assert result.unit == "s"

    def test_result_defaults(self):
        """Test result default values."""
        result = PerformanceTestResult(
            test_name="test1",
            metric_name="metric",
            metric_value=1.0,
            unit=None,
            passed=True,
            details={},
        )
        assert result.message is None
