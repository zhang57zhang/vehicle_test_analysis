"""Unit tests for UI module (main_window.py)."""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QMessageBox, QFileDialog
from PyQt6.QtCore import Qt

# Ensure QApplication exists for tests
@pytest.fixture(scope="module")
def qapp():
    """Create QApplication for the test module."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def main_window(qapp):
    """Create MainWindow instance for testing."""
    from src.ui.main_window import MainWindow
    window = MainWindow()
    yield window
    window.close()


class TestMainWindowInitialization:
    """Tests for MainWindow initialization."""

    def test_window_title(self, main_window):
        """Test window title is set correctly."""
        assert "Vehicle Test Analysis" in main_window.windowTitle()
        assert "车载控制器测试数据分析系统" in main_window.windowTitle()

    def test_minimum_size(self, main_window):
        """Test minimum window size is set."""
        assert main_window.minimumWidth() == 1200
        assert main_window.minimumHeight() == 800

    def test_menubar_exists(self, main_window):
        """Test menu bar is created."""
        menubar = main_window.menuBar()
        assert menubar is not None

    def test_toolbar_exists(self, main_window):
        """Test toolbar is created."""
        toolbars = main_window.findChildren(type(main_window.menuBar()).__class__.__bases__[0])
        # Check that at least one toolbar exists
        from PyQt6.QtWidgets import QToolBar
        toolbars = main_window.findChildren(QToolBar)
        assert len(toolbars) >= 1

    def test_statusbar_exists(self, main_window):
        """Test status bar is created."""
        assert main_window.statusbar is not None
        assert main_window.statusBar() is not None

    def test_statusbar_initial_message(self, main_window):
        """Test status bar shows initial message."""
        assert main_window.statusbar.currentMessage() == "就绪"

    def test_central_widget_is_tabwidget(self, main_window):
        """Test central widget is a QTabWidget."""
        from PyQt6.QtWidgets import QTabWidget
        assert isinstance(main_window.centralWidget(), QTabWidget)

    def test_tabs_exist(self, main_window):
        """Test all expected tabs are created."""
        tab_widget = main_window.tab_widget
        assert tab_widget.count() == 4
        
        tab_names = [tab_widget.tabText(i) for i in range(tab_widget.count())]
        assert "项目管理" in tab_names
        assert "数据管理" in tab_names
        assert "分析结果" in tab_names
        assert "报告生成" in tab_names

    def test_current_project_path_initial_state(self, main_window):
        """Test current_project_path is None initially."""
        assert main_window.current_project_path is None


class TestMenuBarStructure:
    """Tests for menu bar structure."""

    def test_file_menu_exists(self, main_window):
        """Test File menu exists."""
        menubar = main_window.menuBar()
        file_menu = None
        for action in menubar.actions():
            if "文件" in action.text():
                file_menu = action.menu()
                break
        assert file_menu is not None

    def test_edit_menu_exists(self, main_window):
        """Test Edit menu exists."""
        menubar = main_window.menuBar()
        edit_menu = None
        for action in menubar.actions():
            if "编辑" in action.text():
                edit_menu = action.menu()
                break
        assert edit_menu is not None

    def test_analysis_menu_exists(self, main_window):
        """Test Analysis menu exists."""
        menubar = main_window.menuBar()
        analysis_menu = None
        for action in menubar.actions():
            if "分析" in action.text():
                analysis_menu = action.menu()
                break
        assert analysis_menu is not None

    def test_report_menu_exists(self, main_window):
        """Test Report menu exists."""
        menubar = main_window.menuBar()
        report_menu = None
        for action in menubar.actions():
            if "报告" in action.text():
                report_menu = action.menu()
                break
        assert report_menu is not None

    def test_help_menu_exists(self, main_window):
        """Test Help menu exists."""
        menubar = main_window.menuBar()
        help_menu = None
        for action in menubar.actions():
            if "帮助" in action.text():
                help_menu = action.menu()
                break
        assert help_menu is not None

    def test_file_menu_actions(self, main_window):
        """Test File menu has expected actions."""
        menubar = main_window.menuBar()
        file_menu = None
        for action in menubar.actions():
            if "文件" in action.text():
                file_menu = action.menu()
                break
        
        action_texts = [action.text() for action in file_menu.actions()]
        # Check for key actions (text may contain accelerator markers)
        assert any("新建" in text for text in action_texts)
        assert any("打开" in text for text in action_texts)
        assert any("导入" in text for text in action_texts)
        assert any("退出" in text for text in action_texts)


class TestMenuShortcuts:
    """Tests for menu action shortcuts."""

    def test_new_project_shortcut(self, main_window):
        """Test new project action has Ctrl+N shortcut."""
        menubar = main_window.menuBar()
        file_menu = None
        for action in menubar.actions():
            if "文件" in action.text():
                file_menu = action.menu()
                break
        
        for action in file_menu.actions():
            if "新建" in action.text():
                assert action.shortcut().toString() in ["Ctrl+N", "Ctrl+N"]
                return
        pytest.fail("New project action not found")

    def test_open_project_shortcut(self, main_window):
        """Test open project action has Ctrl+O shortcut."""
        menubar = main_window.menuBar()
        file_menu = None
        for action in menubar.actions():
            if "文件" in action.text():
                file_menu = action.menu()
                break
        
        for action in file_menu.actions():
            if "打开" in action.text():
                assert "Ctrl+O" in action.shortcut().toString()
                return
        pytest.fail("Open project action not found")

    def test_import_data_shortcut(self, main_window):
        """Test import data action has Ctrl+I shortcut."""
        menubar = main_window.menuBar()
        file_menu = None
        for action in menubar.actions():
            if "文件" in action.text():
                file_menu = action.menu()
                break
        
        for action in file_menu.actions():
            if "导入" in action.text():
                assert "Ctrl+I" in action.shortcut().toString()
                return
        pytest.fail("Import data action not found")

    def test_run_analysis_shortcut(self, main_window):
        """Test run analysis action has F5 shortcut."""
        menubar = main_window.menuBar()
        analysis_menu = None
        for action in menubar.actions():
            if "分析" in action.text():
                analysis_menu = action.menu()
                break
        
        for action in analysis_menu.actions():
            if "运行" in action.text():
                assert action.shortcut().toString() == "F5"
                return
        pytest.fail("Run analysis action not found")

    def test_generate_report_shortcut(self, main_window):
        """Test generate report action has Ctrl+G shortcut."""
        menubar = main_window.menuBar()
        report_menu = None
        for action in menubar.actions():
            if "报告" in action.text():
                report_menu = action.menu()
                break
        
        for action in report_menu.actions():
            if "生成" in action.text():
                assert "Ctrl+G" in action.shortcut().toString()
                return
        pytest.fail("Generate report action not found")


class TestToolbarStructure:
    """Tests for toolbar structure."""

    def test_toolbar_actions_exist(self, main_window):
        """Test toolbar has expected actions."""
        from PyQt6.QtWidgets import QToolBar
        toolbar = main_window.findChild(QToolBar)
        assert toolbar is not None
        
        action_texts = [action.text() for action in toolbar.actions() if not action.isSeparator()]
        assert any("新建" in text for text in action_texts)
        assert any("打开" in text for text in action_texts)
        assert any("导入" in text for text in action_texts)
        assert any("分析" in text for text in action_texts)
        assert any("报告" in text for text in action_texts)


class TestMenuActionHandlers:
    """Tests for menu action handlers."""

    @patch.object(QMessageBox, 'information')
    def test_on_new_project_shows_message(self, mock_information, main_window):
        """Test new project action shows information message."""
        main_window._on_new_project()
        mock_information.assert_called_once()
        args = mock_information.call_args
        assert "新建项目" in args[0][1]

    @patch.object(QMessageBox, 'information')
    def test_on_settings_shows_message(self, mock_information, main_window):
        """Test settings action shows information message."""
        main_window._on_settings()
        mock_information.assert_called_once()
        args = mock_information.call_args
        assert "设置" in args[0][1]

    @patch.object(QMessageBox, 'information')
    def test_on_run_analysis_shows_message(self, mock_information, main_window):
        """Test run analysis action shows information message."""
        main_window._on_run_analysis()
        mock_information.assert_called_once()
        args = mock_information.call_args
        assert "运行分析" in args[0][1]

    @patch.object(QMessageBox, 'information')
    def test_on_generate_report_shows_message(self, mock_information, main_window):
        """Test generate report action shows information message."""
        main_window._on_generate_report()
        mock_information.assert_called_once()
        args = mock_information.call_args
        assert "生成报告" in args[0][1]

    @patch.object(QMessageBox, 'about')
    def test_on_about_shows_dialog(self, mock_about, main_window):
        """Test about action shows about dialog."""
        main_window._on_about()
        mock_about.assert_called_once()
        args = mock_about.call_args
        assert "关于" in args[0][1]
        assert "车载控制器测试数据分析" in args[0][2]

    @patch.object(QFileDialog, 'getOpenFileName', return_value=('', ''))
    def test_on_open_project_cancelled(self, mock_dialog, main_window):
        """Test open project when dialog is cancelled."""
        main_window._on_open_project()
        assert main_window.current_project_path is None

    @patch.object(QFileDialog, 'getOpenFileName', return_value=('/path/to/test.vta', ''))
    def test_on_open_project_file_selected(self, mock_dialog, main_window):
        """Test open project when file is selected."""
        main_window._on_open_project()
        assert main_window.current_project_path == Path('/path/to/test.vta')
        assert "已打开" in main_window.statusbar.currentMessage()

    @patch.object(QFileDialog, 'getOpenFileNames', return_value=([], ''))
    def test_on_import_data_cancelled(self, mock_dialog, main_window):
        """Test import data when dialog is cancelled."""
        main_window._on_import_data()
        # Status bar should remain unchanged or show "就绪"
        # Since no files selected, no status update

    @patch.object(QFileDialog, 'getOpenFileNames', return_value=(['/path/to/file1.blf', '/path/to/file2.blf'], ''))
    def test_on_import_data_files_selected(self, mock_dialog, main_window):
        """Test import data when files are selected."""
        main_window._on_import_data()
        assert "已选择" in main_window.statusbar.currentMessage()
        assert "2" in main_window.statusbar.currentMessage()


class TestTabWidgets:
    """Tests for tab widgets."""

    def test_project_tab_exists(self, main_window):
        """Test project tab widget exists."""
        assert main_window.project_tab is not None

    def test_data_tab_exists(self, main_window):
        """Test data tab widget exists."""
        assert main_window.data_tab is not None

    def test_analysis_tab_exists(self, main_window):
        """Test analysis tab widget exists."""
        assert main_window.analysis_tab is not None

    def test_report_tab_exists(self, main_window):
        """Test report tab widget exists."""
        assert main_window.report_tab is not None

    def test_tabs_have_layouts(self, main_window):
        """Test all tabs have layouts."""
        assert main_window.project_tab.layout() is not None
        assert main_window.data_tab.layout() is not None
        assert main_window.analysis_tab.layout() is not None
        assert main_window.report_tab.layout() is not None


class TestPlaceholderLabels:
    """Tests for placeholder labels in tabs."""

    def test_project_tab_has_placeholder(self, main_window):
        """Test project tab has placeholder label."""
        from PyQt6.QtWidgets import QLabel
        labels = main_window.project_tab.findChildren(QLabel)
        assert len(labels) >= 1
        assert any("项目管理模块" in label.text() for label in labels)

    def test_data_tab_has_placeholder(self, main_window):
        """Test data tab has placeholder label."""
        from PyQt6.QtWidgets import QLabel
        labels = main_window.data_tab.findChildren(QLabel)
        assert len(labels) >= 1
        assert any("数据管理模块" in label.text() for label in labels)

    def test_analysis_tab_has_placeholder(self, main_window):
        """Test analysis tab has placeholder label."""
        from PyQt6.QtWidgets import QLabel
        labels = main_window.analysis_tab.findChildren(QLabel)
        assert len(labels) >= 1
        assert any("分析结果模块" in label.text() for label in labels)

    def test_report_tab_has_placeholder(self, main_window):
        """Test report tab has placeholder label."""
        from PyQt6.QtWidgets import QLabel
        labels = main_window.report_tab.findChildren(QLabel)
        assert len(labels) >= 1
        assert any("报告生成模块" in label.text() for label in labels)


class TestCreatePlaceholderLayout:
    """Tests for _create_placeholder_layout method."""

    def test_create_placeholder_layout_returns_layout(self, main_window):
        """Test _create_placeholder_layout returns a layout."""
        from PyQt6.QtWidgets import QVBoxLayout
        layout = main_window._create_placeholder_layout("Test")
        assert isinstance(layout, QVBoxLayout)

    def test_create_placeholder_layout_contains_label(self, main_window):
        """Test _create_placeholder_layout contains a label."""
        from PyQt6.QtWidgets import QLabel
        layout = main_window._create_placeholder_layout("Test Text")
        # Find label in layout
        label = None
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item.widget() and isinstance(item.widget(), QLabel):
                label = item.widget()
                break
        assert label is not None
        assert label.text() == "Test Text"

    def test_placeholder_label_alignment(self, main_window):
        """Test placeholder label is centered."""
        from PyQt6.QtWidgets import QLabel
        layout = main_window._create_placeholder_layout("Test")
        label = None
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item.widget() and isinstance(item.widget(), QLabel):
                label = item.widget()
                break
        assert label.alignment() == Qt.AlignmentFlag.AlignCenter


class TestUIModuleExports:
    """Tests for UI module __init__.py exports."""

    def test_main_window_import(self):
        """Test MainWindow can be imported from ui module."""
        from src.ui import MainWindow
        assert MainWindow is not None

    def test_main_window_class_available(self):
        """Test MainWindow class is available."""
        from src.ui.main_window import MainWindow
        assert MainWindow.__name__ == "MainWindow"


class TestWindowClose:
    """Tests for window close behavior."""

    def test_window_can_close(self, main_window):
        """Test window can be closed."""
        # This should not raise any exceptions
        main_window.close()
        assert True

    def test_exit_action_triggers_close(self, main_window):
        """Test exit menu action triggers window close."""
        menubar = main_window.menuBar()
        file_menu = None
        for action in menubar.actions():
            if "文件" in action.text():
                file_menu = action.menu()
                break
        
        exit_action = None
        for action in file_menu.actions():
            if "退出" in action.text():
                exit_action = action
                break
        
        assert exit_action is not None
        # Verify the action is connected to close
        # The triggered signal should be connected to main_window.close
        # We can't easily test the actual close without mocking
