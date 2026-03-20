"""Integration tests for parser to indicator engine workflow."""

import pandas as pd
import pytest
from pathlib import Path

from src.parsers.csv_parser import CSVParser
from src.core.indicator_engine import (
    IndicatorDefinition,
    IndicatorEngine,
    IndicatorType,
)
from src.core.time_sync import TimeSynchronizer


class TestParserToIndicatorIntegration:
    """Integration tests for parser to indicator engine workflow."""

    @pytest.fixture
    def sample_csv_with_indicators(self, tmp_path):
        """Create a CSV file with test data for indicator testing."""
        data = pd.DataFrame(
            {
                "time": [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9],
                "vehicle_speed": [0.0, 10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0],
                "engine_rpm": [800, 1200, 1600, 2000, 2400, 2800, 3200, 3600, 4000, 4400],
                "throttle_position": [0.0, 10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0],
            }
        )
        csv_path = tmp_path / "vehicle_data.csv"
        data.to_csv(csv_path, index=False)
        return csv_path

    def test_full_workflow_single_value(self, sample_csv_with_indicators):
        """Test full workflow: parse CSV -> calculate indicator."""
        # Step 1: Parse CSV
        parser = CSVParser(sample_csv_with_indicators, time_column="time")
        parse_result = parser.parse()

        assert parse_result.is_success
        assert parse_result.data is not None

        # Step 2: Calculate indicator
        engine = IndicatorEngine()
        indicator = IndicatorDefinition(
            name="final_speed",
            indicator_type=IndicatorType.SINGLE_VALUE,
            signal_name="vehicle_speed",
            lower_limit=0.0,
            upper_limit=100.0,
        )

        result = engine.calculate(indicator, parse_result.data)

        assert result.judgment != "fail"
        assert result.calculated_value == 90.0

    def test_full_workflow_statistical(self, sample_csv_with_indicators):
        """Test full workflow with statistical indicator."""
        # Parse
        parser = CSVParser(sample_csv_with_indicators, time_column="time")
        parse_result = parser.parse()

        # Calculate mean RPM
        engine = IndicatorEngine()
        indicator = IndicatorDefinition(
            name="mean_rpm",
            indicator_type=IndicatorType.STATISTICAL,
            signal_name="engine_rpm",
            formula="mean",
            lower_limit=1000.0,
            upper_limit=5000.0,
        )

        result = engine.calculate(indicator, parse_result.data)

        assert result.judgment != "fail"
        assert result.calculated_value > 1000.0

    def test_full_workflow_multiple_indicators(self, sample_csv_with_indicators):
        """Test workflow with multiple indicators."""
        # Parse
        parser = CSVParser(sample_csv_with_indicators, time_column="time")
        parse_result = parser.parse()

        # Define multiple indicators
        indicators = [
            IndicatorDefinition(
                name="max_speed",
                indicator_type=IndicatorType.STATISTICAL,
                signal_name="vehicle_speed",
                formula="max",
                upper_limit=100.0,
            ),
            IndicatorDefinition(
                name="min_rpm",
                indicator_type=IndicatorType.STATISTICAL,
                signal_name="engine_rpm",
                formula="min",
                lower_limit=500.0,
            ),
            IndicatorDefinition(
                name="mean_throttle",
                indicator_type=IndicatorType.STATISTICAL,
                signal_name="throttle_position",
                formula="mean",
            ),
        ]

        # Calculate all
        engine = IndicatorEngine()
        results = [engine.calculate(ind, parse_result.data) for ind in indicators]

        assert all(r.judgment != "fail" for r in results)
        assert results[0].calculated_value == 90.0
        assert results[1].calculated_value == 800

    def test_workflow_with_time_range_filter(self, sample_csv_with_indicators):
        """Test workflow with time range filtering."""
        # Parse
        parser = CSVParser(sample_csv_with_indicators, time_column="time")
        parser.parse()

        # Get filtered data
        filtered_data = parser.get_data(time_range=(0.2, 0.5))

        assert filtered_data is not None
        assert len(filtered_data) > 0

        # Calculate on filtered data
        engine = IndicatorEngine()
        indicator = IndicatorDefinition(
            name="filtered_speed",
            indicator_type=IndicatorType.SINGLE_VALUE,
            signal_name="vehicle_speed",
        )

        result = engine.calculate(indicator, filtered_data)

        # Should be 50.0 (value at time 0.5)
        assert result.calculated_value == 50.0


class TestTimeSyncIntegration:
    """Integration tests for time synchronization with parsers."""

    def test_sync_multiple_csv_files(self, tmp_path):
        """Test synchronizing data from multiple CSV files."""
        # Create two CSV files with different sample rates
        data1 = pd.DataFrame(
            {
                "time": [0.0, 0.1, 0.2, 0.3, 0.4],
                "signal1": [1.0, 2.0, 3.0, 4.0, 5.0],
            }
        )
        data2 = pd.DataFrame(
            {
                "time": [0.0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4],
                "signal2": [10.0, 12.0, 14.0, 16.0, 18.0, 20.0, 22.0, 24.0, 26.0],
            }
        )

        csv1 = tmp_path / "data1.csv"
        csv2 = tmp_path / "data2.csv"
        data1.to_csv(csv1, index=False)
        data2.to_csv(csv2, index=False)

        # Parse both files
        parser1 = CSVParser(csv1, time_column="time")
        parser2 = CSVParser(csv2, time_column="time")

        result1 = parser1.parse()
        result2 = parser2.parse()

        assert result1.is_success
        assert result2.is_success

        # Synchronize
        sync = TimeSynchronizer(precision_ms=10.0)
        aligned = sync.align_to_common_time(
            [result1.data, result2.data],
            ["time", "time"],
        )

        assert "time" in aligned.columns
        assert any("signal1" in col for col in aligned.columns)
        assert any("signal2" in col for col in aligned.columns)


class TestDatabaseIntegration:
    """Integration tests for database operations."""

    def test_store_parse_results(self, tmp_path):
        """Test storing parse results in database."""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session

        from src.database.models import Base, User, Project, DataFile, Signal

        # Create test data
        data = pd.DataFrame(
            {
                "time": [0.0, 0.1, 0.2],
                "speed": [0.0, 10.0, 20.0],
            }
        )
        csv_path = tmp_path / "test.csv"
        data.to_csv(csv_path, index=False)

        # Parse
        parser = CSVParser(csv_path, time_column="time")
        parse_result = parser.parse()

        # Store in database
        db_path = tmp_path / "test.db"
        engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(engine)

        with Session(engine) as session:
            # Create user and project
            user = User(username="testuser", password_hash="hash")
            session.add(user)
            session.commit()

            project = Project(name="Test Project", owner_id=user.id)
            session.add(project)
            session.commit()

            # Create data file record
            data_file = DataFile(
                project_id=project.id,
                file_name=parse_result.metadata["file_name"],
                file_path=str(csv_path),
                file_size=parse_result.metadata["file_size"],
                file_type="csv",
                data_points=parse_result.metadata["row_count"],
            )
            session.add(data_file)
            session.commit()

            # Create signal records
            for sig in parse_result.signals:
                signal = Signal(
                    data_file_id=data_file.id,
                    name=sig["name"],
                    data_type=sig["type"],
                )
                session.add(signal)
            session.commit()

            # Verify
            assert data_file.id is not None
            signals = session.query(Signal).filter(
                Signal.data_file_id == data_file.id
            ).all()
            assert len(signals) == 1  # only speed (time is excluded as time_column)
