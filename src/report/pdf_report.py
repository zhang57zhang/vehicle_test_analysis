"""
PDF report generator.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class PDFReportConfig:
    """Configuration for PDF report generation."""

    page_size: str = "A4"
    margin_top: float = 72  # points
    margin_bottom: float = 72
    margin_left: float = 72
    margin_right: float = 72
    font_name: str = "Helvetica"
    font_size: int = 10
    title_font_size: int = 24
    heading_font_size: int = 14


class PDFReportGenerator:
    """
    Generator for PDF format reports.
    """

    def __init__(
        self,
        template_path: Optional[Path] = None,
        config: Optional[PDFReportConfig] = None,
    ):
        """
        Initialize PDF report generator.

        Args:
            template_path: Optional path to template file.
            config: PDF configuration options.
        """
        self.template_path = template_path
        self.config = config or PDFReportConfig()

    def generate(
        self,
        report_data: Any,
        output_path: Path,
        include_data_source: bool = True,
    ) -> bool:
        """
        Generate PDF report.

        Args:
            report_data: Data for the report.
            output_path: Path to save the report.
            include_data_source: Whether to include data source information.

        Returns:
            True if generation successful.
        """
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.platypus import (
                SimpleDocTemplate,
                Paragraph,
                Spacer,
                Table,
                TableStyle,
                PageBreak,
                Image,
            )
            from reportlab.lib import colors
        except ImportError:
            raise ImportError(
                "reportlab is required for PDF report generation. "
                "Install with: pip install reportlab"
            )

        # Create document
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            topMargin=self.config.margin_top,
            bottomMargin=self.config.margin_bottom,
            leftMargin=self.config.margin_left,
            rightMargin=self.config.margin_right,
        )

        # Create styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Heading1"],
            fontSize=self.config.title_font_size,
            alignment=1,  # Center
            spaceAfter=30,
        )
        heading_style = ParagraphStyle(
            "CustomHeading",
            parent=styles["Heading2"],
            fontSize=self.config.heading_font_size,
            spaceBefore=20,
            spaceAfter=10,
        )

        # Build content
        story = []

        # Title
        story.append(Paragraph(report_data.title, title_style))
        story.append(Spacer(1, 20))

        # Metadata
        story.append(Paragraph(f"项目名称: {report_data.project_name}", styles["Normal"]))
        story.append(Paragraph(f"测试阶段: {report_data.test_phase}", styles["Normal"]))
        story.append(
            Paragraph(
                f"生成时间: {report_data.generated_at.strftime('%Y-%m-%d %H:%M:%S')}",
                styles["Normal"],
            )
        )
        story.append(Paragraph(f"生成人: {report_data.generated_by}", styles["Normal"]))
        story.append(PageBreak())

        # Sections
        for section in report_data.sections:
            story.append(Paragraph(section.title, heading_style))
            story.append(Paragraph(section.content, styles["Normal"]))
            story.append(Spacer(1, 10))

        # Tables
        for table_data in report_data.tables:
            story.extend(self._create_table(table_data, styles))

        # Data source
        if include_data_source and report_data.metadata:
            story.append(PageBreak())
            story.append(Paragraph("数据溯源", heading_style))
            for key, value in report_data.metadata.items():
                story.append(Paragraph(f"{key}: {value}", styles["Normal"]))

        # Build PDF
        doc.build(story)
        return True

    def _create_table(self, table_data: Dict[str, Any], styles) -> List:
        """Create a table element."""
        from reportlab.lib import colors
        from reportlab.platypus import Table, TableStyle, Paragraph

        elements = []

        headers = table_data.get("headers", [])
        rows = table_data.get("rows", [])
        title = table_data.get("title", "")

        if title:
            elements.append(Paragraph(title, styles["Heading3"]))

        if not headers or not rows:
            return elements

        # Create table data
        table_rows = [headers] + rows

        table = Table(table_rows)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )

        elements.append(table)
        return elements
