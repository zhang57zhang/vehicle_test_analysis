"""
Main window for the Vehicle Test Analysis application.
"""

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt
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

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize main window."""
        super().__init__(parent)

        self.setWindowTitle("Vehicle Test Analysis - 车载控制器测试数据分析系统")
        self.setMinimumSize(1200, 800)

        # Initialize UI components
        self._init_menubar()
        self._init_toolbar()
        self._init_central_widget()
        self._init_statusbar()

        # State
        self.current_project_path: Optional[Path] = None

    def _init_menubar(self) -> None:
        """Initialize menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("文件(&F)")

        new_action = file_menu.addAction("新建项目(&N)")
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self._on_new_project)

        open_action = file_menu.addAction("打开项目(&O)")
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._on_open_project)

        file_menu.addSeparator()

        import_action = file_menu.addAction("导入数据(&I)")
        import_action.setShortcut("Ctrl+I")
        import_action.triggered.connect(self._on_import_data)

        file_menu.addSeparator()

        exit_action = file_menu.addAction("退出(&X)")
        exit_action.setShortcut("Alt+F4")
        exit_action.triggered.connect(self.close)

        # Edit menu
        edit_menu = menubar.addMenu("编辑(&E)")

        settings_action = edit_menu.addAction("设置(&S)")
        settings_action.triggered.connect(self._on_settings)

        # Analysis menu
        analysis_menu = menubar.addMenu("分析(&A)")

        run_action = analysis_menu.addAction("运行分析(&R)")
        run_action.setShortcut("F5")
        run_action.triggered.connect(self._on_run_analysis)

        # Report menu
        report_menu = menubar.addMenu("报告(&R)")

        generate_action = report_menu.addAction("生成报告(&G)")
        generate_action.setShortcut("Ctrl+G")
        generate_action.triggered.connect(self._on_generate_report)

        # Help menu
        help_menu = menubar.addMenu("帮助(&H)")

        about_action = help_menu.addAction("关于(&A)")
        about_action.triggered.connect(self._on_about)

    def _init_toolbar(self) -> None:
        """Initialize toolbar."""
        toolbar = QToolBar("主工具栏")
        self.addToolBar(toolbar)

        toolbar.addAction("新建")
        toolbar.addAction("打开")
        toolbar.addSeparator()
        toolbar.addAction("导入")
        toolbar.addAction("分析")
        toolbar.addSeparator()
        toolbar.addAction("报告")

    def _init_central_widget(self) -> None:
        """Initialize central widget with tabs."""
        self.tab_widget = QTabWidget()

        # Create tabs
        self.project_tab = QWidget()
        self.data_tab = QWidget()
        self.analysis_tab = QWidget()
        self.report_tab = QWidget()

        self.tab_widget.addTab(self.project_tab, "项目管理")
        self.tab_widget.addTab(self.data_tab, "数据管理")
        self.tab_widget.addTab(self.analysis_tab, "分析结果")
        self.tab_widget.addTab(self.report_tab, "报告生成")

        # Placeholder labels
        self.project_tab.setLayout(self._create_placeholder_layout("项目管理模块"))
        self.data_tab.setLayout(self._create_placeholder_layout("数据管理模块"))
        self.analysis_tab.setLayout(self._create_placeholder_layout("分析结果模块"))
        self.report_tab.setLayout(self._create_placeholder_layout("报告生成模块"))

        self.setCentralWidget(self.tab_widget)

    def _create_placeholder_layout(self, text: str):
        """Create a placeholder layout with centered text."""
        from PyQt6.QtWidgets import QVBoxLayout

        layout = QVBoxLayout()
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("font-size: 24px; color: #888;")
        layout.addWidget(label)
        return layout

    def _init_statusbar(self) -> None:
        """Initialize status bar."""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self.statusbar.showMessage("就绪")

    # Menu action handlers
    def _on_new_project(self) -> None:
        """Handle new project action."""
        # TODO: Implement project creation dialog
        QMessageBox.information(self, "新建项目", "新建项目功能待实现")

    def _on_open_project(self) -> None:
        """Handle open project action."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "打开项目",
            "",
            "项目文件 (*.vta);;所有文件 (*)",
        )
        if file_path:
            self.current_project_path = Path(file_path)
            self.statusbar.showMessage(f"已打开: {file_path}")

    def _on_import_data(self) -> None:
        """Handle import data action."""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "导入数据文件",
            "",
            "支持的格式 (*.blf *.asc *.mf4 *.mdf *.csv *.tdms);;所有文件 (*)",
        )
        if file_paths:
            self.statusbar.showMessage(f"已选择 {len(file_paths)} 个文件")
            # TODO: Implement data import

    def _on_settings(self) -> None:
        """Handle settings action."""
        QMessageBox.information(self, "设置", "设置功能待实现")

    def _on_run_analysis(self) -> None:
        """Handle run analysis action."""
        QMessageBox.information(self, "运行分析", "分析功能待实现")

    def _on_generate_report(self) -> None:
        """Handle generate report action."""
        QMessageBox.information(self, "生成报告", "报告生成功能待实现")

    def _on_about(self) -> None:
        """Handle about action."""
        QMessageBox.about(
            self,
            "关于",
            "车载控制器测试数据分析与测试报告编写系统\n\n"
            "版本: 0.1.0\n\n"
            "支持 MIL/HIL/DVP/整车测试的数据分析与报告生成",
        )
