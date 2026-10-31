"""
gui/cost_matrix_tab.py
========================
Tab 2 — ISDC Cost Matrix. Full three-level ISDC hierarchy with
Labour / Investment / Expenses / Contingency entry at Level-3 (and
Level-2, for lump-sum entries), per-entry phase allocation, and the
graded approach: every PA / Level-2 / Level-3 item shows its
applicability (M/D/A/C/N) for the facility type, which the user can
override with a justification.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem,
    QLabel, QGroupBox, QFormLayout, QDoubleSpinBox, QComboBox, QLineEdit,
    QPushButton, QSplitter, QSizePolicy, QMessageBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor, QBrush

from core.applicability import WARN, build_applicability_review, level3_cost_on_not_applicable
from core.database import DatabaseManager
from core.facility_profiles import APPLICABILITY_LABELS, effective_applicability
from core.isdc_data import ISDC_HIERARCHY

COLOR_DOMINANT = QColor("#fff3cd")
COLOR_REVIEW = QColor("#ffe0e0")
COLOR_NOT_APPLICABLE = QColor("#e4e8ec")
COLOR_NA_TEXT = QColor("#7a8590")
COLOR_HAS_COST = QColor("#f0f8ff")

(COL_CODE, COL_TITLE, COL_APPL, COL_LABOUR, COL_INVEST, COL_EXPENSE,
 COL_CONTING, COL_TOTAL) = range(8)
N_COLS = 8
COST_KEYS = ("labour_eur", "investment_eur", "expenses_eur", "contingency_eur")


def _fmt(v):
    return f"{v:,.2f}" if v else ""


class CostMatrixTab(QWidget):
    def __init__(self, db: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db = db
        self.main_window = parent
        self.project_id = None
        self.facility_type = None
        self._project = None
        self._entries = {}
        self._overrides = {}
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
        self.lbl_warning.setWordWrap(True)
        self.lbl_warning.setStyleSheet("color:#7a3030; font-weight:bold;")
        outer.addWidget(self.lbl_warning)

        legend = QLabel("Applicability: M = Mandatory, D = Dominant cost driver, A = Applicable, "
                        "C = Conditional, N = Not applicable.  * = set by user for this project.")
        legend.setStyleSheet("color:#5a7a9a; font-style:italic; font-size:11px;")
        outer.addWidget(legend)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        outer.addWidget(splitter)
        outer.setStretch(0, 0)
        outer.setStretch(1, 0)
        outer.setStretch(2, 0)
        outer.setStretch(3, 1)

        self.tree = QTreeWidget()
        self.tree.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tree.setMinimumHeight(420)
        self.tree.setHeaderLabels(
            ["Code", "Title", "Applic.", "Labour (EUR)", "Investment (EUR)", "Expenses (EUR)",
             "Contingency (EUR)", "Total (EUR)"]
        )
        self.tree.setColumnWidth(COL_CODE, 115)
        self.tree.setColumnWidth(COL_TITLE, 300)
        self.tree.setColumnWidth(COL_APPL, 55)
        for col in range(COL_LABOUR, N_COLS):
            self.tree.setColumnWidth(col, 110)
        self.tree.itemSelectionChanged.connect(self._on_selection_changed)
        splitter.addWidget(self.tree)

        self.panel = self._build_entry_panel()
        self.panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        splitter.addWidget(self.panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

    def _build_entry_panel(self):
        panel = QWidget()
        outer = QVBoxLayout(panel)
        outer.setContentsMargins(0, 0, 0, 0)

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
        outer.addWidget(grp)

        # --- Graded approach -------------------------------------------
        grp_a = QGroupBox("Applicability (graded approach)")
        la = QVBoxLayout(grp_a)
        la.setAlignment(Qt.AlignTop)
        self.lbl_appl_default = QLabel("Select a code in the tree.")
        self.lbl_appl_default.setWordWrap(True)
        la.addWidget(self.lbl_appl_default)
        fa = QFormLayout()
        self.cb_appl = QComboBox()
        self.cb_appl.addItem("Use default", None)
        for code, label in APPLICABILITY_LABELS.items():
            self.cb_appl.addItem(f"{code} — {label}", code)
        fa.addRow("Rating", self.cb_appl)
        self.ed_justification = QLineEdit()
        self.ed_justification.setPlaceholderText("Why this rating applies to this facility")
        fa.addRow("Justification", self.ed_justification)
        la.addLayout(fa)
        self.btn_save_appl = QPushButton("Save Applicability")
        self.btn_save_appl.clicked.connect(self._on_save_applicability)
        self.btn_save_appl.setEnabled(False)
        la.addWidget(self.btn_save_appl)
        outer.addWidget(grp_a)
        outer.addStretch()

        self._current_code = None
        self._current_level = None
        return panel

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

    def _appl_cell(self, item, code):
        eff = effective_applicability(self.facility_type, code, self._overrides)
        user_here = code in self._overrides
        item.setText(COL_APPL, eff["rating"] + (" *" if user_here else ""))
        item.setTextAlignment(COL_APPL, Qt.AlignCenter)
        tip = APPLICABILITY_LABELS.get(eff["rating"], eff["rating"])
        tip += f" ({'set by user' if eff['source'] == 'User' else 'default for facility type'}"
        tip += f", defined at {eff['rule_code']})"
        if eff["justification"]:
            tip += f"\n{eff['justification']}"
        item.setToolTip(COL_APPL, tip)
        return eff

    @staticmethod
    def _paint(item, color, text_color=None):
        for col in range(N_COLS):
            item.setBackground(col, color)
            if text_color:
                item.setForeground(col, QBrush(text_color))

    def _refresh_tree(self):
        self.tree.clear()
        if not self.project_id:
            return
        self._project = self.db.get_project(self.project_id)
        self._entries = self.db.get_cost_entries(self.project_id)
        self._overrides = self.db.get_applicability_overrides(self.project_id)
        review = {r.code: r for r in build_applicability_review(self._project, self.db)}

        for pa_code, pa in ISDC_HIERARCHY.items():
            pa_item = QTreeWidgetItem([pa_code, pa["title"]] + [""] * (N_COLS - 2))
            pa_item.setFont(COL_TITLE, QFont("Arial", 9, QFont.Bold))
            pa_item.setData(0, Qt.UserRole, ("1", pa_code))
            pa_sums = [0.0] * 4

            for l2_code, (l2_title, l3_list) in pa["groups"].items():
                l2_item = QTreeWidgetItem([l2_code, l2_title] + [""] * (N_COLS - 2))
                l2_item.setData(0, Qt.UserRole, ("2", l2_code))
                # Lump-sum entry on the Level-2 code itself counts towards the group.
                own = self._entries.get(l2_code) or {}
                l2_sums = [own.get(k) or 0.0 for k in COST_KEYS]

                for l3_code, l3_title in l3_list:
                    entry = self._entries.get(l3_code) or {}
                    vals = [entry.get(k) or 0.0 for k in COST_KEYS]
                    total = sum(vals)
                    l3_item = QTreeWidgetItem([l3_code, l3_title, ""] + [_fmt(v) for v in vals] + [_fmt(total)])
                    l3_item.setData(0, Qt.UserRole, ("3", l3_code))
                    eff = self._appl_cell(l3_item, l3_code)
                    if eff["rating"] == "N":
                        self._paint(l3_item, COLOR_REVIEW if total > 0 else COLOR_NOT_APPLICABLE,
                                    None if total > 0 else COLOR_NA_TEXT)
                    elif total > 0:
                        self._paint(l3_item, COLOR_HAS_COST)
                    l2_item.addChild(l3_item)
                    l2_sums = [a + b for a, b in zip(l2_sums, vals)]

                self._fill_sums(l2_item, l2_sums)
                eff = self._appl_cell(l2_item, l2_code)
                self._colour_reviewed(l2_item, review.get(l2_code), eff)
                pa_item.addChild(l2_item)
                pa_sums = [a + b for a, b in zip(pa_sums, l2_sums)]

            self._fill_sums(pa_item, pa_sums)
            eff = self._appl_cell(pa_item, pa_code)
            self._colour_reviewed(pa_item, review.get(pa_code), eff, top_level=True)
            self.tree.addTopLevelItem(pa_item)

        self.tree.expandToDepth(0)
        self._update_warnings(review)

    def _fill_sums(self, item, sums):
        for col, v in zip((COL_LABOUR, COL_INVEST, COL_EXPENSE, COL_CONTING), sums):
            item.setText(col, _fmt(v))
        item.setText(COL_TOTAL, _fmt(sum(sums)))

    def _colour_reviewed(self, item, row, eff, top_level=False):
        if row and row.severity == WARN:
            self._paint(item, COLOR_REVIEW)
            item.setToolTip(COL_TITLE, row.status)
        elif eff["rating"] == "N":
            self._paint(item, COLOR_NOT_APPLICABLE, COLOR_NA_TEXT)
        elif top_level and eff["rating"] == "D":
            self._paint(item, COLOR_DOMINANT)
        if row:
            item.setToolTip(COL_TITLE, row.status)

    def _update_warnings(self, review):
        issues = [f"{r.code} — {r.status}" for r in review.values() if r.severity == WARN]
        issues += [f"{c} — Cost entered on an item rated Not applicable"
                   for c in level3_cost_on_not_applicable(self._project, self.db)
                   if not any(i.startswith(c[:5] + " ") for i in issues)]
        if not issues:
            self.lbl_warning.setText("")
            return
        shown = issues[:3]
        more = f" (+{len(issues) - 3} more — see the Applicability section of the report)" if len(issues) > 3 else ""
        self.lbl_warning.setText(f"{len(issues)} item(s) need review: " + ";  ".join(shown) + more)

    # ------------------------------------------------------------------
    def _on_selection_changed(self):
        items = self.tree.selectedItems()
        if not items:
            self.btn_save.setEnabled(False)
            self.btn_save_appl.setEnabled(False)
            return
        item = items[0]
        data = item.data(0, Qt.UserRole)
        if not data:
            return
        level, code = data
        self._current_level = int(level)
        self._current_code = code
        self._load_applicability_editor(code)

        cost_editable = level in ("2", "3")
        for w in (self.sp_labour, self.sp_invest, self.sp_expense, self.sp_conting,
                  self.cb_phase, self.ed_notes):
            w.setEnabled(cost_editable)
        self.btn_save.setEnabled(cost_editable)
        if not cost_editable:
            self.lbl_selected.setText(f"{code} — {item.text(COL_TITLE)}\n"
                                      "Select a Level-2 or Level-3 code to enter costs.")
            return
        entry = self._entries.get(code, {})
        self.sp_labour.setValue(entry.get("labour_eur", 0.0) or 0.0)
        self.sp_invest.setValue(entry.get("investment_eur", 0.0) or 0.0)
        self.sp_expense.setValue(entry.get("expenses_eur", 0.0) or 0.0)
        self.sp_conting.setValue(entry.get("contingency_eur", 0.0) or 0.0)
        self.ed_notes.setText(entry.get("notes", "") or "")
        phase_id = entry.get("phase_id")
        idx = self.cb_phase.findData(phase_id) if phase_id else 0
        self.cb_phase.setCurrentIndex(idx if idx >= 0 else 0)
        self.lbl_selected.setText(f"Editing: {code} — {item.text(COL_TITLE)}")
        self._update_total_label()

    def _load_applicability_editor(self, code):
        # Default = what this code would get without a user rating at this exact code.
        overrides_above = {c: o for c, o in self._overrides.items() if c != code}
        base = effective_applicability(self.facility_type, code, overrides_above)
        text = (f"{code}: default {base['rating']} — {APPLICABILITY_LABELS.get(base['rating'])}"
                f" ({'inherited user rating' if base['source'] == 'User' else 'facility-type default'})")
        if base["justification"]:
            text += f"\n{base['justification']}"
        self.lbl_appl_default.setText(text)
        own = self._overrides.get(code)
        idx = self.cb_appl.findData(own["rating"]) if own else 0
        self.cb_appl.setCurrentIndex(max(idx, 0))
        self.ed_justification.setText(own["justification"] if own else "")
        self.btn_save_appl.setEnabled(True)

    def _on_save_applicability(self):
        if not self._current_code or not self.project_id:
            return
        rating = self.cb_appl.currentData()
        why = self.ed_justification.text().strip()
        if rating and not why:
            QMessageBox.warning(self, "Justification required",
                                "Under a graded approach every change to the default rating "
                                "needs a short justification.")
            return
        self.db.set_applicability_override(self.project_id, self._current_code, rating, why)
        code = self._current_code
        self._refresh_tree()
        self._scroll_to_code(code)
        if self.main_window:
            msg = f"Applicability of {code} set to {rating}." if rating else f"{code} reset to default."
            self.main_window.statusBar().showMessage(msg, 4000)

    def _on_save_entry(self):
        if not self._current_code or not self.project_id or self._current_level == 1:
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
