"""
Integration tests for vehicle test analysis system.

Tests the complete data flow:
Parse -> Time Sync -> Indicator Calculation -> Analysis -> Report
"""

import os
import tempfile
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.parsers.csv_parser import CSVParser
from src.parsers.base_parser import ParserStatus
from src.core.time_sync import TimeSynchronizer
from src.core.indicator_engine import (
    IndicatorDefinition,
    IndicatorEngine,
    IndicatorType,
)
from src.analyzers.functional_analyzer import FunctionalAnalyzer
from src.analyzers.performance_analyzer import PerformanceAnalyzer
from src.report.word_report import (
    ReportData,
    ReportSection,
    WordReportGenerator,
)
from src.report.pdf_report import PDFReportGenerator
from src.database.operations import DatabaseManager


class TestCSVToIntegration:
    """Integration tests starting from CSV parsing."""

    @pytest.fixture
    def sample_csv_data(self, tmp_path):
        """Create sample CSV data file."""
        csv_path = tmp_path / "test_data.csv"

        # Create sample data with multiple signals
        data = pd.DataFrame({
            "time": np.linspace(0, 10, 1001),
            "VehicleSpeed": np.concatenate([
                np.linspace(0, 100, 500),
                np.linspace(100, 50, 501)
            ]),
            "EngineSpeed": np.concatenate([
                np.linspace(800, 3000, 500),
                np.linspace(3000, 1500, 501)
            ]),
            "ThrottlePosition": np.concatenate([
                np.linspace(0, 100, 200),
                np.ones(300) * 100,
                np.linspace(100, 50, 501)
            ]),
            "BrakePressure": np.concatenate([
                np.zeros(300),
                np.linspace(0, 50, 200),
                np.linspace(50, 0, 501)
            ]),
        })

        data.to_csv(csv_path, index=False)
        return csv_path, data

    def test_csv_parse_to_time_sync(self, sample_csv_data):
        """Test CSV parsing to time synchronization."""
        csv_path, expected_data = sample_csv_data

        # Parse CSV
        parser = CSVParser(csv_path)
        result = parser.parse()

        assert result.is_success
        assert result.data is not None

        # Time sync - use align_to_common_time for single source
        sync = TimeSynchronizer(precision_ms=10)

        synced_data = sync.align_to_common_time(
            [result.data],
            ["time"],
        )
        assert synced_data is not None
        assert "time" in synced_data.columns

    def test_csv_parse_to_indicator_calculation(self, sample_csv_data):
        """Test CSV parsing to indicator calculation."""
        csv_path, expected_data = sample_csv_data

        # Parse CSV
        parser = CSVParser(csv_path)
        result = parser.parse()

        assert result.is_success

        # Define indicators
        engine = IndicatorEngine()

        indicators = [
            IndicatorDefinition(
                name="MaxVehicleSpeed",
                signal_name="VehicleSpeed",
                indicator_type=IndicatorType.SINGLE_VALUE,
                formula="max",
                upper_limit=120,
            ),
            IndicatorDefinition(
                name="AvgEngineSpeed",
                signal_name="EngineSpeed",
                indicator_type=IndicatorType.STATISTICAL,
                formula="mean",
                lower_limit=500,
                upper_limit=5000,
            ),
        ]

        # Calculate indicators
        results = [engine.calculate(result.data, ind) for ind in indicators]

        assert len(results) == 2
        assert all(r.judgment is not None for r in results)

    def test_full_analysis_pipeline(self, sample_csv_data):
        """Test complete analysis pipeline."""
        csv_path, expected_data = sample_csv_data

        # Step 1: Parse
        parser = CSVParser(csv_path)
        parse_result = parser.parse()
        assert parse_result.is_success

        data = parse_result.data

        # Step 2: Time sync (optional for single source)
        sync = TimeSynchronizer(precision_ms=10)
        synced_data = sync.align_to_common_time([data], ["time"])

        # Note: align_to_common_time renames columns with source_0_ prefix
        # For single source, we can use the original data
        original_data = data

        # Step 3: Calculate indicators
        engine = IndicatorEngine()

        indicators = [
            IndicatorDefinition(
                name="MaxSpeed",
                signal_name="VehicleSpeed",
                indicator_type=IndicatorType.SINGLE_VALUE,
                formula="max",
            ),
            IndicatorDefinition(
                name="AvgThrottle",
                signal_name="ThrottlePosition",
                indicator_type=IndicatorType.STATISTICAL,
                formula="mean",
            ),
        ]

        indicator_results = [engine.calculate(original_data, ind) for ind in indicators]
        assert len(indicator_results) == 2

        # Step 4: Functional analysis
        func_analyzer = FunctionalAnalyzer()

        range_result = func_analyzer.check_value_range(
            original_data,
            "VehicleSpeed",
            min_value=0,
            max_value=120,
        )
        assert range_result.passed

        # Step 5: Performance analysis
        perf_analyzer = PerformanceAnalyzer()

        stats_result = perf_analyzer.calculate_statistics(
            original_data,
            "EngineSpeed",
        )
        assert stats_result.passed
        assert "mean" in stats_result.details


