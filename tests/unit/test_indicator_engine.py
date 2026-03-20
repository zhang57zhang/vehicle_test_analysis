"""Unit tests for indicator engine module."""

import numpy as np
import pandas as pd
import pytest

from src.core.indicator_engine import (
    IndicatorDefinition,
    IndicatorEngine,
    IndicatorResult,
    IndicatorType,
    JudgmentResult,
)


class TestIndicatorDefinition:
    """Tests for IndicatorDefinition dataclass."""

    def test_create_single_value_definition(self):
        """Test creating single value indicator definition."""
        indicator = IndicatorDefinition(
            name="test_signal",
            indicator_type=IndicatorType.SINGLE_VALUE,
            signal_name="signal1",
        )
        assert indicator.name == "test_signal"
        assert indicator.indicator_type == IndicatorType.SINGLE_VALUE
        assert indicator.signal_name == "signal1"

    def test_create_statistical_definition(self):
        """Test creating statistical indicator definition."""
        indicator = IndicatorDefinition(
            name="mean_signal",
            indicator_type=IndicatorType.STATISTICAL,
            signal_name="signal1",
            formula="mean",
        )
        assert indicator.indicator_type == IndicatorType.STATISTICAL
        assert indicator.formula == "mean"

    def test_create_with_limits(self):
        """Test creating indicator with limits."""
        indicator = IndicatorDefinition(
            name="limited_signal",
            indicator_type=IndicatorType.SINGLE_VALUE,
            signal_name="signal1",
            lower_limit=0.0,
            upper_limit=100.0,
        )
        assert indicator.lower_limit == 0.0
        assert indicator.upper_limit == 100.0


