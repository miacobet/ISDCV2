"""
gui/phases_tab.py
=================
Tab 3 — Phases & Timeline.
Defines user-specified project phases with start/end years.
Phases drive NPV and escalation calculations and cost allocation in the matrix.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QGroupBox, QHeaderView, QDialog, QMessageBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor

from core.database import DatabaseManager
from core.calculator import ISDCCalculator
from gui.dialogs import PhaseDialog


class PhasesTab(QWidget):
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

        title = QLabel("Phases & Timeline")
        title.setFont(QFont("Arial", 11, QFont.Bold))
        title.setStyleSheet("color: #1a3a5c;")
        layout.addWidget(title)

        note = QLabel(
            "Define decommissioning project phases. Phases are used for cost allocation and "
            "NPV / escalation calculations. Conservation-period phases should be typed "
            "'Conservation'."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #5a7a9a; font-size: 10px; font-style: italic;")
        layout.addWidget(note)

        btn_row = QHBoxLayout()
        btn_add = QPushButton("Add Phase")
        btn_add.clicked.connect(self._on_add)
        btn_edit = QPushButton("Edit Phase")
        btn_edit.clicked.connect(self._on_edit)
        btn_del = QPushButton("Delete Phase")
        btn_del.clicked.connect(self._on_delete)
        btn_del.setStyleSheet("background-color:#7a3030;")
        btn_row.addWidget(btn_add)
        btn_row.addWidget(btn_edit)
        btn_row.addWidget(btn_del)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Phase Name", "Type", "Start Year", "End Year", "Duration (years)", "Sort Order"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

        grp_profile = QGroupBox("Phase Cost Profile (base-year EUR)")
        profile_layout = QVBoxLayout(grp_profile)
        self.lbl_profile = QLabel("Load project to view phase cost profile.")
        self.lbl_profile.setWordWrap(True)
        self.lbl_profile.setStyleSheet("font-size: 11px; font-family: Menlo, Consolas, \"Courier New\", monospace;")
        profile_layout.addWidget(self.lbl_profile)
        layout.addWidget(grp_profile)

    def load_project(self, project_id: int):
        self.project_id = project_id
        self._refresh()

    def _refresh(self):
        phases = self.db.get_phases(self.project_id)
        self.table.setRowCount(0)
        for ph in phases:
            row = self.table.rowCount()
            self.table.insertRow(row)
            dur = ph["end_year"] - ph["start_year"]
            items = [
                ph["phase_name"], ph["phase_type"],
                str(ph["start_year"]), str(ph["end_year"]),
                str(dur), str(ph["sort_order"])
            ]
            for col, val in enumerate(items):
                it = QTableWidgetItem(val)
                it.setData(Qt.UserRole, ph["id"])
                it.setTextAlignment(Qt.AlignCenter if col > 1 else Qt.AlignLeft | Qt.AlignVCenter)
                self.table.setItem(row, col, it)
            if ph["phase_type"] == "Conservation":
                for col in range(6):
                    self.table.item(row, col).setBackground(QColor("#fff3cd"))

        self._refresh_profile()

    def _refresh_profile(self):
        project = self.db.get_project(self.project_id)
        if not project:
            return
        calc = ISDCCalculator(dict(project), self.db)
        profiles = calc.compute_phase_profiles()
        if not profiles:
            self.lbl_profile.setText("No phases defined. Cost NPV uses a default 5-year midpoint.")
            return
        lines = []
        for p in profiles:
            lines.append(
                f"{p.phase_name:<35} {p.start_year}-{p.end_year}  "
                f"Base: {p.total_cost_eur:>16,.0f} EUR   "
                f"NPV: {p.npv_cost_eur:>16,.0f} EUR"
            )
        self.lbl_profile.setText("\n".join(lines))

    def _get_selected_phase_id(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return item.data(Qt.UserRole) if item else None

    def _on_add(self):
        project = self.db.get_project(self.project_id)
        dlg = PhaseDialog(self.project_id, int(project["base_year"] or 2030), parent=self)
        if dlg.exec_() == QDialog.Accepted:
            self.db.save_phase(dlg.get_data())
            self._refresh()
            if self.main_window:
                self.main_window.tab_matrix.load_project(self.project_id)

    def _on_edit(self):
        pid = self._get_selected_phase_id()
        if not pid:
            QMessageBox.information(self, "No selection", "Select a phase to edit.")
            return
        phases = self.db.get_phases(self.project_id)
        phase_data = next((dict(p) for p in phases if p["id"] == pid), None)
        project = self.db.get_project(self.project_id)
        dlg = PhaseDialog(self.project_id, int(project["base_year"] or 2030), phase_data, parent=self)
        if dlg.exec_() == QDialog.Accepted:
            self.db.save_phase(dlg.get_data())
            self._refresh()
            if self.main_window:
                self.main_window.tab_matrix.load_project(self.project_id)

    def _on_delete(self):
        pid = self._get_selected_phase_id()
        if not pid:
            QMessageBox.information(self, "No selection", "Select a phase to delete.")
            return
        reply = QMessageBox.question(
            self, "Confirm", "Delete this phase?\nCost entries linked to this phase will become unallocated.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.db.delete_phase(pid)
            self._refresh()
            if self.main_window:
                self.main_window.tab_matrix.load_project(self.project_id)
