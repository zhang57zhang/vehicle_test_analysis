# -*- coding: utf-8 -*-
"""
Main window for the Vehicle Test Analysis application.
"""

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QFileDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMenuBar,
    QMessageBox,
    QStatusBar,
    QTabWidget,
    QToolBar,
    QWidget,
)


class MainWindow(QMainWindow):
    """
    Main application window.
    """

    def __init__(
        self, db_manager=None, auth_service=None, parent: Optional[QWidget] = None
    ):
        """Initialize main window."""
        super().__init__(parent)

        self._db = db_manager
        self._auth = auth_service
        self._current_project_id: Optional[int] = None
        self._imported_files: list = []

        self.setWindowTitle("Vehicle Test Analysis")
        self.setMinimumSize(1200, 800)

        self._init_menubar()
        self._init_toolbar()
        self._init_central_widget()
        self._init_statusbar()

        self.current_project_path: Optional[Path] = None

        if self._auth:
            QTimer.singleShot(100, self._update_ui_for_user)

    def _init_menubar(self) -> None:
        """Initialize menu bar."""
        menubar = self.menuBar()

        file_menu = menubar.addMenu("File")

        new_action = file_menu.addAction("New Project")
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self._on_new_project)

        open_action = file_menu.addAction("Open Project")
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._on_open_project)

        file_menu.addSeparator()

        import_action = file_menu.addAction("Import Data")
        import_action.setShortcut("Ctrl+I")
        import_action.triggered.connect(self._on_import_data)

        file_menu.addSeparator()

        self._logout_action = file_menu.addAction("Logout")
        self._logout_action.triggered.connect(self._on_logout)

        exit_action = file_menu.addAction("Exit")
        exit_action.setShortcut("Alt+F4")
        exit_action.triggered.connect(self.close)

        edit_menu = menubar.addMenu("Edit")

        settings_action = edit_menu.addAction("Settings")
        settings_action.triggered.connect(self._on_settings)

        self._user_menu = menubar.addMenu("User")
        self._create_user_action = self._user_menu.addAction("Create User")
        self._create_user_action.triggered.connect(self._on_create_user)
        self._create_user_action.setEnabled(False)

        analysis_menu = menubar.addMenu("Analysis")

        run_action = analysis_menu.addAction("Run Analysis")
        run_action.setShortcut("F5")
        run_action.triggered.connect(self._on_run_analysis)

        report_menu = menubar.addMenu("Report")

        generate_action = report_menu.addAction("Generate Report")
        generate_action.setShortcut("Ctrl+G")
        generate_action.triggered.connect(self._on_generate_report)

        help_menu = menubar.addMenu("Help")

        about_action = help_menu.addAction("About")
        about_action.triggered.connect(self._on_about)

    def _init_toolbar(self) -> None:
        """Initialize toolbar."""
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)

        toolbar.addAction("New", self._on_new_project)
        toolbar.addAction("Open", self._on_open_project)
        toolbar.addSeparator()
        toolbar.addAction("Import", self._on_import_data)
        toolbar.addAction("Analyze", self._on_run_analysis)
        toolbar.addSeparator()
        toolbar.addAction("Report", self._on_generate_report)

    def _init_central_widget(self) -> None:
        """Initialize central widget with tabs."""
        self.tab_widget = QTabWidget()

        self.project_tab = QWidget()
        self.data_tab = QWidget()
        self.analysis_tab = QWidget()
        self.report_tab = QWidget()

        self.tab_widget.addTab(self.project_tab, "Project")
        self.tab_widget.addTab(self.data_tab, "Data")
        self.tab_widget.addTab(self.analysis_tab, "Analysis")
        self.tab_widget.addTab(self.report_tab, "Report")

        self.project_tab.setLayout(
            self._create_placeholder_layout(
                "Project Management\n\nClick 'File -> New Project' to create"
            )
        )
        self.data_tab.setLayout(
            self._create_placeholder_layout(
                "Data Management\n\nImport data files to view here"
            )
        )
        self.analysis_tab.setLayout(
            self._create_placeholder_layout(
                "Analysis Results\n\nRun analysis to see results"
            )
        )
        self.report_tab.setLayout(
            self._create_placeholder_layout(
                "Report Generation\n\nGenerate reports after analysis"
            )
        )

        self.setCentralWidget(self.tab_widget)

    def _create_placeholder_layout(self, text: str):
        """Create a placeholder layout with centered text."""
        from PyQt6.QtWidgets import QVBoxLayout

        layout = QVBoxLayout()
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("font-size: 18px; color: #888;")
        layout.addWidget(label)
        return layout

    def _init_statusbar(self) -> None:
        """Initialize status bar."""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self.statusbar.showMessage("Ready")

    def _update_ui_for_user(self) -> None:
        """Update UI based on current user role."""
        if self._auth and self._auth.is_authenticated():
            session = self._auth.get_current_session()
            if session:
                self.statusbar.showMessage(f"User: {session.username} ({session.role})")
                if session.role == "admin":
                    self._create_user_action.setEnabled(True)

    def _on_new_project(self) -> None:
        """Handle new project action."""
        from src.ui.dialogs.project_dialog import ProjectDialog

        if not self._auth or not self._auth.is_authenticated():
            QMessageBox.warning(self, "Error", "Please login first")
            return

        session = self._auth.get_current_session()
        dialog = ProjectDialog(self._db, session.user_id, self)
        if dialog.exec():
            project = dialog.get_project()
            if project:
                self._current_project_id = project.id
                self.statusbar.showMessage(f"Created project: {project.name}")
                self._refresh_project_tab()

    def _on_open_project(self) -> None:
        """Handle open project action."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Project",
            "",
            "Project Files (*.vta);;All Files (*)",
        )
        if file_path:
            self.current_project_path = Path(file_path)
            self.statusbar.showMessage(f"Opened: {file_path}")

    def _on_import_data(self) -> None:
        """Handle import data action."""
        if not self._current_project_id:
            QMessageBox.warning(self, "Error", "Please create or open a project first")
            return

        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Import Data Files",
            "",
            "Supported Formats (*.blf *.asc *.mf4 *.mdf *.csv *.tdms);;BLF Files (*.blf);;MDF Files (*.mf4 *.mdf);;CSV Files (*.csv);;All Files (*)",
        )
        if file_paths:
            self._import_files(file_paths)

    def _import_files(self, file_paths: list) -> None:
        """Import data files into current project."""
        from pathlib import Path as PathLib
        import hashlib

        imported_count = 0
        errors = []

        for file_path in file_paths:
            path = PathLib(file_path)
            if not path.exists():
                errors.append(f"File not found: {file_path}")
                continue

            file_size = path.stat().st_size
            file_type = path.suffix.lower().lstrip(".")

            file_hash = hashlib.sha256()
            try:
                with open(path, "rb") as f:
                    for chunk in iter(lambda: f.read(8192), b""):
                        file_hash.update(chunk)
                file_hash_str = file_hash.hexdigest()
            except Exception:
                file_hash_str = None

            try:
                data_file = self._db.create_data_file(
                    project_id=self._current_project_id,
                    file_name=path.name,
                    file_path=str(path),
                    file_type=file_type,
                    file_size=file_size,
                    file_hash=file_hash_str,
                )
                self._imported_files.append(data_file)
                imported_count += 1
            except Exception as e:
                errors.append(f"Import failed {path.name}: {str(e)}")

        message = f"Successfully imported {imported_count} files"
        if errors:
            message += f"\nFailed {len(errors)}"
        self.statusbar.showMessage(message)

        if imported_count > 0:
            self._parse_imported_files()

    def _parse_imported_files(self) -> None:
        """Parse imported data files."""
        from src.parsers.can_parser import CANParser
        from src.parsers.mdf_parser import MDFParser
        from src.parsers.csv_parser import CSVParser

        for data_file in self._imported_files[-5:]:
            file_path = Path(data_file.file_path)
            file_type = data_file.file_type.lower()

            parser = None
            if file_type in ("blf", "asc"):
                parser = CANParser(file_path)
            elif file_type in ("mdf", "mf4", "dat"):
                parser = MDFParser(file_path)
            elif file_type in ("csv", "txt", "log"):
                parser = CSVParser(file_path)

            if parser:
                try:
                    result = parser.parse()
                    if result.is_success:
                        metadata = result.metadata or {}
                        with self._db.session() as session:
                            from src.database.models import DataFile

                            db_file = session.get(DataFile, data_file.id)
                            if db_file:
                                db_file.import_status = "parsed"
                                db_file.data_points = metadata.get("row_count")
                                db_file.signal_count = metadata.get("signal_count")
                                if "time_range" in metadata:
                                    db_file.time_range_start = metadata[
                                        "time_range"
                                    ].get("start")
                                    db_file.time_range_end = metadata["time_range"].get(
                                        "end"
                                    )

                        for signal_info in result.signals or []:
                            self._db.create_signal(
                                data_file_id=data_file.id,
                                name=signal_info.get("name", "unknown"),
                                data_type=signal_info.get("type", "float"),
                            )
                    else:
                        with self._db.session() as session:
                            from src.database.models import DataFile

                            db_file = session.get(DataFile, data_file.id)
                            if db_file:
                                db_file.import_status = "error"
                                db_file.error_message = result.error_message
                except Exception:
                    pass

    def _on_settings(self) -> None:
        """Handle settings action."""
        QMessageBox.information(self, "Settings", "Settings feature coming soon")

    def _on_create_user(self) -> None:
        """Handle create user action."""
        from src.ui.login_dialog import CreateUserDialog

        dialog = CreateUserDialog(self._auth, self)
        dialog.exec()

    def _on_logout(self) -> None:
        """Handle logout action."""
        if self._auth:
            self._auth.logout()
        self.close()

    def _on_run_analysis(self) -> None:
        """Handle run analysis action."""
        if not self._current_project_id:
            QMessageBox.warning(self, "Error", "Please create or open a project first")
            return

        if not self._imported_files:
            QMessageBox.warning(self, "Error", "Please import data files first")
            return

        from src.ui.dialogs.analysis_dialog import AnalysisDialog

        dialog = AnalysisDialog(self._db, self._current_project_id, self)
        if dialog.exec():
            self.statusbar.showMessage("Analysis completed")

    def _on_generate_report(self) -> None:
        """Handle generate report action."""
        if not self._current_project_id:
            QMessageBox.warning(self, "Error", "Please create or open a project first")
            return

        from src.ui.dialogs.report_dialog import ReportDialog

        session = self._auth.get_current_session() if self._auth else None
        user_id = session.user_id if session else 1

        dialog = ReportDialog(self._db, self._current_project_id, user_id, self)
        if dialog.exec():
            self.statusbar.showMessage("Report generated")

    def _on_about(self) -> None:
        """Handle about action."""
        QMessageBox.about(
            self,
            "About",
            "Vehicle Test Analysis System\n\n"
            "Version: 0.1.0\n\n"
            "Supports MIL/HIL/DVP/Vehicle test data analysis and report generation",
        )

    def _refresh_project_tab(self) -> None:
        """Refresh project tab with current project info."""
        if self._current_project_id:
            project = self._db.get_project(self._current_project_id)
            if project:
                info = f"Project: {project.name}\n"
                info += f"Phase: {project.test_phase}\n"
                info += f"Description: {project.description or 'None'}\n"
                info += f"Status: {project.status}"

                layout = self.project_tab.layout()
                if layout:
                    for i in range(layout.count()):
                        widget = layout.itemAt(i).widget()
                        if widget:
                            widget.deleteLater()

                label = QLabel(info)
                label.setAlignment(
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
                )
                label.setStyleSheet("font-size: 14px; padding: 20px;")
                layout.addWidget(label)
