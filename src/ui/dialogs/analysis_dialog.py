# -*- coding: utf-8 -*-
"""
Analysis configuration dialog.
"""

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QProgressBar,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


class AnalysisDialog(QDialog):
    """
    Dialog for configuring and running analysis.
    """

    def __init__(self, db_manager, project_id: int, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._db = db_manager
        self._project_id = project_id
        self._results = []
        self._setup_ui()
        self._load_data_files()

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        self.setWindowTitle("Analysis Configuration")
        self.setMinimumSize(600, 500)

        layout = QVBoxLayout(self)

        self._tab_widget = QTabWidget()
        layout.addWidget(self._tab_widget)

        self._tab_widget.addTab(self._create_data_tab(), "Data Selection")
        self._tab_widget.addTab(self._create_indicator_tab(), "Indicators")
        self._tab_widget.addTab(self._create_options_tab(), "Options")

        self._progress_bar = QProgressBar()
        self._progress_bar.setVisible(False)
        layout.addWidget(self._progress_bar)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_run)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self._run_button = button_box.button(QDialogButtonBox.StandardButton.Ok)
        self._run_button.setText("Run Analysis")

    def _create_data_tab(self) -> QWidget:
        """Create data selection tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        label = QLabel("Select data files to analyze:")
        layout.addWidget(label)

        self._file_list = QListWidget()
        self._file_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        layout.addWidget(self._file_list)

        info_group = QGroupBox("File Information")
        info_layout = QVBoxLayout(info_group)
        self._file_info_label = QLabel("Select a file to view details")
        self._file_info_label.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )
        info_layout.addWidget(self._file_info_label)
        layout.addWidget(info_group)

        self._file_list.itemSelectionChanged.connect(self._update_file_info)

        return widget

    def _create_indicator_tab(self) -> QWidget:
        """Create indicator configuration tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        signal_group = QGroupBox("Signal Selection")
        signal_layout = QVBoxLayout(signal_group)

        self._signal_list = QListWidget()
        self._signal_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        signal_layout.addWidget(self._signal_list)

        layout.addWidget(signal_group)

        analysis_group = QGroupBox("Analysis Type")
        analysis_layout = QFormLayout(analysis_group)

        self._analysis_type_combo = QComboBox()
        self._analysis_type_combo.addItems(
            [
                "Statistical Calculation",
                "Response Time Analysis",
                "Trend Analysis",
                "Range Check",
                "State Transition Validation",
            ]
        )
        analysis_layout.addRow("Analysis Type:", self._analysis_type_combo)

        self._stat_func_combo = QComboBox()
        self._stat_func_combo.addItems(
            ["Mean", "Max", "Min", "Std Dev", "Median", "Percentile"]
        )
        analysis_layout.addRow("Stat Function:", self._stat_func_combo)

        layout.addWidget(analysis_group)

        limit_group = QGroupBox("Judgment Limits")
        limit_layout = QFormLayout(limit_group)

        self._lower_limit_edit = QLineEdit()
        self._lower_limit_edit.setPlaceholderText("Lower limit value")
        limit_layout.addRow("Lower Limit:", self._lower_limit_edit)

        self._upper_limit_edit = QLineEdit()
        self._upper_limit_edit.setPlaceholderText("Upper limit value")
        limit_layout.addRow("Upper Limit:", self._upper_limit_edit)

        self._target_edit = QLineEdit()
        self._target_edit.setPlaceholderText("Target value")
        limit_layout.addRow("Target Value:", self._target_edit)

        layout.addWidget(limit_group)

        return widget

    def _create_options_tab(self) -> QWidget:
        """Create analysis options tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        time_group = QGroupBox("Time Range")
        time_layout = QFormLayout(time_group)

        self._time_start_edit = QLineEdit()
        self._time_start_edit.setPlaceholderText("Start time (s)")
        time_layout.addRow("Start Time:", self._time_start_edit)

        self._time_end_edit = QLineEdit()
        self._time_end_edit.setPlaceholderText("End time (s)")
        time_layout.addRow("End Time:", self._time_end_edit)

        layout.addWidget(time_group)

        sync_group = QGroupBox("Time Synchronization")
        sync_layout = QFormLayout(sync_group)

        self._sync_check = QCheckBox("Enable multi-source time sync")
        self._sync_check.setChecked(True)
        sync_layout.addRow(self._sync_check)

        self._sync_precision_spin = QSpinBox()
        self._sync_precision_spin.setRange(1, 1000)
        self._sync_precision_spin.setValue(10)
        self._sync_precision_spin.setSuffix(" ms")
        sync_layout.addRow("Sync Precision:", self._sync_precision_spin)

        layout.addWidget(sync_group)

        output_group = QGroupBox("Output Options")
        output_layout = QFormLayout(output_group)

        self._auto_report_check = QCheckBox("Auto-generate report after analysis")
        output_layout.addRow(self._auto_report_check)

        self._save_results_check = QCheckBox("Save results to database")
        self._save_results_check.setChecked(True)
        output_layout.addRow(self._save_results_check)

        layout.addWidget(output_group)
        layout.addStretch()

        return widget

    def _load_data_files(self) -> None:
        """Load data files for current project."""
        data_files = self._db.list_data_files(self._project_id)

        self._file_list.clear()
        for df in data_files:
            if df.import_status == "parsed":
                self._file_list.addItem(f"{df.file_name} ({df.file_type.upper()})")
                self._file_list.item(self._file_list.count() - 1).setData(
                    Qt.ItemDataRole.UserRole, df.id
                )

        signals = []
        for df in data_files:
            if df.import_status == "parsed":
                file_signals = self._db.list_signals(df.id)
                for sig in file_signals:
                    self._signal_list.addItem(sig.name)
                    self._signal_list.item(self._signal_list.count() - 1).setData(
                        Qt.ItemDataRole.UserRole, sig.id
                    )

    def _update_file_info(self) -> None:
        """Update file info display."""
        selected = self._file_list.selectedItems()
        if not selected:
            self._file_info_label.setText("Select a file to view details")
            return

        item = selected[0]
        file_id = item.data(Qt.ItemDataRole.UserRole)
        data_file = self._db.get_data_file(file_id)

        if data_file:
            info = f"File: {data_file.file_name}\n"
            info += f"Type: {data_file.file_type}\n"
            info += f"Size: {data_file.file_size / 1024:.1f} KB\n"
            info += f"Data Points: {data_file.data_points or 'N/A'}\n"
            info += f"Signals: {data_file.signal_count or 'N/A'}\n"
            if data_file.time_range_start is not None:
                info += f"Time Range: {data_file.time_range_start:.2f}s - {data_file.time_range_end:.2f}s"
            self._file_info_label.setText(info)

    def _on_run(self) -> None:
        """Run analysis."""
        selected_files = self._file_list.selectedItems()
        selected_signals = self._signal_list.selectedItems()

        if not selected_files:
            QMessageBox.warning(self, "Error", "Please select at least one data file")
            return

        if not selected_signals:
            QMessageBox.warning(self, "Error", "Please select at least one signal")
            return

        self._progress_bar.setVisible(True)
        self._progress_bar.setRange(0, 0)
        self._run_button.setEnabled(False)

        try:
            self._run_analysis(selected_signals)
            self._progress_bar.setRange(0, 100)
            self._progress_bar.setValue(100)
            QMessageBox.information(self, "Complete", "Analysis completed")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Analysis failed: {str(e)}")
        finally:
            self._progress_bar.setVisible(False)
            self._run_button.setEnabled(True)

    def _run_analysis(self, selected_signals) -> None:
        """Run the actual analysis."""
        from src.core.indicator_engine import (
            IndicatorEngine,
            IndicatorDefinition,
            IndicatorType,
        )
        from src.parsers.csv_parser import CSVParser
        from src.parsers.can_parser import CANParser
        from src.parsers.mdf_parser import MDFParser
        import pandas as pd

        engine = IndicatorEngine()
        analysis_type = self._analysis_type_combo.currentIndex()
        stat_func_map = {
            0: "mean",
            1: "max",
            2: "min",
            3: "std",
            4: "median",
            5: "percentile",
        }

        selected_files = self._file_list.selectedItems()
        for file_item in selected_files:
            file_id = file_item.data(Qt.ItemDataRole.UserRole)
            data_file = self._db.get_data_file(file_id)

            parser = None
            path = __import__("pathlib").Path(data_file.file_path)

            if data_file.file_type.lower() in ("blf", "asc"):
                parser = CANParser(path)
            elif data_file.file_type.lower() in ("mdf", "mf4", "dat"):
                parser = MDFParser(path)
            elif data_file.file_type.lower() in ("csv", "txt", "log"):
                parser = CSVParser(path)

            if parser:
                result = parser.parse()
                if result.is_success and result.data is not None:
                    for sig_item in selected_signals:
                        signal_name = sig_item.text()

                        if signal_name not in result.data.columns:
                            continue

                        lower = (
                            float(self._lower_limit_edit.text())
                            if self._lower_limit_edit.text()
                            else None
                        )
                        upper = (
                            float(self._upper_limit_edit.text())
                            if self._upper_limit_edit.text()
                            else None
                        )
                        target = (
                            float(self._target_edit.text())
                            if self._target_edit.text()
                            else None
                        )

                        indicator_type = IndicatorType.STATISTICAL
                        formula = stat_func_map.get(
                            self._stat_func_combo.currentIndex(), "mean"
                        )

                        indicator = IndicatorDefinition(
                            name=f"{signal_name}_{formula}",
                            signal_name=signal_name,
                            indicator_type=indicator_type,
                            formula=formula,
                            lower_limit=lower,
                            upper_limit=upper,
                            target_value=target,
                        )

                        ind_result = engine.calculate(indicator, result.data)
                        self._results.append(
                            {
                                "signal": signal_name,
                                "value": ind_result.calculated_value,
                                "judgment": ind_result.judgment.value,
                                "details": ind_result.calculation_details,
                            }
                        )

    def get_results(self) -> list:
        """Get analysis results."""
        return self._results
