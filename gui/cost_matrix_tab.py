"""
gui/cost_matrix_tab.py
========================
Tab 2 — ISDC Cost Matrix. Full three-level ISDC hierarchy with
Labour / Investment / Expenses / Contingency entry at Level-3 (and
Level-2, for lump-sum entries), colour-coded by facility-type
applicability, with per-entry phase allocation.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QLabel, QGroupBox, QFormLayout, QDoubleSpinBox, QComboBox, QLineEdit,
    QPushButton, QHeaderView, QMessageBox, QSplitter, QSizePolicy
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor

from core.database import DatabaseManager
from core.facility_profiles import get_code_applicability
from core.isdc_data import ISDC_HIERARCHY

COLOR_DOMINANT = QColor("#fff3cd")
COLOR_MANDATORY_EMPTY = QColor("#ffe0e0")
COLOR_NOT_APPLICABLE = QColor("#b0b8c0")
COLOR_HAS_COST = QColor("#f0f8ff")

COL_CODE, COL_TITLE, COL_LABOUR, COL_INVEST, COL_EXPENSE, COL_CONTING, COL_TOTAL = range(7)


class CostMatrixTab(QWidget):
    def __init__(self, db: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db = db
        self.main_window = parent
        self.project_id = None
        self.facility_type = None
        self._entries = {}
        self._phases = []
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)

        title = QLabel("ISDC Cost Matrix")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        title.setStyleSheet("color:#1a3a5c;")
        outer.addWidget(title)

        self.lbl_warning = QLabel("")
        self.lbl_warning.setStyleSheet("color:#7a3030; font-weight:bold;")
        outer.addWidget(self.lbl_warning)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        outer.addWidget(splitter)
        outer.setStretch(0, 0)
        outer.setStretch(1, 0)
        outer.setStretch(2, 1)

        self.tree = QTreeWidget()
        self.tree.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tree.setMinimumHeight(420)
        self.tree.setHeaderLabels(
            ["Code", "Title", "Labour (EUR)", "Investment (EUR)", "Expenses (EUR)",
             "Contingency (EUR)", "Total (EUR)"]
        )
        self.tree.setColumnWidth(0, 90)
        self.tree.setColumnWidth(1, 300)
        for col in range(2, 7):
            self.tree.setColumnWidth(col, 110)
        self.tree.itemSelectionChanged.connect(self._on_selection_changed)
        splitter.addWidget(self.tree)

        self.panel = self._build_entry_panel()
        self.panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        splitter.addWidget(self.panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

    def _build_entry_panel(self):
        grp = QGroupBox("Cost Entry")
        layout = QVBoxLayout(grp)
        layout.setAlignment(Qt.AlignTop)
        self.lbl_selected = QLabel("Select a code in the tree.")
        self.lbl_selected.setWordWrap(True)
        layout.addWidget(self.lbl_selected)

        form = QFormLayout()
        self.sp_labour = QDoubleSpinBox()
        self.sp_invest = QDoubleSpinBox()
        self.sp_expense = QDoubleSpinBox()
        self.sp_conting = QDoubleSpinBox()
        for sp in (self.sp_labour, self.sp_invest, self.sp_expense, self.sp_conting):
            sp.setRange(0, 1e12)
            sp.setDecimals(2)
            sp.setSuffix(" EUR")
        form.addRow("Labour", self.sp_labour)
        form.addRow("Investment", self.sp_invest)
        form.addRow("Expenses", self.sp_expense)
        form.addRow("Contingency", self.sp_conting)

        self.cb_phase = QComboBox()
        self.cb_phase.addItem("(unallocated)", None)
        form.addRow("Phase", self.cb_phase)

        self.ed_notes = QLineEdit()
        form.addRow("Notes", self.ed_notes)
        layout.addLayout(form)

        self.lbl_total = QLabel("Total: 0.00 EUR")
        self.lbl_total.setStyleSheet("font-weight:bold;")
        layout.addWidget(self.lbl_total)
        for sp in (self.sp_labour, self.sp_invest, self.sp_expense, self.sp_conting):
            sp.valueChanged.connect(self._update_total_label)

        self.btn_save = QPushButton("Save Entry")
        self.btn_save.clicked.connect(self._on_save_entry)
        self.btn_save.setEnabled(False)
        layout.addWidget(self.btn_save)

        layout.addStretch()
        self._current_code = None
        self._current_level = None
        return grp

    def _update_total_label(self):
        total = (self.sp_labour.value() + self.sp_invest.value()
                 + self.sp_expense.value() + self.sp_conting.value())
        self.lbl_total.setText(f"Total: {total:,.2f} EUR")

    # ------------------------------------------------------------------
    def load_project(self, project_id: int):
        self.project_id = project_id
        project = self.db.get_project(project_id)
        self.facility_type = project.get("facility_type") if project else None
        self._phases = self.db.get_phases(project_id)
        self.cb_phase.clear()
        self.cb_phase.addItem("(unallocated)", None)
        for ph in self._phases:
            self.cb_phase.addItem(f"{ph['phase_name']} ({ph['start_year']}-{ph['end_year']})", ph["id"])
        self._refresh_tree()

    def _refresh_tree(self):
        self.tree.clear()
        self._entries = self.db.get_cost_entries(self.project_id) if self.project_id else {}
        mandatory_empty = 0
        dominant_empty = 0

        for pa_code, pa in ISDC_HIERARCHY.items():
            applicability = get_code_applicability(self.facility_type, pa_code) if self.facility_type else "A"
            pa_labour = pa_invest = pa_expense = pa_conting = 0.0
            pa_item = QTreeWidgetItem([pa_code, pa["title"], "", "", "", "", ""])
            pa_item.setFont(COL_TITLE, QFont("Arial", 9, QFont.Bold))

            for l2_code, (l2_title, l3_list) in pa["groups"].items():
                l2_item = QTreeWidgetItem([l2_code, l2_title, "", "", "", "", ""])
                l2_labour = l2_invest = l2_expense = l2_conting = 0.0

                for l3_code, l3_title in l3_list:
                    entry = self._entries.get(l3_code)
                    labour = entry.get("labour_eur", 0.0) if entry else 0.0
                    invest = entry.get("investment_eur", 0.0) if entry else 0.0
                    expense = entry.get("expenses_eur", 0.0) if entry else 0.0
                    conting = entry.get("contingency_eur", 0.0) if entry else 0.0
                    total = labour + invest + expense + conting
                    l3_item = QTreeWidgetItem([
                        l3_code, l3_title,
                        f"{labour:,.2f}" if labour else "",
                        f"{invest:,.2f}" if invest else "",
                        f"{expense:,.2f}" if expense else "",
                        f"{conting:,.2f}" if conting else "",
                        f"{total:,.2f}" if total else "",
                    ])
                    l3_item.setData(0, Qt.UserRole, ("3", l3_code))
                    if total > 0:
                        for col in range(7):
                            l3_item.setBackground(col, COLOR_HAS_COST)
                    l2_item.addChild(l3_item)
                    l2_labour += labour
                    l2_invest += invest
                    l2_expense += expense
                    l2_conting += conting

                l2_total = l2_labour + l2_invest + l2_expense + l2_conting
                l2_item.setText(COL_LABOUR, f"{l2_labour:,.2f}" if l2_labour else "")
                l2_item.setText(COL_INVEST, f"{l2_invest:,.2f}" if l2_invest else "")
                l2_item.setText(COL_EXPENSE, f"{l2_expense:,.2f}" if l2_expense else "")
                l2_item.setText(COL_CONTING, f"{l2_conting:,.2f}" if l2_conting else "")
                l2_item.setText(COL_TOTAL, f"{l2_total:,.2f}" if l2_total else "")
                l2_item.setData(0, Qt.UserRole, ("2", l2_code))
                pa_item.addChild(l2_item)
                pa_labour += l2_labour
                pa_invest += l2_invest
                pa_expense += l2_expense
                pa_conting += l2_conting

            pa_total = pa_labour + pa_invest + pa_expense + pa_conting
            pa_item.setText(COL_LABOUR, f"{pa_labour:,.2f}" if pa_labour else "")
            pa_item.setText(COL_INVEST, f"{pa_invest:,.2f}" if pa_invest else "")
            pa_item.setText(COL_EXPENSE, f"{pa_expense:,.2f}" if pa_expense else "")
            pa_item.setText(COL_CONTING, f"{pa_conting:,.2f}" if pa_conting else "")
            pa_item.setText(COL_TOTAL, f"{pa_total:,.2f}" if pa_total else "")
            pa_item.setData(0, Qt.UserRole, ("1", pa_code))

            if applicability == "N":
                for col in range(7):
                    pa_item.setBackground(col, COLOR_NOT_APPLICABLE)
            elif applicability == "D":
                for col in range(7):
                    pa_item.setBackground(col, COLOR_DOMINANT)
                if pa_total == 0:
                    dominant_empty += 1
            elif applicability == "M" and pa_total == 0:
                for col in range(7):
                    pa_item.setBackground(col, COLOR_MANDATORY_EMPTY)
                mandatory_empty += 1

            self.tree.addTopLevelItem(pa_item)

        self.tree.expandToDepth(0)
        warnings = []
        if mandatory_empty:
            warnings.append(f"{mandatory_empty} mandatory Principal Activity(ies) have no cost entered")
        if dominant_empty:
            warnings.append(f"{dominant_empty} dominant-cost Principal Activity(ies) have no cost entered")
        self.lbl_warning.setText(" / ".join(warnings))

    # ------------------------------------------------------------------
    def _on_selection_changed(self):
        items = self.tree.selectedItems()
        if not items:
            self.btn_save.setEnabled(False)
            return
        item = items[0]
        data = item.data(0, Qt.UserRole)
        if not data or data[0] not in ("2", "3"):
            self.btn_save.setEnabled(False)
            self.lbl_selected.setText("Select a Level-2 or Level-3 code to enter costs.")
            self._current_code = None
            return
        level, code = data
        self._current_level = int(level)
        self._current_code = code
        entry = self._entries.get(code, {})
        self.sp_labour.setValue(entry.get("labour_eur", 0.0) or 0.0)
        self.sp_invest.setValue(entry.get("investment_eur", 0.0) or 0.0)
        self.sp_expense.setValue(entry.get("expenses_eur", 0.0) or 0.0)
        self.sp_conting.setValue(entry.get("contingency_eur", 0.0) or 0.0)
        self.ed_notes.setText(entry.get("notes", "") or "")
        phase_id = entry.get("phase_id")
        idx = self.cb_phase.findData(phase_id) if phase_id else 0
        self.cb_phase.setCurrentIndex(idx if idx >= 0 else 0)
        self.lbl_selected.setText(f"Editing: {code} — {item.text(1)}")
        self.btn_save.setEnabled(True)
        self._update_total_label()

    def _on_save_entry(self):
        if not self._current_code or not self.project_id:
            return
        self.db.save_cost_entry(
            self.project_id, self._current_code, self._current_level,
            self.sp_labour.value(), self.sp_invest.value(),
            self.sp_expense.value(), self.sp_conting.value(),
            phase_id=self.cb_phase.currentData(),
            notes=self.ed_notes.text().strip(),
        )
        saved_code = self._current_code
        self._refresh_tree()
        self._scroll_to_code(saved_code)
        if self.main_window:
            self.main_window.statusBar().showMessage(f"Saved cost entry {saved_code}.", 4000)

    def _scroll_to_code(self, code: str):
        def find(item):
            data = item.data(0, Qt.UserRole)
            if data and data[1] == code:
                return item
            for i in range(item.childCount()):
                found = find(item.child(i))
                if found:
                    return found
            return None

        for i in range(self.tree.topLevelItemCount()):
            node = find(self.tree.topLevelItem(i))
            if node:
                self.tree.setCurrentItem(node)
                self.tree.scrollToItem(node, QTreeWidget.PositionAtCenter)
                return