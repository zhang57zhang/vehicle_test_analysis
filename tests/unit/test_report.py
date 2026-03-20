"""Unit tests for report modules."""

import sys
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from src.report.word_report import (
    ReportData,
    ReportSection,
    WordReportGenerator,
    TestResultTable,
)
from src.report.pdf_report import (
    PDFReportConfig,
    PDFReportGenerator,
)


class TestReportSection:
    """Tests for ReportSection dataclass."""

    def test_create_section(self):
        """Test creating a report section."""
        section = ReportSection(
            title="Introduction",
            content="This is the introduction.",
            level=1,
        )
        assert section.title == "Introduction"
        assert section.content == "This is the introduction."
        assert section.level == 1

    def test_section_defaults(self):
        """Test section default values."""
        section = ReportSection(title="Test", content="Content")
        assert section.level == 1


class TestReportData:
    """Tests for ReportData dataclass."""

    def test_create_report_data(self):
        """Test creating report data."""
        data = ReportData(
            title="Test Report",
            project_name="Test Project",
            test_phase="HIL",
            generated_at=datetime.now(),
            generated_by="Test User",
            sections=[],
            tables=[],
            figures=[],
            metadata={},
        )
        assert data.title == "Test Report"
        assert data.project_name == "Test Project"
        assert data.test_phase == "HIL"