class TestReportGeneration:
    """Integration tests for report generation."""

    @pytest.fixture
    def sample_report_data(self):
        """Create sample report data."""
        return ReportData(
            title="Vehicle Test Analysis Report",
            project_name="HIL Test Project",
            test_phase="HIL",
            generated_at=datetime.now(),
            generated_by="Test Engineer",
            sections=[
                ReportSection(
                    title="1. 测试概述",
                    content="本次测试对车辆控制系统进行了全面的功能和性能验证。",
                ),
                ReportSection(
                    title="2. 测试条件",
                    content="测试环境：HIL台架\n测试温度：25°C",
                    level=2,
                ),
                ReportSection(
                    title="3. 测试结果",
                    content="所有测试项目均通过。",
                ),
            ],
            tables=[
                {
                    "title": "测试结果汇总",
                    "headers": ["指标名称", "计算值", "单位", "判定结果"],
                    "rows": [
                        ["最高车速", "100.0", "km/h", "Pass"],
                        ["平均发动机转速", "1766.5", "rpm", "Pass"],
                        ["响应时间", "0.5", "s", "Pass"],
                    ],
                }
            ],
            figures=[],
            metadata={
                "数据源": "test_data.csv",
                "时间范围": "0.0 - 10.0 s",
                "采样点数": "1001",
            },
        )

    def test_word_report_generation(self, sample_report_data, tmp_path):
        """Test Word report generation."""
        generator = WordReportGenerator()
        output_path = tmp_path / "test_report.docx"

        result = generator.generate(sample_report_data, output_path)

        assert result is True
        assert output_path.exists()
        assert output_path.stat().st_size > 0

    def test_pdf_report_generation(self, sample_report_data, tmp_path):
        """Test PDF report generation."""
        generator = PDFReportGenerator()
        output_path = tmp_path / "test_report.pdf"

        result = generator.generate(sample_report_data, output_path)

        assert result is True
        assert output_path.exists()
        assert output_path.stat().st_size > 0

    def test_report_with_analysis_results(self, tmp_path):
        """Test report generation with analysis results."""
        # Create sample data
        data = pd.DataFrame({
            "time": np.linspace(0, 10, 1001),
            "VehicleSpeed": np.linspace(0, 100, 1001),
            "EngineSpeed": np.linspace(800, 3000, 1001),
        })

        # Run analysis
        func_analyzer = FunctionalAnalyzer()
        perf_analyzer = PerformanceAnalyzer()

        func_analyzer.check_value_range(data, "VehicleSpeed", 0, 120)
        perf_analyzer.calculate_statistics(data, "EngineSpeed")

        # Create report
        report_data = ReportData(
            title="Analysis Report",
            project_name="Test Project",
            test_phase="HIL",
            generated_at=datetime.now(),
            generated_by="Test Engineer",
            sections=[
                ReportSection(
                    title="Analysis Results",
                    content="See table below for details.",
                ),
            ],
            tables=[
                {
                    "title": "Functional Test Results",
                    "headers": ["Test", "Result", "Message"],
                    "rows": [
                        [r.test_name, "Pass" if r.passed else "Fail", r.message]
                        for r in func_analyzer.get_results()
                    ],
                },
                {
                    "title": "Performance Metrics",
                    "headers": ["Metric", "Value", "Unit"],
                    "rows": [
                        [r.test_name, f"{r.metric_value:.2f}", r.unit or ""]
                        for r in perf_analyzer.get_results()
                    ],
                },
            ],
            figures=[],
            metadata={},
        )

        generator = WordReportGenerator()
        output_path = tmp_path / "analysis_report.docx"

        result = generator.generate(report_data, output_path)

        assert result is True
        assert output_path.exists()


