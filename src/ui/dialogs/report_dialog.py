# -*- coding: utf-8 -*-
"""
Report generation dialog.
"""

from datetime import datetime
from typing import Optional

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QRadioButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class ReportDialog(QDialog):
    """
    Dialog for generating reports.
    """

    def __init__(
        self,
        db_manager,
        project_id: int,
        user_id: int,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._db = db_manager
        self._project_id = project_id
        self._user_id = user_id
        self._output_path = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        self.setWindowTitle("Generate Report")
        self.setMinimumWidth(500)

        layout = QVBoxLayout(self)

        project = self._db.get_project(self._project_id)
        project_name = project.name if project else "Unknown"

        info_group = QGroupBox("Project Information")
        info_layout = QFormLayout(info_group)
        info_layout.addRow("Project Name:", QLineEdit(project_name))
        if project:
            info_layout.addRow("Test Phase:", QLineEdit(project.test_phase))
        layout.addWidget(info_group)

        report_group = QGroupBox("Report Settings")
        report_layout = QFormLayout(report_group)

        self._title_edit = QLineEdit()
        self._title_edit.setText(f"{project_name} Test Report")
        report_layout.addRow("Report Title:", self._title_edit)

        self._type_formal_radio = QRadioButton("Formal Report")
        self._type_audit_radio = QRadioButton("Audit Report (with data traceability)")
        self._type_formal_radio.setChecked(True)
        report_layout.addRow("Report Type:", self._type_formal_radio)
        report_layout.addRow("", self._type_audit_radio)

        self._format_combo = QComboBox()
        self._format_combo.addItems(["Word (.docx)", "PDF (.pdf)"])
        report_layout.addRow("Output Format:", self._format_combo)

        self._template_combo = QComboBox()
        self._template_combo.addItems(
            [
                "Standard Template",
                "MIL Test Template",
                "HIL Test Template",
                "DVP Test Template",
                "Vehicle Test Template",
            ]
        )
        report_layout.addRow("Report Template:", self._template_combo)

        layout.addWidget(report_group)

        content_group = QGroupBox("Report Content")
        content_layout = QFormLayout(content_group)

        self._summary_edit = QTextEdit()
        self._summary_edit.setPlaceholderText("Test summary...")
        self._summary_edit.setMaximumHeight(80)
        content_layout.addRow("Summary:", self._summary_edit)

        self._conclusion_edit = QTextEdit()
        self._conclusion_edit.setPlaceholderText("Test conclusion...")
        self._conclusion_edit.setMaximumHeight(80)
        content_layout.addRow("Conclusion:", self._conclusion_edit)

        layout.addWidget(content_group)

        output_group = QGroupBox("Output Settings")
        output_layout = QFormLayout(output_group)

        self._output_edit = QLineEdit()
        self._output_edit.setPlaceholderText("Select output directory...")
        self._output_edit.setReadOnly(True)
        output_layout.addRow("Output Directory:", self._output_edit)

        layout.addWidget(output_group)

        self._progress_bar = QProgressBar()
        self._progress_bar.setVisible(False)
        layout.addWidget(self._progress_bar)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_generate)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self._generate_btn = button_box.button(QDialogButtonBox.StandardButton.Ok)
        self._generate_btn.setText("Generate Report")

    def _on_generate(self) -> None:
        """Generate the report."""
        title = self._title_edit.text().strip()
        if not title:
            QMessageBox.warning(self, "Error", "Please enter report title")
            return

        if not self._output_path:
            from pathlib import Path

            self._output_path = Path("data/exports")
            self._output_path.mkdir(parents=True, exist_ok=True)

        self._progress_bar.setVisible(True)
        self._progress_bar.setRange(0, 0)
        self._generate_btn.setEnabled(False)

        try:
            self._generate_report()
            self._progress_bar.setRange(0, 100)
            self._progress_bar.setValue(100)
            QMessageBox.information(
                self, "Complete", f"Report generated: {self._output_path}"
            )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate report: {str(e)}")
        finally:
            self._progress_bar.setVisible(False)
            self._generate_btn.setEnabled(True)

    def _generate_report(self) -> None:
        """Generate the actual report."""
        from pathlib import Path
        from src.report.word_report import (
            WordReportGenerator,
            ReportData,
            ReportSection,
        )
        from src.report.pdf_report import PDFReportGenerator

        project = self._db.get_project(self._project_id)
        test_cases = self._db.list_test_cases(self._project_id)

        is_audit = self._type_audit_radio.isChecked()
        is_pdf = self._format_combo.currentIndex() == 1

        sections = []

        sections.append(
            ReportSection(
                title="Test Overview",
                content=self._summary_edit.toPlainText()
                or "This test was executed according to test case requirements.",
                level=1,
            )
        )

        if test_cases:
            tc_content = "Test Case List:\n\n"
            for tc in test_cases:
                tc_content += f"- {tc.case_id}: {tc.name} ({tc.test_type})\n"
            sections.append(
                ReportSection(
                    title="Test Cases",
                    content=tc_content,
                    level=1,
                )
            )

        data_files = self._db.list_data_files(self._project_id)
        if data_files:
            df_content = "Data Files:\n\n"
            for df in data_files:
                df_content += f"- {df.file_name} ({df.file_type.upper()})\n"
            sections.append(
                ReportSection(
                    title="Data Files",
                    content=df_content,
                    level=1,
                )
            )

        sections.append(
            ReportSection(
                title="Test Conclusion",
                content=self._conclusion_edit.toPlainText()
                or "Test completed. See results for details.",
                level=1,
            )
        )

        tables = []
        if test_cases:
            rows = []
            for tc in test_cases:
                results = self._db.list_test_results(tc.id)
                result_str = results[0].result if results else "Not Run"
                rows.append([tc.case_id, tc.name, tc.test_type, result_str])

            tables.append(
                {
                    "title": "Test Results Summary",
                    "headers": ["Case ID", "Case Name", "Test Type", "Result"],
                    "rows": rows,
                }
            )

        metadata = {}
        if is_audit:
            metadata["Project ID"] = str(self._project_id)
            metadata["Generated By User ID"] = str(self._user_id)
            metadata["Generated At"] = datetime.now().isoformat()
            if data_files:
                metadata["Data File Count"] = str(len(data_files))

        report_data = ReportData(
            title=self._title_edit.text(),
            project_name=project.name if project else "Unknown",
            test_phase=project.test_phase if project else "Unknown",
            generated_at=datetime.now(),
            generated_by="System",
            sections=sections,
            tables=tables,
            figures=[],
            metadata=metadata,
        )

        output_dir = Path(self._output_path)
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if is_pdf:
            output_file = output_dir / f"report_{timestamp}.pdf"
            generator = PDFReportGenerator()
        else:
            output_file = output_dir / f"report_{timestamp}.docx"
            generator = WordReportGenerator()

        generator.generate(report_data, output_file, include_data_source=is_audit)

        self._db.create_report(
            project_id=self._project_id,
            name=self._title_edit.text(),
            generated_by=self._user_id,
            report_type="audit" if is_audit else "formal",
            format="pdf" if is_pdf else "docx",
            file_path=str(output_file),
            template_used=self._template_combo.currentText(),
        )
