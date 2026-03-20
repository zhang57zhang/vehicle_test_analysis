"""
Core module - Time synchronization and data alignment.
"""

from typing import List, Optional

import numpy as np
import pandas as pd


class TimeSynchronizer:
    """
    Time synchronization for multiple data sources.

    Supports aligning data from different sources with different
    time bases to a common time reference.
    """

    def __init__(self, precision_ms: float = 10.0):
        """
        Initialize time synchronizer.

        Args:
            precision_ms: Time synchronization precision in milliseconds.
        """
        self.precision_ms = precision_ms
        self.precision_s = precision_ms / 1000.0

    def align_to_common_time(
        self,
        dataframes: List[pd.DataFrame],
        time_columns: List[str],
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
    ) -> pd.DataFrame:
        """
        Align multiple DataFrames to a common time base.

        Args:
            dataframes: List of DataFrames to align.
            time_columns: List of column names containing timestamps.
            start_time: Optional start time for the common time base.
            end_time: Optional end time for the common time base.

        Returns:
            DataFrame with aligned data.
        """
        if not dataframes:
            return pd.DataFrame()

        if len(dataframes) != len(time_columns):
            raise ValueError("Number of dataframes must match number of time columns")

        # Find the time range
        all_times = []
        for df, time_col in zip(dataframes, time_columns):
            if time_col in df.columns:
                all_times.extend(df[time_col].values)

        if not all_times:
            return pd.DataFrame()

        if start_time is None:
            start_time = min(all_times)
        if end_time is None:
            end_time = max(all_times)

        # Create common time base
        common_time = np.arange(start_time, end_time, self.precision_s)

        # Align each DataFrame
        aligned_data = {"time": common_time}

        for i, (df, time_col) in enumerate(zip(dataframes, time_columns)):
            if time_col not in df.columns:
                continue

            df_sorted = df.sort_values(time_col)

            for col in df_sorted.columns:
                if col == time_col:
                    continue

                # Interpolate values to common time base
                aligned_data[f"source_{i}_{col}"] = np.interp(
                    common_time,
                    df_sorted[time_col].values,
                    df_sorted[col].values,
                    left=np.nan,
                    right=np.nan,
                )

        return pd.DataFrame(aligned_data)

    def resample(
        self,
        df: pd.DataFrame,
        time_column: str,
        target_rate_hz: float,
    ) -> pd.DataFrame:
        """
        Resample a DataFrame to a target sample rate.

        Args:
            df: Input DataFrame.
            time_column: Name of the time column.
            target_rate_hz: Target sample rate in Hz.

        Returns:
            Resampled DataFrame.
        """
        if time_column not in df.columns:
            raise ValueError(f"Time column '{time_column}' not found")

        if len(df) < 2:
            return df.copy()

        df_sorted = df.sort_values(time_column)
        time_values = df_sorted[time_column].values

        start_time = time_values[0]
        end_time = time_values[-1]
        step = 1.0 / target_rate_hz

        new_time = np.arange(start_time, end_time, step)

        result = {time_column: new_time}

        for col in df_sorted.columns:
            if col == time_column:
                continue

            result[col] = np.interp(
                new_time,
                time_values,
                df_sorted[col].values,
                left=np.nan,
                right=np.nan,
            )

        return pd.DataFrame(result)


def convert_timestamp_to_seconds(
    timestamp,
    format_string: Optional[str] = None,
    epoch: str = "unix",
) -> float:
    """
    Convert various timestamp formats to seconds.

    Args:
        timestamp: Input timestamp (various formats supported).
        format_string: Strptime format string if timestamp is a string.
        epoch: Epoch reference ('unix' or 'gps').

    Returns:
        Timestamp in seconds.
    """
    if isinstance(timestamp, (int, float)):
        return float(timestamp)

    if isinstance(timestamp, str):
        if format_string:
            from datetime import datetime

            dt = datetime.strptime(timestamp, format_string)
            return dt.timestamp()
        else:
            # Try to parse as float
            try:
                return float(timestamp)
            except ValueError:
                raise ValueError(f"Cannot parse timestamp: {timestamp}")

    if hasattr(timestamp, "timestamp"):
        # datetime-like object
        return timestamp.timestamp()

    raise TypeError(f"Unsupported timestamp type: {type(timestamp)}")
