"""
Vehicle Test Analysis - Main Entry Point
========================================
"""

import argparse
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def main(argv: list | None = None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(
        description="Vehicle Test Analysis System"
    )
    parser.add_argument(
        "--gui", "-g",
        action="store_true",
        help="Launch graphical interface"
    )
    
    args = parser.parse_args(argv)
    
    if args.gui:
        return main_gui()
    
    print("Vehicle Test Analysis System")
    print("Use --gui or -g to launch the graphical interface.")
    return 0


def main_gui() -> int:
    """GUI entry point."""
    from PyQt6.QtWidgets import QApplication

    from src.ui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("Vehicle Test Analysis")
    app.setApplicationVersion("0.1.0")

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
