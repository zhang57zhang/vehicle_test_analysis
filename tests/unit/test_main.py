"""Unit tests for main.py entry point."""

import pytest
import sys
from unittest.mock import patch, MagicMock
from pathlib import Path

from src.main import main


class TestMain:
    """Tests for main() function."""

    def test_main_returns_zero(self):
        """Test that main() returns 0 (success)."""
        result = main([])
        assert result == 0

    def test_main_prints_message(self, capsys):
        """Test that main() prints expected messages."""
        main([])
        captured = capsys.readouterr()
        assert "Vehicle Test Analysis System" in captured.out

    def test_main_as_script_execution(self):
        """Test that main() can be called directly."""
        result = main([])
        assert isinstance(result, int)
        assert result >= 0

    def test_main_gui_flag(self):
        """Test that --gui flag triggers GUI mode."""
        with patch("src.main.main_gui") as mock_gui:
            mock_gui.return_value = 0
            result = main(["--gui"])
            mock_gui.assert_called_once()
            assert result == 0

    def test_main_skip_login_flag(self):
        """Test that --skip-login flag is recognized."""
        with patch("src.main.main_gui") as mock_gui:
            mock_gui.return_value = 0
            result = main(["--gui", "--skip-login"])
            mock_gui.assert_called_once_with(skip_login=True)
            assert result == 0


class TestMainGui:
    """Tests for main_gui() function."""

    def test_main_gui_imports_successfully(self):
        """Test that main_gui can be imported."""
        from src.main import main_gui

        assert callable(main_gui)


class TestModuleStructure:
    """Tests for module structure and imports."""

    def test_main_function_exists(self):
        """Test that main function is importable."""
        from src.main import main

        assert callable(main)

    def test_main_gui_function_exists(self):
        """Test that main_gui function is importable."""
        from src.main import main_gui

        assert callable(main_gui)

    def test_module_docstring(self):
        """Test that module has docstring."""
        import src.main as main_module

        assert main_module.__doc__ is not None
        assert "Vehicle Test Analysis" in main_module.__doc__


class TestPathSetup:
    """Tests for path setup in main.py."""

    def test_project_root_exists(self):
        """Test that project_root is defined."""
        from src.main import project_root

        assert project_root is not None
        assert isinstance(project_root, Path)

    def test_project_root_is_valid_path(self):
        """Test that project_root points to a valid directory."""
        from src.main import project_root

        assert project_root.exists() or project_root.parent.exists()

    def test_sys_path_contains_project_root(self):
        """Test that project root is added to sys.path."""
        from src.main import project_root

        str_root = str(project_root)
        assert str_root in sys.path