class TestWordReportGenerator:
    """Tests for WordReportGenerator class."""

    def test_init(self):
        """Test initialization."""
        generator = WordReportGenerator()
        assert generator.template_path is None

    def test_init_with_template(self, tmp_path):
        """Test initialization with template."""
        template = tmp_path / "template.docx"
        template.write_bytes(b"PK")  # Minimal docx header

        generator = WordReportGenerator(template_path=template)
        assert generator.template_path == template

    def test_generate_with_existing_template(self, tmp_path):
        """Test generating report using an existing template file."""
        # First create a valid docx file by generating one
        generator = WordReportGenerator()
        report_data = ReportData(
            title="Template Test",
            project_name="Test Project",
            test_phase="HIL",
            generated_at=datetime.now(),
            generated_by="Test User",
            sections=[],
            tables=[],
            figures=[],
            metadata={},
        )
        template_path = tmp_path / "template.docx"
        generator.generate(report_data, template_path)
        
        # Now use it as a template
        generator_with_template = WordReportGenerator(template_path=template_path)
        output_path = tmp_path / "from_template.docx"
        result = generator_with_template.generate(report_data, output_path)
        
        assert result is True
        assert output_path.exists()

    def test_generate_simple_report(self, tmp_path):
        """Test generating a simple report."""
        generator = WordReportGenerator()

        report_data = ReportData(
            title="Test Report",
            project_name="Test Project",
            test_phase="HIL",
            generated_at=datetime.now(),
            generated_by="Test User",
            sections=[
                ReportSection(title="Section 1", content="Content 1"),
                ReportSection(title="Section 2", content="Content 2", level=2),
            ],
            tables=[],
            figures=[],
            metadata={"Source": "Test Data"},
        )

        output_path = tmp_path / "report.docx"
        result = generator.generate(report_data, output_path)

        assert result is True
        assert output_path.exists()
        assert output_path.stat().st_size > 0

    def test_generate_report_with_table(self, tmp_path):
        """Test generating a report with a table."""
        generator = WordReportGenerator()

        report_data = ReportData(
            title="Test Report",
            project_name="Test Project",
            test_phase="HIL",
            generated_at=datetime.now(),
            generated_by="Test User",
            sections=[],
            tables=[
                {
                    "title": "Test Results",
                    "headers": ["Name", "Value", "Result"],
                    "rows": [
                        ["Indicator 1", "1.5", "Pass"],
                        ["Indicator 2", "2.0", "Pass"],
                    ],
                }
            ],
            figures=[],
            metadata={},
        )

        output_path = tmp_path / "report_with_table.docx"
        result = generator.generate(report_data, output_path)

        assert result is True
        assert output_path.exists()

    def test_generate_report_without_data_source(self, tmp_path):
        """Test generating a report without data source."""
        generator = WordReportGenerator()

        report_data = ReportData(
            title="Test Report",
            project_name="Test Project",
            test_phase="HIL",
            generated_at=datetime.now(),
            generated_by="Test User",
            sections=[],
            tables=[],
            figures=[],
            metadata={"Source": "Test Data"},
        )

        output_path = tmp_path / "report_no_source.docx"
        result = generator.generate(
            report_data, output_path, include_data_source=False
        )

        assert result is True

    def test_generate_creates_parent_directories(self, tmp_path):
        """Test that generation creates parent directories."""
        generator = WordReportGenerator()

        report_data = ReportData(
            title="Test Report",
            project_name="Test Project",
            test_phase="HIL",
            generated_at=datetime.now(),
            generated_by="Test User",
            sections=[],
            tables=[],
            figures=[],
            metadata={},
        )

        output_path = tmp_path / "subdir" / "report.docx"
        result = generator.generate(report_data, output_path)

        assert result is True
        assert output_path.exists()

    def test_generate_report_with_empty_table(self, tmp_path):
        """Test generating a report with an empty table (no headers/rows)."""
        generator = WordReportGenerator()

        report_data = ReportData(
            title="Test Report",
            project_name="Test Project",
            test_phase="HIL",
            generated_at=datetime.now(),
            generated_by="Test User",
            sections=[],
            tables=[
                {"title": "Empty Table", "headers": [], "rows": []},
                {"title": "No Rows", "headers": ["A", "B"], "rows": []},
                {"title": "No Headers", "headers": [], "rows": [["1", "2"]]},
            ],
            figures=[],
            metadata={},
        )

        output_path = tmp_path / "report_empty_table.docx"
        result = generator.generate(report_data, output_path)

        assert result is True
        assert output_path.exists()

    def test_generate_report_with_figure(self, tmp_path):
        """Test generating a report with a figure."""
        generator = WordReportGenerator()

        # Create a test image
        from PIL import Image
        image_path = tmp_path / "test_image.png"
        img = Image.new('RGB', (100, 100), color='red')
        img.save(image_path)

        report_data = ReportData(
            title="Test Report",
            project_name="Test Project",
            test_phase="HIL",
            generated_at=datetime.now(),
            generated_by="Test User",
            sections=[],
            tables=[],
            figures=[
                {
                    "path": str(image_path),
                    "caption": "Test Figure",
                    "width": 4,
                }
            ],
            metadata={},
        )

        output_path = tmp_path / "report_with_figure.docx"
        result = generator.generate(report_data, output_path)

        assert result is True
        assert output_path.exists()

    def test_generate_report_with_figure_no_caption(self, tmp_path):
        """Test generating a report with a figure without caption."""
        generator = WordReportGenerator()

        # Create a test image
        from PIL import Image
        image_path = tmp_path / "test_image.png"
        img = Image.new('RGB', (100, 100), color='blue')
        img.save(image_path)

        report_data = ReportData(
            title="Test Report",
            project_name="Test Project",
            test_phase="HIL",
            generated_at=datetime.now(),
            generated_by="Test User",
            sections=[],
            tables=[],
            figures=[
                {
                    "path": str(image_path),
                    "caption": "",  # Empty caption
                    "width": 5,
                }
            ],
            metadata={},
        )

        output_path = tmp_path / "report_figure_no_caption.docx"
        result = generator.generate(report_data, output_path)

        assert result is True
        assert output_path.exists()

    def test_generate_report_with_missing_figure(self, tmp_path):
        """Test generating a report with a missing figure file."""
        generator = WordReportGenerator()

        report_data = ReportData(
            title="Test Report",
            project_name="Test Project",
            test_phase="HIL",
            generated_at=datetime.now(),
            generated_by="Test User",
            sections=[],
            tables=[],
            figures=[
                {
                    "path": str(tmp_path / "nonexistent.png"),
                    "caption": "Missing Figure",
                    "width": 6,
                }
            ],
            metadata={},
        )

        output_path = tmp_path / "report_missing_figure.docx"
        result = generator.generate(report_data, output_path)

        # Should still succeed, just without the figure
        assert result is True
        assert output_path.exists()

    def test_generate_report_with_empty_metadata(self, tmp_path):
        """Test generating a report with empty metadata (no data source section)."""
        generator = WordReportGenerator()

        report_data = ReportData(
            title="Test Report",
            project_name="Test Project",
            test_phase="HIL",
            generated_at=datetime.now(),
            generated_by="Test User",
            sections=[],
            tables=[],
            figures=[],
            metadata={},  # Empty metadata
        )

        output_path = tmp_path / "report_empty_metadata.docx"
        result = generator.generate(report_data, output_path, include_data_source=True)

        assert result is True
        assert output_path.exists()


