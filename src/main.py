# -*- coding: utf-8 -*-
"""
Vehicle Test Analysis - Main Entry Point
========================================
"""

import argparse
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def main(argv: list | None = None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description="Vehicle Test Analysis System")
    parser.add_argument(
        "--gui", "-g", action="store_true", help="Launch graphical interface"
    )
    parser.add_argument(
        "--skip-login", action="store_true", help="Skip login screen (for development)"
    )

    args = parser.parse_args(argv)

    if args.gui:
        return main_gui(skip_login=args.skip_login)

    print("Vehicle Test Analysis System")
    print("Use --gui or -g to launch the graphical interface.")
    return 0


def main_gui(skip_login: bool = False) -> int:
    """GUI entry point."""
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    app.setApplicationName("Vehicle Test Analysis")
    app.setApplicationVersion("0.1.0")

    from src.database.operations import DatabaseManager
    from src.core.auth import AuthService
    from src.ui.login_dialog import LoginDialog
    from src.ui.main_window import MainWindow

    db_path = project_root / "database" / "vehicle_test.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    db_manager = DatabaseManager(f"sqlite:///{db_path}")
    db_manager.initialize()

    _ensure_admin_user(db_manager)

    auth_service = AuthService(db_manager)

    if not skip_login:
        login_dialog = LoginDialog(auth_service)
        if login_dialog.exec() != LoginDialog.DialogCode.Accepted:
            return 0

    window = MainWindow(db_manager, auth_service)
    window.show()

    return app.exec()


def _ensure_admin_user(db_manager) -> None:
    """Ensure admin user exists."""
    from src.core.auth import AuthService

    existing = db_manager.get_user_by_username("admin")
    if existing is None:
        auth = AuthService(db_manager)
        auth.create_user(
            username="admin",
            password="admin123",
            email="admin@example.com",
            full_name="Administrator",
            role="admin",
        )


if __name__ == "__main__":
    sys.exit(main())
