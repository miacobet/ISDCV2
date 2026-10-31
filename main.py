"""
main.py
=======
ISDC Decommissioning Cost Estimation Tool
Based on the NEA/OECD International Structure for Decommissioning Costing
of Nuclear Installations (ISDC 2012, NEA No. 7088).

Author: Marian
"""

import sys
import traceback

from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import Qt

from core.database import DatabaseManager
from gui.main_window import MainWindow

APP_STYLESHEET = """
QWidget { font-family: "Segoe UI", Arial, sans-serif; font-size: 12px; }
QMainWindow { background-color: #f4f6f9; }
QGroupBox {
    border: 1px solid #c3cfdd; border-radius: 4px; margin-top: 8px;
    padding-top: 10px; font-weight: bold; color: #1a3a5c;
}
QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; }
QPushButton {
    background-color: #2a5a8c; color: white; border: none;
    border-radius: 3px; padding: 6px 14px;
}
QPushButton:hover { background-color: #1a3a5c; }
QPushButton:pressed { background-color: #12283f; }
QTabWidget::pane { border: 1px solid #c3cfdd; background: white; }
QTabBar::tab {
    background: #e8eef5; padding: 7px 14px; border: 1px solid #c3cfdd;
    border-bottom: none; border-top-left-radius: 4px; border-top-right-radius: 4px;
}
QTabBar::tab:selected { background: white; font-weight: bold; color: #1a3a5c; }
QHeaderView::section {
    background-color: #1a3a5c; color: white; padding: 4px; border: none;
}
QTableWidget, QTreeWidget { gridline-color: #d8e0ea; }
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit, QPlainTextEdit {
    border: 1px solid #c3cfdd; border-radius: 3px; padding: 3px;
    background: white;
}
QLabel[desc="true"] { color: #5a7a9a; font-style: italic; font-size: 10px; }
"""


def handle_exception(exc_type, exc_value, exc_tb):
    """Global exception hook: show a dialog instead of letting PyQt abort()."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return
    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    print("UNHANDLED EXCEPTION:\n", error_msg)
    try:
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle("Application Error")
        msg.setText("An unexpected error occurred. Details below.")
        msg.setDetailedText(error_msg)
        msg.exec_()
    except Exception:
        pass


def main():
    sys.excepthook = handle_exception

    app = QApplication(sys.argv)
    app.setApplicationName("ISDC Decommissioning Cost Estimation Tool")
    app.setStyleSheet(APP_STYLESHEET)
    app.setAttribute(Qt.AA_EnableHighDpiScaling, True)

    db = DatabaseManager("isdc_tool.db")
    db.initialize()

    window = MainWindow(db)
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
