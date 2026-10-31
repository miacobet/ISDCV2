"""
main.py
=======
ISDC Decommissioning Cost Estimation Tool
Uses the cost item hierarchy of the NEA/OECD International Structure for
Decommissioning Costing of Nuclear Installations (ISDC 2012, NEA No. 7088).

Author: Marian
"""

import sys
import traceback

from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import Qt

from core.database import DatabaseManager
from gui.main_window import MainWindow

APP_STYLESHEET = """
QWidget { font-family: "Segoe UI", Arial, sans-serif; font-size: 14px; }
QMainWindow { background-color: #f4f6f9; }
QGroupBox {
    border: 1px solid #c3cfdd; border-radius: 4px; margin-top: 8px;
    padding-top: 10px; font-weight: bold; color: #1a3a5c;
}
QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; }
QPushButton {
    background-color: #2a5a8c; color: white; border: none;
    border-radius: 3px; padding: 7px 16px;
}
QPushButton:hover { background-color: #1a3a5c; }
QPushButton:pressed { background-color: #12283f; }
QPushButton:focus { outline: none; border: 2px solid #ffb400; }
QTabWidget::pane { border: 1px solid #c3cfdd; background: white; }
QTabBar::tab {
    background: #e8eef5; padding: 8px 18px; min-width: 90px;
    border: 1px solid #c3cfdd; border-top: 3px solid #c3cfdd;
    border-bottom: none; border-top-left-radius: 4px; border-top-right-radius: 4px;
}
/* Selected tab: no bold font (Qt sizes tabs for the normal font, so bold text
   gets clipped); highlight with colour and a top accent of the same thickness. */
QTabBar::tab:selected { background: white; color: #1a3a5c; border-top: 3px solid #2a5a8c; }
QTabBar::tab:hover:!selected { background: #dde6f0; }
QHeaderView::section {
    background-color: #1a3a5c; color: white; padding: 5px; border: none;
}
QTableWidget, QTreeWidget { gridline-color: #d8e0ea; }

QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit, QPlainTextEdit {
    border: 1px solid #c3cfdd; border-radius: 3px; padding: 4px;
    background: white; color: #1a1a1a;
}
QComboBox QAbstractItemView::item { color: #1a1a1a; padding: 4px; }
QComboBox QAbstractItemView::item:selected { color: white; background: #2a5a8c; }
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus,
QTextEdit:focus, QPlainTextEdit:focus {
    border: 2px solid #2a5a8c;
}

/* --- Spin box up/down buttons: the stylesheet above switches Qt into
   "styled" rendering, which otherwise hides the native increment/decrement
   glyphs. Redraw them explicitly as simple triangles so they stay visible
   on every platform. --- */
QSpinBox::up-button, QDoubleSpinBox::up-button {
    subcontrol-origin: border; subcontrol-position: top right;
    width: 18px; border-left: 1px solid #c3cfdd; border-bottom: 1px solid #c3cfdd;
    background: #e8eef5; border-top-right-radius: 3px;
}
QSpinBox::down-button, QDoubleSpinBox::down-button {
    subcontrol-origin: border; subcontrol-position: bottom right;
    width: 18px; border-left: 1px solid #c3cfdd; border-top: 1px solid #c3cfdd;
    background: #e8eef5; border-bottom-right-radius: 3px;
}
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
    background: #c3cfdd;
}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {
    width: 0; height: 0;
    border-left: 4px solid transparent; border-right: 4px solid transparent;
    border-bottom: 6px solid #1a3a5c;
}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
    width: 0; height: 0;
    border-left: 4px solid transparent; border-right: 4px solid transparent;
    border-top: 6px solid #1a3a5c;
}
QSpinBox::up-arrow:disabled, QDoubleSpinBox::up-arrow:disabled,
QSpinBox::down-arrow:disabled, QDoubleSpinBox::down-arrow:disabled {
    border-bottom-color: #b0b8c0; border-top-color: #b0b8c0;
}

/* --- Combo box dropdown arrow: same issue as the spin boxes above. --- */
QComboBox::drop-down {
    subcontrol-origin: padding; subcontrol-position: top right;
    width: 22px; border-left: 1px solid #c3cfdd;
}
QComboBox::down-arrow {
    width: 0; height: 0;
    border-left: 5px solid transparent; border-right: 5px solid transparent;
    border-top: 6px solid #1a3a5c;
    margin-right: 6px;
}
QComboBox QAbstractItemView {
    border: 1px solid #c3cfdd; background: white; selection-background-color: #2a5a8c;
    selection-color: white;
}

QLabel[desc="true"] { color: #5a7a9a; font-style: italic; font-size: 11px; }
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

    # High-DPI attributes must be set before the QApplication is created.
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("ISDC Decommissioning Cost Estimation Tool")
    app.setStyleSheet(APP_STYLESHEET)

    db = DatabaseManager("isdc_tool.db")
    db.initialize()

    window = MainWindow(db)
    window.show()

    if db.last_migration:
        m = db.last_migration
        QMessageBox.information(
            window, "Updated to the ISDC 2012 structure",
            "Your projects were converted to the official ISDC 2012 cost structure "
            "(NEA No. 7088, Appendix A).\n\n"
            f"Cost entries converted: {m['entries']} (combined where several old items map to one "
            f"ISDC item: {m['merged']}).\n"
            f"Applicability ratings carried over: {m['overrides']}.\n\n"
            "Each converted entry notes its old code. Former contingency items were moved to the "
            "Contingency cost category; former income items were moved to 11.04 Asset recovery "
            "(enter income as negative amounts).\n\n"
            f"A backup of the previous database was saved as:\n{m['backup'] or '(not saved)'}"
        )

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()