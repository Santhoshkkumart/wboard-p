"""Launch the interactive whiteboard desktop application."""

import sys

try:
    from PySide6.QtWidgets import QApplication, QMessageBox
except ImportError as exc:
    raise SystemExit("PySide6 is required. Run: pip install -r requirements.txt") from exc

from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