class TestDatabaseIntegration:
    """Integration tests for database operations."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        db_url = f"sqlite:///{db_path}"
        db_manager = DatabaseManager(db_url)
        db_manager.initialize()

        yield db_manager

        try:
            os.unlink(db_path)
        except Exception:
            pass

    def test_project_workflow(self, temp_db):
        """Test complete project workflow."""
        # Create user
        user = temp_db.create_user("engineer", "hash", role="engineer")

        # Create project
        project = temp_db.create_project(
            name="Test Project",
            owner_id=user.id,
            test_phase="HIL",
        )

        # Create test case
        test_case = temp_db.create_test_case(
            project_id=project.id,
            case_id="TC001",
            name="Speed Test",
            test_type="functional",
        )

        # Create indicator
        indicator = temp_db.create_indicator(
            test_case_id=test_case.id,
            name="MaxSpeed",
            signal_name="VehicleSpeed",
            indicator_type="single_value",
            unit="km/h",
            upper_limit=120.0,
        )

        # Create test result
        test_result = temp_db.create_test_result(
            test_case_id=test_case.id,
            result="pass",
        )

        # Create indicator result
        indicator_result = temp_db.create_indicator_result(
            test_result_id=test_result.id,
            indicator_id=indicator.id,
            result="pass",
            calculated_value=100.0,
        )

        # Verify
        assert temp_db.get_project(project.id) is not None
        assert len(temp_db.list_test_cases(project.id)) == 1
        assert len(temp_db.list_indicators(test_case.id)) == 1

    def test_data_file_workflow(self, temp_db):
        """Test data file workflow."""
        # Setup
        user = temp_db.create_user("engineer", "hash")
        project = temp_db.create_project("Test Project", user.id)

        # Create data file
        data_file = temp_db.create_data_file(
            project_id=project.id,
            file_name="test_data.csv",
            file_path="/data/test_data.csv",
            file_type="csv",
            file_size=1024,
            time_range_start=0.0,
            time_range_end=10.0,
            data_points=1001,
            signal_count=4,
        )

        # Create signals
        signal1 = temp_db.create_signal(
            data_file_id=data_file.id,
            name="VehicleSpeed",
            data_type="float",
            unit="km/h",
        )
        signal2 = temp_db.create_signal(
            data_file_id=data_file.id,
            name="EngineSpeed",
            data_type="float",
            unit="rpm",
        )

        # Verify
        assert len(temp_db.list_data_files(project.id)) == 1
        assert len(temp_db.list_signals(data_file.id)) == 2

    def test_report_workflow(self, temp_db):
        """Test report workflow."""
        # Setup
        user = temp_db.create_user("engineer", "hash")
        project = temp_db.create_project("Test Project", user.id)

        # Create report
        report = temp_db.create_report(
            project_id=project.id,
            name="Test Report",
            generated_by=user.id,
            report_type="formal",
            format="docx",
            file_path="/reports/test_report.docx",
        )

        # Verify
        assert len(temp_db.list_reports(project.id)) == 1
        assert temp_db.get_report(report.id) is not None


class TestEndToEndWorkflow:
    """End-to-end workflow tests."""

    @pytest.fixture
    def setup_environment(self, tmp_path):
        """Setup test environment with data and database."""
        # Create CSV data
        csv_path = tmp_path / "test_data.csv"
        data = pd.DataFrame({
            "time": np.linspace(0, 10, 1001),
            "VehicleSpeed": np.concatenate([
                np.linspace(0, 100, 500),
                np.linspace(100, 50, 501)
            ]),
            "EngineSpeed": np.concatenate([
                np.linspace(800, 3000, 500),
                np.linspace(3000, 1500, 501)
            ]),
        })
        data.to_csv(csv_path, index=False)

        # Create database
        db_path = tmp_path / "test.db"
        db_url = f"sqlite:///{db_path}"
        db_manager = DatabaseManager(db_url)
        db_manager.initialize()

        return {
            "csv_path": csv_path,
            "db_manager": db_manager,
            "output_dir": tmp_path,
        }

    def test_complete_workflow(self, setup_environment):
        """Test complete analysis workflow from data to report."""
        csv_path = setup_environment["csv_path"]
        db = setup_environment["db_manager"]
        output_dir = setup_environment["output_dir"]

        # Step 1: Create user and project in database
        user = db.create_user("engineer", "hash")
        project = db.create_project("HIL Test", user.id, test_phase="HIL")

        # Step 2: Parse data
        parser = CSVParser(csv_path)
        parse_result = parser.parse()
        assert parse_result.is_success

        # Step 3: Record data file
        data_file = db.create_data_file(
            project_id=project.id,
            file_name=csv_path.name,
            file_path=str(csv_path),
            file_type="csv",
            file_size=csv_path.stat().st_size,
            data_points=len(parse_result.data),
            signal_count=len(parse_result.signals),
        )

        # Step 4: Create test case and indicators
        test_case = db.create_test_case(
            project_id=project.id,
            case_id="TC001",
            name="Speed Performance Test",
        )

        indicator1 = db.create_indicator(
            test_case_id=test_case.id,
            name="MaxVehicleSpeed",
            signal_name="VehicleSpeed",
            indicator_type="single_value",
            formula="max",
            unit="km/h",
            upper_limit=120.0,
        )

        indicator2 = db.create_indicator(
            test_case_id=test_case.id,
            name="AvgEngineSpeed",
            signal_name="EngineSpeed",
            indicator_type="statistical",
            formula="mean",
            unit="rpm",
            lower_limit=500.0,
            upper_limit=5000.0,
        )

        # Step 5: Calculate indicators
        engine = IndicatorEngine()

        indicator_defs = [
            IndicatorDefinition(
                name="MaxVehicleSpeed",
                signal_name="VehicleSpeed",
                indicator_type=IndicatorType.SINGLE_VALUE,
                formula="max",
                upper_limit=120.0,
            ),
            IndicatorDefinition(
                name="AvgEngineSpeed",
                signal_name="EngineSpeed",
                indicator_type=IndicatorType.STATISTICAL,
                formula="mean",
                lower_limit=500.0,
                upper_limit=5000.0,
            ),
        ]

        results = [engine.calculate(parse_result.data, ind) for ind in indicator_defs]

        # Step 6: Store test results
        all_pass = all(r.judgment and r.judgment != "fail" for r in results)
        test_result = db.create_test_result(
            test_case_id=test_case.id,
            result="pass" if all_pass else "fail",
        )

        for r in results:
            ind_name = r.definition["name"] if isinstance(r.definition, dict) else getattr(r.definition, "name", "unknown")
            db.create_indicator_result(
                test_result_id=test_result.id,
                indicator_id=indicator1.id if ind_name == "MaxVehicleSpeed" else indicator2.id,
                result="pass" if r.judgment != "fail" else "fail",
                calculated_value=r.calculated_value,
            )

        # Step 7: Generate report
        report_data = ReportData(
            title="Vehicle Test Analysis Report",
            project_name=project.name,
            test_phase=project.test_phase,
            generated_at=datetime.now(),
            generated_by=user.username,
            sections=[
                ReportSection(title="Test Summary", content="All tests passed."),
            ],
            tables=[
                {
                    "title": "Indicator Results",
                    "headers": ["Indicator", "Value", "Unit", "Result"],
                    "rows": [
                        [r.definition["name"] if isinstance(r.definition, dict) else getattr(r.definition, "name", "unknown"),
                         f"{r.calculated_value:.2f}" if r.calculated_value is not None else "N/A",
                         r.definition.get("unit", "") if isinstance(r.definition, dict) else getattr(r.definition, "unit", ""),
                         "Pass" if r.judgment != "fail" else "Fail"]
                        for r in results
                    ],
                }
            ],
            figures=[],
            metadata={
                "Data File": csv_path.name,
                "Test Case": test_case.name,
            },
        )

        report_path = output_dir / "test_report.docx"
        generator = WordReportGenerator()
        success = generator.generate(report_data, report_path)

        # Step 8: Record report in database
        db.create_report(
            project_id=project.id,
            name="Test Report",
            generated_by=user.id,
            file_path=str(report_path),
        )

        # Verify complete workflow
        assert parse_result.is_success
        assert len(results) == 2
        assert success
        assert report_path.exists()
        assert len(db.list_reports(project.id)) == 1