class TestIndicatorEngine:
    """Tests for IndicatorEngine class."""

    @pytest.fixture
    def engine(self):
        """Create indicator engine instance."""
        return IndicatorEngine()

    @pytest.fixture
    def sample_data(self):
        """Create sample DataFrame."""
        return pd.DataFrame(
            {
                "time": [0.0, 0.1, 0.2, 0.3, 0.4, 0.5],
                "signal1": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
                "signal2": [10.0, 20.0, 30.0, 40.0, 50.0, 60.0],
            }
        )

    def test_engine_init(self, engine):
        """Test engine initialization."""
        assert engine is not None
        assert "mean" in engine._formula_functions

    def test_calculate_single_value_pass(self, engine, sample_data):
        """Test single value calculation that passes."""
        indicator = IndicatorDefinition(
            name="test",
            indicator_type=IndicatorType.SINGLE_VALUE,
            signal_name="signal1",
            lower_limit=0.0,
            upper_limit=10.0,
        )
        result = engine.calculate(indicator, sample_data)
        assert result.judgment == JudgmentResult.PASS
        assert result.calculated_value == 6.0  # Last value

    def test_calculate_single_value_fail_upper(self, engine, sample_data):
        """Test single value calculation that fails upper limit."""
        indicator = IndicatorDefinition(
            name="test",
            indicator_type=IndicatorType.SINGLE_VALUE,
            signal_name="signal1",
            upper_limit=5.0,
        )
        result = engine.calculate(indicator, sample_data)
        assert result.judgment == JudgmentResult.FAIL

    def test_calculate_single_value_fail_lower(self, engine, sample_data):
        """Test single value calculation that fails lower limit."""
        indicator = IndicatorDefinition(
            name="test",
            indicator_type=IndicatorType.SINGLE_VALUE,
            signal_name="signal1",
            lower_limit=10.0,
        )
        result = engine.calculate(indicator, sample_data)
        assert result.judgment == JudgmentResult.FAIL

    def test_calculate_single_value_missing_signal(self, engine, sample_data):
        """Test calculation with missing signal."""
        indicator = IndicatorDefinition(
            name="test",
            indicator_type=IndicatorType.SINGLE_VALUE,
            signal_name="nonexistent",
        )
        result = engine.calculate(indicator, sample_data)
        assert result.judgment == JudgmentResult.INCONCLUSIVE
        assert result.error_message is not None

    def test_calculate_statistical_mean(self, engine, sample_data):
        """Test statistical mean calculation."""
        indicator = IndicatorDefinition(
            name="mean_test",
            indicator_type=IndicatorType.STATISTICAL,
            signal_name="signal1",
            formula="mean",
        )
        result = engine.calculate(indicator, sample_data)
        assert result.judgment == JudgmentResult.PASS
        assert abs(result.calculated_value - 3.5) < 0.001

    def test_calculate_statistical_std(self, engine, sample_data):
        """Test statistical std calculation."""
        indicator = IndicatorDefinition(
            name="std_test",
            indicator_type=IndicatorType.STATISTICAL,
            signal_name="signal1",
            formula="std",
        )
        result = engine.calculate(indicator, sample_data)
        assert result.judgment == JudgmentResult.PASS
        assert result.calculated_value > 0

    def test_calculate_statistical_max(self, engine, sample_data):
        """Test statistical max calculation."""
        indicator = IndicatorDefinition(
            name="max_test",
            indicator_type=IndicatorType.STATISTICAL,
            signal_name="signal1",
            formula="max",
        )
        result = engine.calculate(indicator, sample_data)
        assert result.calculated_value == 6.0

    def test_calculate_statistical_min(self, engine, sample_data):
        """Test statistical min calculation."""
        indicator = IndicatorDefinition(
            name="min_test",
            indicator_type=IndicatorType.STATISTICAL,
            signal_name="signal1",
            formula="min",
        )
        result = engine.calculate(indicator, sample_data)
        assert result.calculated_value == 1.0

    def test_calculate_formula(self, engine, sample_data):
        """Test formula-based calculation."""
        indicator = IndicatorDefinition(
            name="formula_test",
            indicator_type=IndicatorType.CALCULATED,
            formula="signal1[-1] + signal2[-1]",
        )
        result = engine.calculate(indicator, sample_data)
        assert result.calculated_value == 66.0  # 6 + 60

    def test_calculate_with_target_value(self, engine, sample_data):
        """Test calculation with target value."""
        indicator = IndicatorDefinition(
            name="target_test",
            indicator_type=IndicatorType.SINGLE_VALUE,
            signal_name="signal1",
            target_value=6.0,
            tolerance=0.5,
        )
        result = engine.calculate(indicator, sample_data)
        assert result.judgment == JudgmentResult.PASS

    def test_calculate_with_target_value_fail(self, engine, sample_data):
        """Test calculation with target value that fails."""
        indicator = IndicatorDefinition(
            name="target_test",
            indicator_type=IndicatorType.SINGLE_VALUE,
            signal_name="signal1",
            target_value=5.0,
            tolerance=0.5,
        )
        result = engine.calculate(indicator, sample_data)
        assert result.judgment == JudgmentResult.FAIL

    def test_calculate_empty_data(self, engine):
        """Test calculation with empty data."""
        indicator = IndicatorDefinition(
            name="test",
            indicator_type=IndicatorType.SINGLE_VALUE,
            signal_name="signal1",
        )
        result = engine.calculate(indicator, pd.DataFrame())
        assert result.judgment == JudgmentResult.INCONCLUSIVE

    def test_register_custom_function(self, engine, sample_data):
        """Test registering custom formula function."""
        engine.register_formula_function("double", lambda x: x * 2)

        indicator = IndicatorDefinition(
            name="custom_test",
            indicator_type=IndicatorType.STATISTICAL,
            signal_name="signal1",
            formula="double",
        )
        result = engine.calculate(indicator, sample_data)
        # double of mean(3.5) = 7.0
        assert abs(result.calculated_value - 7.0) < 0.001

    def test_time_domain_response_time(self, engine):
        """Test time domain response time calculation."""
        data = pd.DataFrame(
            {
                "time": np.linspace(0, 1, 100),
                "signal": np.concatenate(
                    [np.zeros(30), np.linspace(0, 10, 70)]
                ),
            }
        )
        indicator = IndicatorDefinition(
            name="response_time",
            indicator_type=IndicatorType.TIME_DOMAIN,
            signal_name="signal",
            formula="response_time",
        )
        result = engine.calculate(indicator, data)
        assert result.calculation_details is not None
        assert "metric" in result.calculation_details

    def test_time_domain_overshoot(self, engine):
        """Test time domain overshoot calculation."""
        # Create signal with overshoot
        t = np.linspace(0, 1, 100)
        signal = 10 * (1 - np.exp(-5 * t)) * (1 + 0.2 * np.sin(10 * t))
        data = pd.DataFrame({"time": t, "signal": signal})

        indicator = IndicatorDefinition(
            name="overshoot",
            indicator_type=IndicatorType.TIME_DOMAIN,
            signal_name="signal",
            formula="overshoot",
            target_value=10.0,
        )
        result = engine.calculate(indicator, data)
        assert result.calculation_details is not None