class TestPDFReportConfig:
    """Tests for PDFReportConfig dataclass."""

    def test_default_config(self):
        """Test default configuration."""
        config = PDFReportConfig()
        assert config.page_size == "A4"
        assert config.font_name == "Helvetica"
        assert config.font_size == 10

    def test_custom_config(self):
        """Test custom configuration."""
        config = PDFReportConfig(
            page_size="Letter",
            font_size=12,
            title_font_size=28,
        )
        assert config.page_size == "Letter"
        assert config.font_size == 12
        assert config.title_font_size == 28


class TestPDFReportGenerator:
    """Tests for PDFReportGenerator class."""

    def test_init(self):
        """Test initialization."""
        generator = PDFReportGenerator()
        assert generator.config is not None

    def test_init_with_config(self):
        """Test initialization with custom config."""
        config = PDFReportConfig(font_size=12)
        generator = PDFReportGenerator(config=config)
        assert generator.config.font_size == 12

    def test_generate_simple_report(self, tmp_path):
        """Test generating a simple PDF report."""
        generator = PDFReportGenerator()

        report_data = ReportData(
            title="Test Report",
            project_name="Test Project",
            test_phase="HIL",
            generated_at=datetime.now(),
            generated_by="Test User",
            sections=[
                ReportSection(title="Section 1", content="Content 1"),
            ],
            tables=[],
            figures=[],
            metadata={"Source": "Test Data"},
        )

        output_path = tmp_path / "report.pdf"
        result = generator.generate(report_data, output_path)

        assert result is True
        assert output_path.exists()
        assert output_path.stat().st_size > 0

    def test_generate_report_with_table(self, tmp_path):
        """Test generating a PDF report with a table."""
        generator = PDFReportGenerator()

        report_data = ReportData(
            title="Test Report",
            project_name="Test Project",
            test_phase="HIL",
            generated_at=datetime.now(),
            generated_by="Test User",
            sections=[],
            tables=[
                {
                    "title": "Test Results",
                    "headers": ["Name", "Value", "Result"],
                    "rows": [
                        ["Indicator 1", "1.5", "Pass"],
                        ["Indicator 2", "2.0", "Pass"],
                    ],
                }
            ],
            figures=[],
            metadata={},
        )

        output_path = tmp_path / "report_with_table.pdf"
        result = generator.generate(report_data, output_path)

        assert result is True
        assert output_path.exists()

    def test_generate_creates_parent_directories(self, tmp_path):
        """Test that generation creates parent directories."""
        generator = PDFReportGenerator()

        report_data = ReportData(
            title="Test Report",
            project_name="Test Project",
            test_phase="HIL",
            generated_at=datetime.now(),
            generated_by="Test User",
            sections=[],
            tables=[],
            figures=[],
            metadata={},
        )

        output_path = tmp_path / "subdir" / "report.pdf"
        result = generator.generate(report_data, output_path)

        assert result is True
        assert output_path.exists()

    def test_generate_report_with_empty_table(self, tmp_path):
        """Test generating a PDF report with an empty table (no headers/rows)."""
        generator = PDFReportGenerator()

        report_data = ReportData(
            title="Test Report",
            project_name="Test Project",
            test_phase="HIL",
            generated_at=datetime.now(),
            generated_by="Test User",
            sections=[],
            tables=[
                {"title": "Empty Table", "headers": [], "rows": []},
                {"title": "No Rows", "headers": ["A", "B"], "rows": []},
                {"title": "No Headers", "headers": [], "rows": [["1", "2"]]},
            ],
            figures=[],
            metadata={},
        )

        output_path = tmp_path / "report_empty_table.pdf"
        result = generator.generate(report_data, output_path)

        assert result is True
        assert output_path.exists()

    def test_generate_report_without_data_source(self, tmp_path):
        """Test generating a PDF report without data source."""
        generator = PDFReportGenerator()

        report_data = ReportData(
            title="Test Report",
            project_name="Test Project",
            test_phase="HIL",
            generated_at=datetime.now(),
            generated_by="Test User",
            sections=[],
            tables=[],
            figures=[],
            metadata={"Source": "Test Data"},
        )

        output_path = tmp_path / "report_no_source.pdf"
        result = generator.generate(
            report_data, output_path, include_data_source=False
        )

        assert result is True
        assert output_path.exists()


