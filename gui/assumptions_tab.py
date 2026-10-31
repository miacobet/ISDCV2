"""
gui/assumptions_tab.py
========================
Tab 5 — Assumptions Register, following an Appendix-B style checklist,
with facility-specific additional items. Supports bulk "mark as
documented" for a section or for all sections.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHeaderView, QComboBox, QProgressBar, QMessageBox,
    QCheckBox, QLineEdit
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from core.database import DatabaseManager


class AssumptionsTab(QWidget):
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

        title = QLabel("Assumptions Register")
        title.setFont(QFont("Arial", 11, QFont.Bold))
        title.setStyleSheet("color: #1a3a5c;")
        layout.addWidget(title)

        note = QLabel(
            "Checklist of key assumptions that should be documented to support this estimate, "
            "condensed from the topics of ISDC Appendix B, with additional facility-specific items. "
            "For full coverage, also check against Appendix B of the ISDC publication."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #5a7a9a; font-size: 10px; font-style: italic;")
        layout.addWidget(note)

        self.progress = QProgressBar()
        self.progress.setFormat("Completeness: %p%")
        layout.addWidget(self.progress)

        ctl_row = QHBoxLayout()
        ctl_row.addWidget(QLabel("Section:"))
        self.cb_section = QComboBox()
        self.cb_section.addItem("All sections")
        ctl_row.addWidget(self.cb_section)
        self.btn_mark = QPushButton("Mark visible section as documented")
        self.btn_mark.clicked.connect(self._on_bulk_mark)
        ctl_row.addWidget(self.btn_mark)
        ctl_row.addStretch()
        layout.addLayout(ctl_row)
        self.cb_section.currentTextChanged.connect(self._refresh)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Documented", "Section", "Assumption", "Notes"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Interactive)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Interactive)
        self.table.setColumnWidth(1, 170)
        self.table.setColumnWidth(3, 260)
        # Long assumption texts wrap onto several lines instead of being cut off with "...".
        self.table.setWordWrap(True)
        self.table.setTextElideMode(Qt.ElideNone)
        header.sectionResized.connect(lambda *_: self.table.resizeRowsToContents())
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

    def load_project(self, project_id: int):
        self.project_id = project_id
        self._refresh_sections()
        self._refresh()

    def _refresh_sections(self):
        rows = self.db.get_project_assumptions(self.project_id)
        sections = sorted({r["section"] for r in rows if r.get("section")})
        current = self.cb_section.currentText()
        self.cb_section.blockSignals(True)
        self.cb_section.clear()
        self.cb_section.addItem("All sections")
        for s in sections:
            self.cb_section.addItem(s)
        idx = self.cb_section.findText(current)
        self.cb_section.setCurrentIndex(idx if idx >= 0 else 0)
        self.cb_section.blockSignals(False)

    def _refresh(self):
        if not self.project_id:
            return
        rows = self.db.get_project_assumptions(self.project_id)
        section_filter = self.cb_section.currentText()
        if section_filter != "All sections":
            rows = [r for r in rows if r.get("section") == section_filter]

        self.table.setRowCount(0)
        documented_count = 0
        for r in rows:
            row = self.table.rowCount()
            self.table.insertRow(row)

            chk = QCheckBox()
            chk.setChecked(bool(r.get("documented")))
            chk.stateChanged.connect(lambda state, rid=r["id"]: self._on_toggle(rid, state))
            self.table.setCellWidget(row, 0, chk)

            sec_item = QTableWidgetItem(r.get("section") or "")
            sec_item.setToolTip(sec_item.text())
            self.table.setItem(row, 1, sec_item)
            text = r.get("custom_text")
            if not text:
                checklist = self.db.get_assumptions_checklist()
                item = next((c for c in checklist if c["id"] == r.get("checklist_id")), None)
                text = item["text"] if item else ""
            text_item = QTableWidgetItem(text)
            text_item.setToolTip(text)
            self.table.setItem(row, 2, text_item)

            notes_edit = QLineEdit(r.get("notes") or "")
            notes_edit.editingFinished.connect(
                lambda rid=r["id"], w=notes_edit, chk=chk: self.db.set_assumption_documented(
                    rid, chk.isChecked(), w.text().strip()
                )
            )
            self.table.setCellWidget(row, 3, notes_edit)

            if r.get("documented"):
                documented_count += 1

        self.table.resizeRowsToContents()
        total = len(rows)
        pct = int(round(100 * documented_count / total)) if total else 0
        self.progress.setValue(pct)

    def _on_toggle(self, assumption_id, state):
        self.db.set_assumption_documented(assumption_id, state == Qt.Checked, self._notes_for_row(assumption_id))
        self._refresh()

    def _notes_for_row(self, assumption_id):
        rows = self.db.get_project_assumptions(self.project_id)
        row = next((r for r in rows if r["id"] == assumption_id), None)
        return row.get("notes") or "" if row else ""

    def _on_bulk_mark(self):
        section = self.cb_section.currentText()
        scope_desc = "ALL sections" if section == "All sections" else f"section '{section}'"
        reply = QMessageBox.question(
            self, "Confirm bulk update",
            f"Mark every visible assumption in {scope_desc} as documented?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.db.bulk_set_documented(self.project_id, section, True)
            self._refresh()