class TestJudgmentResult:
    """Tests for judgment result enum."""

    def test_judgment_values(self):
        """Test judgment result enum values."""
        assert JudgmentResult.PASS.value == "pass"
        assert JudgmentResult.FAIL.value == "fail"
        assert JudgmentResult.INCONCLUSIVE.value == "inconclusive"
        assert JudgmentResult.NOT_RUN.value == "not_run"


class TestIndicatorType:
    """Tests for indicator type enum."""

    def test_type_values(self):
        """Test indicator type enum values."""
        assert IndicatorType.SINGLE_VALUE.value == "single_value"
        assert IndicatorType.CALCULATED.value == "calculated"
        assert IndicatorType.TIME_DOMAIN.value == "time_domain"
        assert IndicatorType.STATISTICAL.value == "statistical"


class TestMissingCoverage:
    """Tests to cover missing branches and edge cases."""

    @pytest.fixture
    def engine(self):
        """Create indicator engine instance."""
        return IndicatorEngine()

    @pytest.fixture
    def sample_data(self):
        """Create sample DataFrame."""
        return pd.DataFrame(
            {
                "time": [0.0, 0.1, 0.2, 0.3, 0.4, 0.5],
                "signal1": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
                "signal2": [10.0, 20.0, 30.0, 40.0, 50.0, 60.0],
            }
        )

    # Lines 111-119: Unknown indicator type and exception handling in calculate()
    def test_unknown_indicator_type(self, engine, sample_data):
        """Test calculation with unknown indicator type."""
        # Create a mock indicator with invalid type
        indicator = IndicatorDefinition(
            name="test",
            indicator_type="invalid_type",  # type: ignore
            signal_name="signal1",
        )
        result = engine.calculate(indicator, sample_data)
        assert result.judgment == JudgmentResult.INCONCLUSIVE
        assert "Unknown indicator type" in result.error_message

    def test_calculate_exception_handling(self, engine):
        """Test exception handling in calculate method."""
        # Create data that will cause an exception
        data = pd.DataFrame({"time": [0.0, 0.1], "signal1": [1.0, None]})
        
        # Force an exception by using a formula that will fail
        indicator = IndicatorDefinition(
            name="test",
            indicator_type=IndicatorType.CALCULATED,
            formula="1/0",  # Division by zero
        )
        result = engine.calculate(indicator, data)
        assert result.judgment == JudgmentResult.INCONCLUSIVE
        assert result.error_message is not None

    def test_calculate_exception_none_data(self, engine):
        """Test exception handling when data is None."""
        indicator = IndicatorDefinition(
            name="test",
            indicator_type=IndicatorType.SINGLE_VALUE,
            signal_name="signal1",
        )
        result = engine.calculate(indicator, None)  # type: ignore
        assert result.judgment == JudgmentResult.INCONCLUSIVE
        assert result.error_message is not None

    # Line 145: Single value with empty signal data
    def test_single_value_empty_signal_data(self, engine):
        """Test single value calculation with empty signal data."""
        data = pd.DataFrame({
            "time": [0.0, 0.1, 0.2],
            "signal1": [np.nan, np.nan, np.nan],
        })
        indicator = IndicatorDefinition(
            name="test",
            indicator_type=IndicatorType.SINGLE_VALUE,
            signal_name="signal1",
        )
        result = engine.calculate(indicator, data)
        assert result.judgment == JudgmentResult.INCONCLUSIVE
        assert "No valid data points" in result.error_message

    # Line 145: Statistical with empty signal data
    def test_statistical_empty_signal_data(self, engine):
        """Test statistical calculation with empty signal data."""
        data = pd.DataFrame({
            "time": [0.0, 0.1, 0.2],
            "signal1": [np.nan, np.nan, np.nan],
        })
        indicator = IndicatorDefinition(
            name="test",
            indicator_type=IndicatorType.STATISTICAL,
            signal_name="signal1",
            formula="mean",
        )
        result = engine.calculate(indicator, data)
        assert result.judgment == JudgmentResult.INCONCLUSIVE
        assert "No valid data points" in result.error_message

    # Line 179: Statistical with function that returns array (diff, gradient)
    def test_statistical_diff_function(self, engine, sample_data):
        """Test statistical calculation with diff function (returns array)."""
        indicator = IndicatorDefinition(
            name="diff_test",
            indicator_type=IndicatorType.STATISTICAL,
            signal_name="signal1",
            formula="diff",
        )
        result = engine.calculate(indicator, sample_data)
        # diff returns array of size n-1, mean is taken
        assert result.judgment == JudgmentResult.PASS
        assert result.calculated_value is not None

    def test_statistical_gradient_function(self, engine, sample_data):
        """Test statistical calculation with gradient function (returns array)."""
        indicator = IndicatorDefinition(
            name="gradient_test",
            indicator_type=IndicatorType.STATISTICAL,
            signal_name="signal1",
            formula="gradient",
        )
        result = engine.calculate(indicator, sample_data)
        # gradient returns array of same size, mean is taken
        assert result.judgment == JudgmentResult.PASS
        assert result.calculated_value is not None

    # Line 189: Statistical with unknown formula (falls back to mean)
    def test_statistical_unknown_formula(self, engine, sample_data):
        """Test statistical calculation with unknown formula."""
        indicator = IndicatorDefinition(
            name="unknown_formula_test",
            indicator_type=IndicatorType.STATISTICAL,
            signal_name="signal1",
            formula="unknown_function",
        )
        result = engine.calculate(indicator, sample_data)
        # Falls back to mean
        assert result.judgment == JudgmentResult.PASS
        assert abs(result.calculated_value - 3.5) < 0.001

    # Line 211: Statistical with function that throws exception
    def test_statistical_function_exception(self, engine, sample_data):
        """Test statistical calculation when function throws exception."""
        # Register a function that will raise an exception
        def bad_func(x):
            raise ValueError("Test error")
        
        engine.register_formula_function("bad_func", bad_func)
        
        indicator = IndicatorDefinition(
            name="bad_func_test",
            indicator_type=IndicatorType.STATISTICAL,
            signal_name="signal1",
            formula="bad_func",
        )
        result = engine.calculate(indicator, sample_data)
        # Falls back to base_value (mean)
        assert result.judgment == JudgmentResult.PASS
        assert abs(result.calculated_value - 3.5) < 0.001

    # Line 216, 219-222: Statistical with array-returning function edge cases
    def test_statistical_array_single_element(self, engine, sample_data):
        """Test statistical with function returning single-element array."""
        # Register a function that returns single-element array
        def single_elem_func(x):
            return np.array([42.0])
        
        engine.register_formula_function("single_elem", single_elem_func)
        
        indicator = IndicatorDefinition(
            name="single_elem_test",
            indicator_type=IndicatorType.STATISTICAL,
            signal_name="signal1",
            formula="single_elem",
        )
        result = engine.calculate(indicator, sample_data)
        assert result.calculated_value == 42.0

    def test_statistical_array_wrong_size(self, engine, sample_data):
        """Test statistical with function returning array of wrong size."""
        # Register a function that returns array of different size
        def wrong_size_func(x):
            return np.array([1.0, 2.0])  # Size 2, not matching signal size
        
        engine.register_formula_function("wrong_size", wrong_size_func)
        
        indicator = IndicatorDefinition(
            name="wrong_size_test",
            indicator_type=IndicatorType.STATISTICAL,
            signal_name="signal1",
            formula="wrong_size",
        )
        result = engine.calculate(indicator, sample_data)
        # Falls back to base_value (mean)
        assert abs(result.calculated_value - 3.5) < 0.001

    # Line 249: Time domain with missing time column
    def test_time_domain_missing_time_column(self, engine):
        """Test time domain calculation with missing time column."""
        data = pd.DataFrame({
            "signal": [1.0, 2.0, 3.0, 4.0, 5.0],
        })
        indicator = IndicatorDefinition(
            name="response_time",
            indicator_type=IndicatorType.TIME_DOMAIN,
            signal_name="signal",
            formula="response_time",
        )
        result = engine.calculate(indicator, data)
        assert result.judgment == JudgmentResult.INCONCLUSIVE
        assert "Time column" in result.error_message

    # Line 258: Time domain with missing signal
    def test_time_domain_missing_signal(self, engine):
        """Test time domain calculation with missing signal."""
        data = pd.DataFrame({
            "time": [0.0, 0.1, 0.2, 0.3, 0.4],
        })
        indicator = IndicatorDefinition(
            name="response_time",
            indicator_type=IndicatorType.TIME_DOMAIN,
            signal_name="nonexistent",
            formula="response_time",
        )
        result = engine.calculate(indicator, data)
        assert result.judgment == JudgmentResult.INCONCLUSIVE
        assert "not found" in result.error_message

    # Line 295: Formula calculation with no formula
    def test_formula_no_formula(self, engine, sample_data):
        """Test formula calculation with no formula provided."""
        indicator = IndicatorDefinition(
            name="formula_test",
            indicator_type=IndicatorType.CALCULATED,
            formula=None,
        )
        result = engine.calculate(indicator, sample_data)
        assert result.judgment == JudgmentResult.INCONCLUSIVE
        assert "No formula provided" in result.error_message

    # Lines 331-332: Formula evaluation error
    def test_formula_evaluation_error(self, engine, sample_data):
        """Test formula calculation with evaluation error."""
        indicator = IndicatorDefinition(
            name="bad_formula",
            indicator_type=IndicatorType.CALCULATED,
            formula="undefined_var + 1",
        )
        result = engine.calculate(indicator, sample_data)
        assert result.judgment == JudgmentResult.INCONCLUSIVE
        assert "Formula evaluation error" in result.error_message

    # Line 364: Response time when thresholds not met
    def test_response_time_thresholds_not_met(self, engine):
        """Test response time when 10-90% thresholds cannot be found."""
        # Flat signal - no rise
        data = pd.DataFrame({
            "time": np.linspace(0, 1, 100),
            "signal": np.ones(100) * 5.0,  # Constant signal
        })
        indicator = IndicatorDefinition(
            name="response_time",
            indicator_type=IndicatorType.TIME_DOMAIN,
            signal_name="signal",
            formula="response_time",
        )
        result = engine.calculate(indicator, data)
        # Should return None for value since thresholds not met
        assert result.calculated_value is None
        assert result.judgment == JudgmentResult.INCONCLUSIVE

    # Line 376: Overshoot with zero target (uses nanmax as fallback)
    def test_overshoot_zero_target(self, engine):
        """Test overshoot calculation with zero target value (uses nanmax as fallback)."""
        data = pd.DataFrame({
            "time": np.linspace(0, 1, 100),
            "signal": np.linspace(0, 10, 100),
        })
        indicator = IndicatorDefinition(
            name="overshoot",
            indicator_type=IndicatorType.TIME_DOMAIN,
            signal_name="signal",
            formula="overshoot",
            target_value=0.0,
        )
        result = engine.calculate(indicator, data)
        # With target_value=0.0, the code uses `definition.target_value or np.nanmax(signal)`
        # Since 0.0 is falsy, it falls back to np.nanmax(signal) = 10.0
        # Then (signal_max - target) / abs(target) * 100 = (10 - 10) / 10 * 100 = 0.0
        assert result.calculated_value == 0.0
        assert result.judgment == JudgmentResult.PASS

    # Lines 380-397: Settling time calculation
    def test_settling_time(self, engine):
        """Test settling time calculation."""
        # Create signal that settles
        t = np.linspace(0, 2, 200)
        signal = 10 * (1 - np.exp(-5 * t))  # Exponential approach to 10
        data = pd.DataFrame({"time": t, "signal": signal})
        
        indicator = IndicatorDefinition(
            name="settling_time",
            indicator_type=IndicatorType.TIME_DOMAIN,
            signal_name="signal",
            formula="settling_time",
        )
        result = engine.calculate(indicator, data)
        assert result.calculated_value is not None
        assert result.calculation_details is not None
        assert "final_value" in result.calculation_details

    def test_settling_time_zero_final_value(self, engine):
        """Test settling time with zero final value."""
        # Signal that settles to zero
        t = np.linspace(0, 2, 200)
        signal = 10 * np.exp(-5 * t)  # Exponential decay to 0
        data = pd.DataFrame({"time": t, "signal": signal})
        
        indicator = IndicatorDefinition(
            name="settling_time",
            indicator_type=IndicatorType.TIME_DOMAIN,
            signal_name="signal",
            formula="settling_time",
        )
        result = engine.calculate(indicator, data)
        assert result.calculated_value is not None

    # Line 408: Unknown time domain metric
    def test_unknown_time_domain_metric(self, engine):
        """Test unknown time domain metric."""
        data = pd.DataFrame({
            "time": np.linspace(0, 1, 100),
            "signal": np.linspace(0, 10, 100),
        })
        indicator = IndicatorDefinition(
            name="unknown_metric",
            indicator_type=IndicatorType.TIME_DOMAIN,
            signal_name="signal",
            formula="unknown_metric",
        )
        result = engine.calculate(indicator, data)
        assert result.calculated_value is None
        assert result.judgment == JudgmentResult.INCONCLUSIVE
        assert "Unknown time domain metric" in result.calculation_details.get("error", "")

    # Additional edge cases for better coverage

    def test_single_value_no_time_column(self, engine):
        """Test single value calculation without time column."""
        data = pd.DataFrame({
            "signal1": [1.0, 2.0, 3.0, 4.0, 5.0],
        })
        indicator = IndicatorDefinition(
            name="test",
            indicator_type=IndicatorType.SINGLE_VALUE,
            signal_name="signal1",
        )
        result = engine.calculate(indicator, data)
        assert result.judgment == JudgmentResult.PASS
        assert result.time_range is None

    def test_statistical_no_time_column(self, engine):
        """Test statistical calculation without time column."""
        data = pd.DataFrame({
            "signal1": [1.0, 2.0, 3.0, 4.0, 5.0],
        })
        indicator = IndicatorDefinition(
            name="test",
            indicator_type=IndicatorType.STATISTICAL,
            signal_name="signal1",
            formula="mean",
        )
        result = engine.calculate(indicator, data)
        assert result.judgment == JudgmentResult.PASS
        assert result.time_range is None

    def test_formula_no_time_column(self, engine):
        """Test formula calculation without time column."""
        data = pd.DataFrame({
            "signal1": [1.0, 2.0, 3.0, 4.0, 5.0],
        })
        indicator = IndicatorDefinition(
            name="test",
            indicator_type=IndicatorType.CALCULATED,
            formula="signal1[-1] * 2",
        )
        result = engine.calculate(indicator, data)
        assert result.calculated_value == 10.0

    def test_single_value_with_nan_data(self, engine):
        """Test single value calculation with NaN values in signal."""
        data = pd.DataFrame({
            "time": [0.0, 0.1, 0.2, 0.3, 0.4],
            "signal1": [1.0, np.nan, 3.0, np.nan, 5.0],
        })
        indicator = IndicatorDefinition(
            name="test",
            indicator_type=IndicatorType.SINGLE_VALUE,
            signal_name="signal1",
        )
        result = engine.calculate(indicator, data)
        # Should use last non-NaN value
        assert result.calculated_value == 5.0
        assert result.data_points_used == 3  # Only non-NaN values

    def test_statistical_with_nan_data(self, engine):
        """Test statistical calculation with NaN values in signal."""
        data = pd.DataFrame({
            "time": [0.0, 0.1, 0.2, 0.3, 0.4],
            "signal1": [1.0, np.nan, 3.0, np.nan, 5.0],
        })
        indicator = IndicatorDefinition(
            name="test",
            indicator_type=IndicatorType.STATISTICAL,
            signal_name="signal1",
            formula="mean",
        )
        result = engine.calculate(indicator, data)
        # Mean of [1, 3, 5] = 3.0
        assert abs(result.calculated_value - 3.0) < 0.001
        assert result.data_points_used == 3

    def test_judge_value_none(self, engine):
        """Test _judge_value with None value."""
        indicator = IndicatorDefinition(
            name="test",
            indicator_type=IndicatorType.SINGLE_VALUE,
            signal_name="signal1",
        )
        result = engine._judge_value(None, indicator)
        assert result == JudgmentResult.INCONCLUSIVE

    def test_judge_value_with_tolerance_zero(self, engine):
        """Test _judge_value with zero tolerance."""
        indicator = IndicatorDefinition(
            name="test",
            indicator_type=IndicatorType.SINGLE_VALUE,
            signal_name="signal1",
            target_value=5.0,
            tolerance=0.0,
        )
        # Exact match should pass
        assert engine._judge_value(5.0, indicator) == JudgmentResult.PASS
        # Any deviation should fail
        assert engine._judge_value(5.1, indicator) == JudgmentResult.FAIL

    def test_register_formula_function_overwrite(self, engine, sample_data):
        """Test overwriting existing formula function."""
        # Register a function
        engine.register_formula_function("custom", lambda x: x * 2)
        
        indicator = IndicatorDefinition(
            name="test",
            indicator_type=IndicatorType.STATISTICAL,
            signal_name="signal1",
            formula="custom",
        )
        result = engine.calculate(indicator, sample_data)
        assert abs(result.calculated_value - 7.0) < 0.001  # 3.5 * 2
        
        # Overwrite with new function
        engine.register_formula_function("custom", lambda x: x * 3)
        result = engine.calculate(indicator, sample_data)
        assert abs(result.calculated_value - 10.5) < 0.001  # 3.5 * 3

    def test_indicator_result_dataclass(self):
        """Test IndicatorResult dataclass."""
        definition = IndicatorDefinition(
            name="test",
            indicator_type=IndicatorType.SINGLE_VALUE,
        )
        result = IndicatorResult(
            definition=definition,
            calculated_value=42.0,
            raw_value=40.0,
            judgment=JudgmentResult.PASS,
            data_points_used=100,
            time_range=(0.0, 10.0),
            calculation_details={"key": "value"},
            error_message=None,
        )
        assert result.calculated_value == 42.0
        assert result.raw_value == 40.0
        assert result.judgment == JudgmentResult.PASS
        assert result.data_points_used == 100
        assert result.time_range == (0.0, 10.0)
        assert result.calculation_details == {"key": "value"}
        assert result.error_message is None

    def test_formula_with_numpy_functions(self, engine, sample_data):
        """Test formula using numpy functions."""
        indicator = IndicatorDefinition(
            name="test",
            indicator_type=IndicatorType.CALCULATED,
            formula="np.mean(signal1) + np.std(signal1)",
        )
        result = engine.calculate(indicator, sample_data)
        assert result.calculated_value is not None
        assert result.judgment == JudgmentResult.PASS

    def test_time_domain_overshoot_no_target(self, engine):
        """Test overshoot calculation without target value."""
        data = pd.DataFrame({
            "time": np.linspace(0, 1, 100),
            "signal": np.linspace(0, 10, 100),
        })
        indicator = IndicatorDefinition(
            name="overshoot",
            indicator_type=IndicatorType.TIME_DOMAIN,
            signal_name="signal",
            formula="overshoot",
            target_value=None,  # No target specified
        )
        result = engine.calculate(indicator, data)
        # Should use np.nanmax(signal) as target
        assert result.calculation_details is not None
        assert "target" in result.calculation_details

    def test_response_time_valid_rise(self, engine):
        """Test response time with valid rising signal."""
        # Create a proper step response
        t = np.linspace(0, 1, 100)
        signal = np.zeros(100)
        signal[30:] = np.linspace(0, 10, 70)  # Rise from index 30
        
        data = pd.DataFrame({"time": t, "signal": signal})
        
        indicator = IndicatorDefinition(
            name="response_time",
            indicator_type=IndicatorType.TIME_DOMAIN,
            signal_name="signal",
            formula="response_time",
        )
        result = engine.calculate(indicator, data)
        # Should have a valid response time
        assert result.calculation_details is not None
        assert "threshold_10" in result.calculation_details
        assert "threshold_90" in result.calculation_details