class TestTestResultTable:
    """Tests for TestResultTable helper class."""

    def test_from_indicator_results_empty(self):
        """Test creating table from empty results."""
        table_data = TestResultTable.from_indicator_results([])
        
        assert table_data["title"] == "测试结果汇总"
        assert table_data["headers"] == ["指标名称", "计算值", "判定结果", "备注"]
        assert table_data["rows"] == []

    def test_from_indicator_results_with_data(self):
        """Test creating table from indicator results."""
        # Create mock indicator results
        class MockIndicator:
            def __init__(self, name):
                self.name = name

        class MockJudgment:
            def __init__(self, value):
                self.value = value

        class MockResult:
            def __init__(self, name, value, judgment, error=None):
                self.definition = MockIndicator(name)
                self.calculated_value = value
                self.judgment = MockJudgment(judgment)
                self.error_message = error

        results = [
            MockResult("Speed", 100.0, "Pass"),
            MockResult("Temperature", 85.5, "Pass"),
            MockResult("Pressure", None, "Fail", "Sensor error"),
        ]

        table_data = TestResultTable.from_indicator_results(results)

        assert len(table_data["rows"]) == 3
        assert table_data["rows"][0][0] == "Speed"
        assert table_data["rows"][0][2] == "Pass"

    def test_from_indicator_results_custom_title(self):
        """Test creating table with custom title."""
        table_data = TestResultTable.from_indicator_results(
            [], title="Custom Title"
        )
        assert table_data["title"] == "Custom Title"


class TestImportErrors:
    """Tests for ImportError handling when dependencies are missing."""

    def test_pdf_report_import_error(self, tmp_path):
        """Test PDF report raises ImportError when reportlab is not available."""
        generator = PDFReportGenerator()
        report_data = ReportData(
            title="Test Report",
            project_name="Test Project",
            test_phase="HIL",
            generated_at=datetime.now(),
            generated_by="Test User",
            sections=[],
            tables=[],
            figures=[],
            metadata={},
        )
        output_path = tmp_path / "report.pdf"

        # Mock the import to raise ImportError
        with patch.dict(sys.modules, {'reportlab': None, 'reportlab.lib': None, 'reportlab.lib.pagesizes': None}):
            with patch('builtins.__import__', side_effect=lambda name, *args, **kwargs: 
                       (_ for _ in ()).throw(ImportError(f"No module named '{name}'")) if name.startswith('reportlab') 
                       else __import__(name, *args, **kwargs)):
                with pytest.raises(ImportError, match="reportlab is required"):
                    generator.generate(report_data, output_path)

    def test_word_report_import_error(self, tmp_path):
        """Test Word report raises ImportError when python-docx is not available."""
        generator = WordReportGenerator()
        report_data = ReportData(
            title="Test Report",
            project_name="Test Project",
            test_phase="HIL",
            generated_at=datetime.now(),
            generated_by="Test User",
            sections=[],
            tables=[],
            figures=[],
            metadata={},
        )
        output_path = tmp_path / "report.docx"

        # Mock the import to raise ImportError
        with patch.dict(sys.modules, {'docx': None}):
            with patch('builtins.__import__', side_effect=lambda name, *args, **kwargs: 
                       (_ for _ in ()).throw(ImportError(f"No module named '{name}'")) if name.startswith('docx') 
                       else __import__(name, *args, **kwargs)):
                with pytest.raises(ImportError, match="python-docx is required"):
                    generator.generate(report_data, output_path)
