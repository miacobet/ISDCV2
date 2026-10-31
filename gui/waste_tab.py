"""
gui/waste_tab.py
=================
Tab 4 — Waste Streams. Records estimated waste streams classified per
the IAEA GSG-1 waste classification scheme.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHeaderView, QDialog, QMessageBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from core.database import DatabaseManager
from core.calculator import WASTE_CLASS_LABELS
from gui.dialogs import WasteStreamDialog


class WasteTab(QWidget):
    def __init__(self, db: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db = db
        self.main_window = parent
        self.project_id = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title = QLabel("Waste Streams")
        title.setFont(QFont("Arial", 11, QFont.Bold))
        title.setStyleSheet("color: #1a3a5c;")
        layout.addWidget(title)

        note = QLabel(
            "Waste streams classified per the IAEA General Safety Guide GSG-1 scheme: "
            "HLW / ILW / LLW / VLLW / VSLW / EW."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #5a7a9a; font-size: 10px; font-style: italic;")
        layout.addWidget(note)

        btn_row = QHBoxLayout()
        btn_add = QPushButton("Add Waste Stream")
        btn_add.clicked.connect(self._on_add)
        btn_edit = QPushButton("Edit")
        btn_edit.clicked.connect(self._on_edit)
        btn_del = QPushButton("Delete")
        btn_del.clicked.connect(self._on_delete)
        btn_del.setStyleSheet("background-color:#7a3030;")
        btn_row.addWidget(btn_add)
        btn_row.addWidget(btn_edit)
        btn_row.addWidget(btn_del)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["Class", "Description", "Volume (m3)", "Activity / Characterisation", "Destination"]
        )
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

        self.lbl_summary = QLabel("")
        self.lbl_summary.setStyleSheet("font-family: Menlo, Consolas, \"Courier New\", monospace; font-size: 11px;")
        layout.addWidget(self.lbl_summary)

    def load_project(self, project_id: int):
        self.project_id = project_id
        self._refresh()

    def _refresh(self):
        streams = self.db.get_waste_streams(self.project_id)
        self.table.setRowCount(0)
        totals = {}
        for ws in streams:
            row = self.table.rowCount()
            self.table.insertRow(row)
            values = [
                ws["waste_class"], ws.get("description") or "",
                f"{ws.get('volume_m3') or 0:,.2f}",
                ws.get("activity_notes") or "", ws.get("destination") or "",
            ]
            for col, val in enumerate(values):
                it = QTableWidgetItem(str(val))
                it.setData(Qt.UserRole, ws["id"])
                self.table.setItem(row, col, it)
            totals[ws["waste_class"]] = totals.get(ws["waste_class"], 0.0) + (ws.get("volume_m3") or 0)

        lines = ["Volume summary by class:"]
        for cls, label in WASTE_CLASS_LABELS.items():
            vol = totals.get(cls, 0.0)
            if vol:
                lines.append(f"  {cls} ({label}): {vol:,.2f} m3")
        self.lbl_summary.setText("\n".join(lines) if len(lines) > 1 else "No waste streams defined yet.")

    def _get_selected_id(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return item.data(Qt.UserRole) if item else None

    def _on_add(self):
        dlg = WasteStreamDialog(self.project_id, parent=self)
        if dlg.exec_() == QDialog.Accepted:
            self.db.save_waste_stream(dlg.get_data())
            self._refresh()

    def _on_edit(self):
        wid = self._get_selected_id()
        if not wid:
            QMessageBox.information(self, "No selection", "Select a waste stream to edit.")
            return
        streams = self.db.get_waste_streams(self.project_id)
        existing = next((dict(w) for w in streams if w["id"] == wid), None)
        dlg = WasteStreamDialog(self.project_id, existing, parent=self)
        if dlg.exec_() == QDialog.Accepted:
            self.db.save_waste_stream(dlg.get_data())
            self._refresh()

    def _on_delete(self):
        wid = self._get_selected_id()
        if not wid:
            QMessageBox.information(self, "No selection", "Select a waste stream to delete.")
            return
        reply = QMessageBox.question(
            self, "Confirm", "Delete this waste stream?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.db.delete_waste_stream(wid)
            self._refresh()
