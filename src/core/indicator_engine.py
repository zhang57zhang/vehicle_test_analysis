"""
Indicator Engine - Calculate test metrics from signal data.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

import numpy as np
import pandas as pd
from scipy import integrate, signal


class IndicatorType(Enum):
    """Types of indicators."""

    SINGLE_VALUE = "single_value"
    CALCULATED = "calculated"
    TIME_DOMAIN = "time_domain"
    STATISTICAL = "statistical"


class JudgmentResult(Enum):
    """Result of indicator judgment."""

    PASS = "pass"
    FAIL = "fail"
    INCONCLUSIVE = "inconclusive"
    NOT_RUN = "not_run"


@dataclass
class IndicatorDefinition:
    """Definition of a test indicator."""

    name: str
    indicator_type: IndicatorType
    signal_name: Optional[str] = None
    formula: Optional[str] = None
    unit: Optional[str] = None
    lower_limit: Optional[float] = None
    upper_limit: Optional[float] = None
    target_value: Optional[float] = None
    tolerance: Optional[float] = None
    description: Optional[str] = None


@dataclass
class IndicatorResult:
    """Result of indicator calculation."""

    definition: IndicatorDefinition
    calculated_value: Optional[float]
    raw_value: Optional[float]
    judgment: JudgmentResult
    data_points_used: int = 0
    time_range: Optional[tuple] = None
    calculation_details: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class IndicatorEngine:
    """
    Engine for calculating test indicators from signal data.
    """

    def __init__(self):
        """Initialize the indicator engine."""
        self._formula_functions: Dict[str, Callable] = {
            "mean": np.mean,
            "std": np.std,
            "var": np.var,
            "min": np.min,
            "max": np.max,
            "median": np.median,
            "sum": np.sum,
            "abs": np.abs,
            "sqrt": np.sqrt,
            "square": np.square,
            "diff": np.diff,
            "gradient": np.gradient,
        }

    def calculate(
        self,
        definition: IndicatorDefinition,
        data: pd.DataFrame,
        time_column: str = "time",
    ) -> IndicatorResult:
        """
        Calculate an indicator from data.

        Args:
            definition: Indicator definition.
            data: DataFrame containing signal data.
            time_column: Name of the time column.

        Returns:
            IndicatorResult with calculated value and judgment.
        """
        try:
            if definition.indicator_type == IndicatorType.SINGLE_VALUE:
                return self._calculate_single_value(definition, data, time_column)
            elif definition.indicator_type == IndicatorType.STATISTICAL:
                return self._calculate_statistical(definition, data, time_column)
            elif definition.indicator_type == IndicatorType.TIME_DOMAIN:
                return self._calculate_time_domain(definition, data, time_column)
            elif definition.indicator_type == IndicatorType.CALCULATED:
                return self._calculate_formula(definition, data, time_column)
            else:
                return IndicatorResult(
                    definition=definition,
                    calculated_value=None,
                    raw_value=None,
                    judgment=JudgmentResult.INCONCLUSIVE,
                    error_message=f"Unknown indicator type: {definition.indicator_type}",
                )
        except Exception as e:
            return IndicatorResult(
                definition=definition,
                calculated_value=None,
                raw_value=None,
                judgment=JudgmentResult.INCONCLUSIVE,
                error_message=str(e),
            )

    def _calculate_single_value(
        self,
        definition: IndicatorDefinition,
        data: pd.DataFrame,
        time_column: str,
    ) -> IndicatorResult:
        """Calculate single signal value indicator."""
        if not definition.signal_name or definition.signal_name not in data.columns:
            return IndicatorResult(
                definition=definition,
                calculated_value=None,
                raw_value=None,
                judgment=JudgmentResult.INCONCLUSIVE,
                error_message=f"Signal '{definition.signal_name}' not found in data",
            )

        signal_data = data[definition.signal_name].dropna()
        if len(signal_data) == 0:
            return IndicatorResult(
                definition=definition,
                calculated_value=None,
                raw_value=None,
                judgment=JudgmentResult.INCONCLUSIVE,
                error_message="No valid data points",
            )

        # Get the value (could be last value, mean, or specific point)
        value = float(signal_data.iloc[-1])
        judgment = self._judge_value(value, definition)

        return IndicatorResult(
            definition=definition,
            calculated_value=value,
            raw_value=value,
            judgment=judgment,
            data_points_used=len(signal_data),
            time_range=(
                float(data[time_column].iloc[0]),
                float(data[time_column].iloc[-1]),
            )
            if time_column in data.columns
            else None,
        )

    def _calculate_statistical(
        self,
        definition: IndicatorDefinition,
        data: pd.DataFrame,
        time_column: str,
    ) -> IndicatorResult:
        """Calculate statistical indicator."""
        if not definition.signal_name or definition.signal_name not in data.columns:
            return IndicatorResult(
                definition=definition,
                calculated_value=None,
                raw_value=None,
                judgment=JudgmentResult.INCONCLUSIVE,
                error_message=f"Signal '{definition.signal_name}' not found in data",
            )

        signal_data = data[definition.signal_name].dropna()
        if len(signal_data) == 0:
            return IndicatorResult(
                definition=definition,
                calculated_value=None,
                raw_value=None,
                judgment=JudgmentResult.INCONCLUSIVE,
                error_message="No valid data points",
            )

        # Parse formula to determine statistical function
        formula = definition.formula or "mean"
        func = self._formula_functions.get(formula, np.mean)
        
        # Calculate base value first
        base_value = float(np.mean(signal_data.values))
        
        # Apply custom function if registered
        if formula in self._formula_functions:
            try:
                result = func(signal_data.values)
                # Handle functions that return arrays
                if isinstance(result, np.ndarray):
                    if result.size == 1:
                        value = float(result.item())
                    elif len(signal_data) > 0 and result.shape[0] == len(signal_data):
                        # Function transforms array, take mean of result
                        value = float(np.mean(result))
                    else:
                        value = base_value
                else:
                    value = float(result)
            except Exception:
                value = base_value
        else:
            value = base_value
        
        judgment = self._judge_value(value, definition)

        return IndicatorResult(
            definition=definition,
            calculated_value=value,
            raw_value=float(signal_data.mean()),
            judgment=judgment,
            data_points_used=len(signal_data),
            time_range=(
                float(data[time_column].iloc[0]),
                float(data[time_column].iloc[-1]),
            )
            if time_column in data.columns
            else None,
            calculation_details={"function": formula},
        )

    def _calculate_time_domain(
        self,
        definition: IndicatorDefinition,
        data: pd.DataFrame,
        time_column: str,
    ) -> IndicatorResult:
        """Calculate time domain indicator (response time, overshoot, etc.)."""
        if not definition.signal_name or definition.signal_name not in data.columns:
            return IndicatorResult(
                definition=definition,
                calculated_value=None,
                raw_value=None,
                judgment=JudgmentResult.INCONCLUSIVE,
                error_message=f"Signal '{definition.signal_name}' not found in data",
            )

        if time_column not in data.columns:
            return IndicatorResult(
                definition=definition,
                calculated_value=None,
                raw_value=None,
                judgment=JudgmentResult.INCONCLUSIVE,
                error_message=f"Time column '{time_column}' not found in data",
            )

        time_data = data[time_column].values
        signal_data = data[definition.signal_name].values

        # Parse formula for time domain calculation
        formula = definition.formula or "response_time"
        value, details = self._compute_time_domain_metric(
            formula, time_data, signal_data, definition
        )

        judgment = self._judge_value(value, definition)

        return IndicatorResult(
            definition=definition,
            calculated_value=value,
            raw_value=None,
            judgment=judgment,
            data_points_used=len(signal_data),
            time_range=(float(time_data[0]), float(time_data[-1])),
            calculation_details=details,
        )

    def _calculate_formula(
        self,
        definition: IndicatorDefinition,
        data: pd.DataFrame,
        time_column: str,
    ) -> IndicatorResult:
        """Calculate indicator using custom formula."""
        if not definition.formula:
            return IndicatorResult(
                definition=definition,
                calculated_value=None,
                raw_value=None,
                judgment=JudgmentResult.INCONCLUSIVE,
                error_message="No formula provided for calculated indicator",
            )

        # Create evaluation context with signal data
        context = {}
        for col in data.columns:
            if col != time_column:
                context[col] = data[col].values

        # Add numpy functions
        context.update(self._formula_functions)
        context["np"] = np

        try:
            value = float(eval(definition.formula, {"__builtins__": {}}, context))
            judgment = self._judge_value(value, definition)

            return IndicatorResult(
                definition=definition,
                calculated_value=value,
                raw_value=value,
                judgment=judgment,
                data_points_used=len(data),
                time_range=(
                    float(data[time_column].iloc[0]),
                    float(data[time_column].iloc[-1]),
                )
                if time_column in data.columns
                else None,
                calculation_details={"formula": definition.formula},
            )
        except Exception as e:
            return IndicatorResult(
                definition=definition,
                calculated_value=None,
                raw_value=None,
                judgment=JudgmentResult.INCONCLUSIVE,
                error_message=f"Formula evaluation error: {e}",
            )

    def _compute_time_domain_metric(
        self,
        metric: str,
        time: np.ndarray,
        signal: np.ndarray,
        definition: IndicatorDefinition,
    ) -> tuple:
        """Compute specific time domain metric."""
        details = {"metric": metric}

        if metric == "response_time":
            # Calculate 10-90% rise time
            signal_min, signal_max = np.nanmin(signal), np.nanmax(signal)
            signal_range = signal_max - signal_min

            threshold_10 = signal_min + 0.1 * signal_range
            threshold_90 = signal_min + 0.9 * signal_range

            idx_10 = np.argmax(signal >= threshold_10)
            idx_90 = np.argmax(signal >= threshold_90)

            if idx_10 > 0 and idx_90 > idx_10:
                value = float(time[idx_90] - time[idx_10])
            else:
                value = None

            details["threshold_10"] = threshold_10
            details["threshold_90"] = threshold_90

        elif metric == "overshoot":
            # Calculate overshoot percentage
            target = definition.target_value or np.nanmax(signal)
            signal_max = np.nanmax(signal)
            if target != 0:
                value = float((signal_max - target) / abs(target) * 100)
            else:
                value = None
            details["target"] = target
            details["max_value"] = signal_max

        elif metric == "settling_time":
            # Calculate settling time (within 2% of final value)
            final_value = signal[-1]
            tolerance = 0.02 * abs(final_value) if final_value != 0 else 0.02

            settled_idx = len(signal) - 1
            for i in range(len(signal) - 1, -1, -1):
                if abs(signal[i] - final_value) > tolerance:
                    settled_idx = i + 1
                    break

            value = float(time[settled_idx] - time[0])
            details["final_value"] = final_value
            details["tolerance"] = tolerance

        else:
            value = None
            details["error"] = f"Unknown time domain metric: {metric}"

        return value, details

    def _judge_value(
        self,
        value: Optional[float],
        definition: IndicatorDefinition,
    ) -> JudgmentResult:
        """Judge if a value passes the criteria."""
        if value is None:
            return JudgmentResult.INCONCLUSIVE

        # Check against limits
        if definition.lower_limit is not None and value < definition.lower_limit:
            return JudgmentResult.FAIL

        if definition.upper_limit is not None and value > definition.upper_limit:
            return JudgmentResult.FAIL

        # Check against target with tolerance
        if definition.target_value is not None:
            tolerance = definition.tolerance or 0.0
            if abs(value - definition.target_value) > tolerance:
                return JudgmentResult.FAIL

        return JudgmentResult.PASS

    def register_formula_function(self, name: str, func: Callable) -> None:
        """Register a custom formula function."""
        self._formula_functions[name] = func
