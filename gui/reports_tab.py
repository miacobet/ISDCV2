"""
gui/reports_tab.py
====================
Tab 6 — Reports. Financial Summary, Funding Plan, EUR/MWh Levy (power
reactors only) and Export sub-tabs.
"""

import datetime

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel, QFormLayout,
    QDoubleSpinBox, QSpinBox, QComboBox, QPushButton, QFileDialog, QMessageBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView
)
from PyQt5.QtCore import Qt, QLocale
from PyQt5.QtGui import QFont

from core.database import DatabaseManager
from core.facility_profiles import is_power_reactor
from core.calculator import ISDCCalculator, ESTIMATE_ACCURACY, REFERENCE_TARIFFS, REFERENCE_TARIFFS_NOTE
from core.funding_plan import (
    FREQUENCIES, PLAN_METHOD_NOTE, compute_funding_plan, cost_profile_for_project,
    inputs_from_project, levy_for_project, sensitivity,
)
from export import excel_export, pdf_export


class ReportsTab(QWidget):
    def __init__(self, db: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db = db
        self.main_window = parent
        self.project_id = None
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)
        title = QLabel("Reports")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        title.setStyleSheet("color:#1a3a5c;")
        outer.addWidget(title)

        self.inner_tabs = QTabWidget()
        self.inner_tabs.setElideMode(Qt.ElideNone)
        self.inner_tabs.tabBar().setUsesScrollButtons(True)
        self.inner_tabs.tabBar().setExpanding(False)
        outer.addWidget(self.inner_tabs)

        self._build_financial_summary_tab()
        self._build_funding_plan_tab()
        self._build_mwh_tab()
        self._build_export_tab()

    # ------------------------------------------------------------------
    def _build_financial_summary_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.lbl_summary = QLabel("Load a project to view the financial summary.")
        self.lbl_summary.setWordWrap(True)
        self.lbl_summary.setStyleSheet("font-family: Menlo, Consolas, \"Courier New\", monospace; font-size: 11px;")
        layout.addWidget(self.lbl_summary)
        layout.addStretch()
        self.inner_tabs.addTab(tab, "Financial Summary")

    def _build_funding_plan_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        note = QLabel(
            "How much must be paid into the decommissioning fund, and how often, so the fund "
            "can pay every cost when it falls due. Uses the phase cost profile of this project. "
            "All rates are your inputs — use the values required by your national legislation."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color:#5a7a9a; font-style:italic; font-size:11px;")
        layout.addWidget(note)

        top = QHBoxLayout()
        form = QFormLayout()

        def year_box():
            sb = QSpinBox()
            sb.setRange(1950, 2200)
            return sb

        def pct_box(lo=-20.0, hi=50.0):
            sb = QDoubleSpinBox()
            sb.setRange(lo, hi)
            sb.setDecimals(2)
            sb.setSingleStep(0.25)
            sb.setSuffix(" %")
            return sb

        self.fp_start = year_box()
        form.addRow("Plan start year (first contribution)", self.fp_start)
        self.fp_shutdown = year_box()
        form.addRow("Shutdown year (last contribution the year before)", self.fp_shutdown)
        self.fp_balance = QDoubleSpinBox()
        self.fp_balance.setRange(0, 1e13)
        self.fp_balance.setDecimals(0)
        self.fp_balance.setGroupSeparatorShown(True)
        self.fp_balance.setLocale(QLocale(QLocale.English))  # 1,000,000 like the rest of the app
        self.fp_balance.setSuffix(" EUR")
        form.addRow("Fund balance at plan start", self.fp_balance)
        self.fp_return = pct_box()
        form.addRow("Expected fund return (nominal, per year)", self.fp_return)
        self.fp_escalation = pct_box()
        form.addRow("Cost escalation / inflation (per year)", self.fp_escalation)
        self.fp_frequency = QComboBox()
        self.fp_frequency.addItems(list(FREQUENCIES.keys()))
        form.addRow("Payment frequency", self.fp_frequency)
        self.fp_growth = pct_box()
        form.addRow("Yearly increase of payments (0 = level)", self.fp_growth)
        top.addLayout(form, 3)

        self.lbl_fp_result = QLabel("")
        self.lbl_fp_result.setWordWrap(True)
        self.lbl_fp_result.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.lbl_fp_result.setStyleSheet("font-family: Menlo, Consolas, \"Courier New\", monospace; font-size: 11px;")
        self.lbl_fp_result.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        top.addWidget(self.lbl_fp_result, 4)
        layout.addLayout(top)

        btn = QPushButton("Calculate && Save Funding Plan")
        btn.clicked.connect(self._on_funding_plan_calculate)
        layout.addWidget(btn)

        self.fp_table = QTableWidget(0, 7)
        self.fp_table.setHorizontalHeaderLabels(
            ["Year", "Stage", "Opening balance", "Contributions", "Fund return", "Costs paid", "Closing balance"])
        self.fp_table.verticalHeader().setVisible(False)
        self.fp_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.fp_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.fp_table, 1)
        self.inner_tabs.addTab(tab, "Funding Plan")

    def _load_funding_plan_inputs(self, project):
        this_year = datetime.date.today().year
        base_year = int(project.get("base_year") or this_year)
        start = int(project.get("fp_start_year") or max(base_year, this_year))
        op_years = float(project.get("remaining_op_years") or 0)
        shutdown = int(project.get("fp_shutdown_year") or (start + (round(op_years) if op_years else 20)))
        self.fp_start.setValue(start)
        self.fp_shutdown.setValue(shutdown)
        self.fp_balance.setValue(float(project.get("fp_opening_balance") or 0))
        ret = project.get("fp_return_pct")
        self.fp_return.setValue(float(ret if ret is not None else (project.get("discount_rate") or 3.0)))
        esc = project.get("fp_escalation_pct")
        self.fp_escalation.setValue(float(esc if esc is not None else (project.get("inflation_rate") or 2.0)))
        idx = self.fp_frequency.findText(project.get("fp_frequency") or "Yearly")
        self.fp_frequency.setCurrentIndex(max(idx, 0))
        self.fp_growth.setValue(float(project.get("fp_growth_pct") or 0))
        if project.get("fp_shutdown_year"):
            self._show_funding_plan(project)
        else:
            self.lbl_fp_result.setText("Enter the plan inputs and press Calculate.")
            self.fp_table.setRowCount(0)

    def _on_funding_plan_calculate(self):
        if not self.project_id:
            return
        if self.fp_shutdown.value() <= self.fp_start.value():
            QMessageBox.warning(self, "Funding plan",
                                "The shutdown year must be later than the plan start year.")
            return
        self.db.update_project(self.project_id, {
            "fp_start_year": self.fp_start.value(),
            "fp_shutdown_year": self.fp_shutdown.value(),
            "fp_opening_balance": self.fp_balance.value(),
            "fp_return_pct": self.fp_return.value(),
            "fp_escalation_pct": self.fp_escalation.value(),
            "fp_frequency": self.fp_frequency.currentText(),
            "fp_growth_pct": self.fp_growth.value(),
        })
        self._show_funding_plan(self.db.get_project(self.project_id))
        self._on_calculate_mwh()  # the levy is derived from the plan
        if self.main_window:
            self.main_window.statusBar().showMessage("Funding plan saved.", 4000)

    def _show_funding_plan(self, project):
        inp = inputs_from_project(project)
        profile = cost_profile_for_project(project, self.db)
        if not inp or not profile:
            self.lbl_fp_result.setText("No costs entered yet — nothing to fund.")
            self.fp_table.setRowCount(0)
            return
        res = compute_funding_plan(inp, profile)
        unit = {12: "month", 4: "quarter", 1: "year"}[res.periods_per_year]
        lines = []
        if res.message:
            lines += [res.message, ""]
        lines += [
            f"Required payment:          {res.payment_per_period:>18,.0f} EUR per {unit}",
            f"  = per year (first year): {res.first_year_annual_contribution:>18,.0f} EUR",
        ]
        if inp.contribution_growth_pct:
            lines.append(f"  (increasing {inp.contribution_growth_pct:.2f}% each year)")
        if res.eur_per_mwh:
            lines.append(f"  = per MWh (first year):  {res.eur_per_mwh:>18,.3f} EUR/MWh")
        lines += [
            f"Number of contribution years: {res.contribution_years}",
            "",
            f"Fund needed at shutdown:   {res.balance_at_shutdown:>18,.0f} EUR",
            f"Total contributions:       {res.total_contributions:>18,.0f} EUR",
            f"Total fund returns:        {res.total_returns:>18,.0f} EUR",
            f"Costs, base-year prices:   {res.total_costs_base:>18,.0f} EUR",
            f"Costs, escalated (nominal):{res.total_costs_nominal:>18,.0f} EUR",
        ]
        bounds = ESTIMATE_ACCURACY.get(project.get("estimate_type") or "Budgetary",
                                       ESTIMATE_ACCURACY["Budgetary"])
        lines += ["", "Sensitivity (first-year EUR per year):"]
        for label, val in sensitivity(inp, profile, 1 + bounds["upper_pct"] / 100.0):
            lines.append(f"  {label:<40}{val:>16,.0f}")
        self.lbl_fp_result.setText("\n".join(lines))
        self.lbl_fp_result.setToolTip(PLAN_METHOD_NOTE)

        self.fp_table.setRowCount(len(res.schedule))
        for row, s in enumerate(res.schedule):
            values = [str(s.year), s.stage, s.opening_balance, s.contributions, s.returns,
                      s.costs_paid, s.closing_balance]
            for col, v in enumerate(values):
                item = QTableWidgetItem(v if isinstance(v, str) else f"{v:,.0f}")
                if not isinstance(v, str):
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.fp_table.setItem(row, col, item)

    def _build_mwh_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        note = QLabel(
            "Levy per MWh generated that pays the contributions of the saved Funding Plan. "
            "Annual energy and your national decommissioning tariff are taken from "
            "Project Setup > Power Unit (MWh); fund inputs from Reports > Funding Plan."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color:#5a7a9a; font-style:italic; font-size:11px;")
        layout.addWidget(note)

        btn = QPushButton("Recalculate Levy")
        btn.clicked.connect(self._on_calculate_mwh)
        layout.addWidget(btn)

        top = QHBoxLayout()
        self.lbl_mwh_result = QLabel("")
        self.lbl_mwh_result.setWordWrap(True)
        self.lbl_mwh_result.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.lbl_mwh_result.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.lbl_mwh_result.setStyleSheet("font-family: Menlo, Consolas, \"Courier New\", monospace; font-size: 11px;")
        top.addWidget(self.lbl_mwh_result, 3)

        self.mwh_table = QTableWidget(0, 3)
        self.mwh_table.setHorizontalHeaderLabels(["Year", "Contribution (EUR)", "Levy (EUR/MWh)"])
        self.mwh_table.verticalHeader().setVisible(False)
        self.mwh_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.mwh_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        top.addWidget(self.mwh_table, 2)
        layout.addLayout(top, 1)

        ref = QLabel(REFERENCE_TARIFFS_NOTE)
        ref.setWordWrap(True)
        ref.setStyleSheet("color:#5a7a9a; font-style:italic; font-size:10px;")
        layout.addWidget(ref)
        self._mwh_tab_index = self.inner_tabs.addTab(tab, "EUR/MWh Levy")

    def _build_export_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        btn_matrix = QPushButton("Export ISDC Matrix (.xlsx)")
        btn_matrix.clicked.connect(self._on_export_matrix_xlsx)
        layout.addWidget(btn_matrix)

        btn_full_xlsx = QPushButton("Export Full Report (.xlsx)")
        btn_full_xlsx.clicked.connect(self._on_export_full_xlsx)
        layout.addWidget(btn_full_xlsx)

        btn_full_pdf = QPushButton("Export Full Report (.pdf)")
        btn_full_pdf.clicked.connect(self._on_export_full_pdf)
        layout.addWidget(btn_full_pdf)

        btn_fund_pdf = QPushButton("Export Funding Plan Note (.pdf)")
        btn_fund_pdf.clicked.connect(self._on_export_fund_pdf)
        layout.addWidget(btn_fund_pdf)

        btn_snapshot = QPushButton("Save Version Snapshot")
        btn_snapshot.clicked.connect(self._on_save_snapshot)
        layout.addWidget(btn_snapshot)

        self.lbl_export_status = QLabel("")
        self.lbl_export_status.setWordWrap(True)
        layout.addWidget(self.lbl_export_status)
        layout.addStretch()
        self.inner_tabs.addTab(tab, "Export")

    # ------------------------------------------------------------------
    def load_project(self, project_id: int):
        self.project_id = project_id
        project = self.db.get_project(project_id)
        if project:
            self._load_funding_plan_inputs(project)
            # The EUR/MWh levy only makes sense for electricity-generating facilities.
            self.inner_tabs.setTabVisible(self._mwh_tab_index, is_power_reactor(project.get("facility_type")))
            self._on_calculate_mwh()
        self._on_calculate()

    def _get_calc(self):
        project = self.db.get_project(self.project_id)
        return ISDCCalculator(dict(project) if project else {}, self.db), project

    def _on_calculate_mwh(self):
        self.mwh_table.setRowCount(0)
        if not self.project_id:
            return
        project = self.db.get_project(self.project_id)
        if not project or not is_power_reactor(project.get("facility_type")):
            return
        if not project.get("fp_shutdown_year"):
            self.lbl_mwh_result.setText("Set up and save the Funding Plan first (Reports > Funding Plan).")
            return
        if not float(project.get("annual_energy_mwh") or 0):
            self.lbl_mwh_result.setText("Enter the annual energy production in "
                                        "Project Setup > Power Unit (MWh).")
            return
        res = levy_for_project(project, self.db)
        if not res:
            self.lbl_mwh_result.setText("No costs entered yet — nothing to fund.")
            return
        currency = project.get("local_currency") or "EUR"
        rate = float(project.get("local_rate") or 1.0)
        lines = [
            f"Annual energy production:       {res.annual_energy_mwh:>16,.0f} MWh/yr",
            "",
            f"Required levy, first year:      {res.first_year_levy:>16,.3f} EUR/MWh",
        ]
        if abs(res.last_year_levy - res.first_year_levy) > 1e-6:
            lines.append(f"Required levy, last year:       {res.last_year_levy:>16,.3f} EUR/MWh")
            lines.append("  (payments grow each year as set in the Funding Plan)")
        lines.append(f"Constant levy (same every year):{res.constant_levy:>16,.3f} EUR/MWh")
        if currency != "EUR":
            lines.append(f"  = {res.first_year_levy * rate:,.3f} {currency}/MWh first year, "
                         f"{res.constant_levy * rate:,.3f} {currency}/MWh constant")
        lines.append("")
        if res.user_tariff_sufficient is None:
            lines.append("National decommissioning tariff: not entered (Project Setup > Power Unit).")
        else:
            lines.append(f"National decommissioning tariff:{res.user_tariff:>16,.3f} EUR/MWh")
            if res.user_tariff_sufficient:
                lines.append(f"  SUFFICIENT — fund ends with {res.user_tariff_final_balance_eur:,.0f} EUR")
            else:
                lines.append(f"  NOT SUFFICIENT — fund falls short by up to "
                             f"{res.user_tariff_shortfall_eur:,.0f} EUR")
        lines += [
            "",
            "Reference ranges (informational only):",
            f"  Decommissioning:   {REFERENCE_TARIFFS['decom_eur_per_mwh_low']:.2f} - "
            f"{REFERENCE_TARIFFS['decom_eur_per_mwh_high']:.2f} EUR/MWh",
            f"  Radioactive waste: {REFERENCE_TARIFFS['waste_eur_per_mwh_low']:.2f} - "
            f"{REFERENCE_TARIFFS['waste_eur_per_mwh_high']:.2f} EUR/MWh",
        ]
        self.lbl_mwh_result.setText("\n".join(lines))
        self.mwh_table.setRowCount(len(res.years))
        for row, y in enumerate(res.years):
            for col, text in enumerate((str(y.year), f"{y.contribution_eur:,.0f}", f"{y.levy_eur_per_mwh:,.3f}")):
                item = QTableWidgetItem(text)
                if col:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.mwh_table.setItem(row, col, item)

    def _on_calculate(self):
        if not self.project_id:
            return
        self._refresh_financial_summary()

    def _refresh_financial_summary(self):
        if not self.project_id:
            return
        calc, project = self._get_calc()
        financials = calc.compute_financials()
        currency = (project.get("local_currency") or "EUR") if project else "EUR"
        rate = float(project.get("local_rate") or 1.0) if project else 1.0

        lines = [
            f"Project: {project.get('name') if project else ''}",
            f"Estimate accuracy class: {financials.accuracy_class}",
            "",
            "Totals by Principal Activity (EUR):",
        ]
        for pa in financials.pa_totals:
            lines.append(f"  PA {pa.pa_code} {pa.title:<55} {pa.total_eur:>16,.0f}")
        lines += [
            "",
            f"{'Labour total':<40}{financials.labour_total_eur:>20,.0f} EUR",
            f"{'Investment total':<40}{financials.investment_total_eur:>20,.0f} EUR",
            f"{'Expenses total':<40}{financials.expenses_total_eur:>20,.0f} EUR",
            f"{'Contingency total':<40}{financials.contingency_total_eur:>20,.0f} EUR",
            f"{'GRAND TOTAL (EUR)':<40}{financials.grand_total_eur:>20,.0f} EUR",
        ]
        if currency and currency != "EUR":
            lines.append(f"{'GRAND TOTAL (' + currency + ')':<40}{financials.grand_total_eur * rate:>20,.0f} {currency}")
        lines += [
            f"{'Lower bound':<40}{financials.lower_bound:>20,.0f} EUR",
            f"{'Upper bound':<40}{financials.upper_bound:>20,.0f} EUR",
            f"{'NPV (base year)':<40}{financials.npv_total:>20,.0f} EUR",
        ]
        self.lbl_summary.setText("\n".join(lines))

    # ------------------------------------------------------------------
    def _choose_save_path(self, default_name, filter_str):
        path, _ = QFileDialog.getSaveFileName(self, "Save file", default_name, filter_str)
        return path

    def _on_export_matrix_xlsx(self):
        if not self.project_id:
            return
        path = self._choose_save_path("isdc_matrix.xlsx", "Excel Files (*.xlsx)")
        if not path:
            return
        try:
            excel_export.export_isdc_matrix(self.db, self.project_id, path)
            self.lbl_export_status.setText(f"Exported: {path}")
        except Exception as exc:
            QMessageBox.critical(self, "Export failed", str(exc))

    def _on_export_full_xlsx(self):
        if not self.project_id:
            return
        path = self._choose_save_path("isdc_full_report.xlsx", "Excel Files (*.xlsx)")
        if not path:
            return
        try:
            excel_export.export_full_report(self.db, self.project_id, path)
            self.lbl_export_status.setText(f"Exported: {path}")
        except Exception as exc:
            QMessageBox.critical(self, "Export failed", str(exc))

    def _on_export_full_pdf(self):
        if not self.project_id:
            return
        path = self._choose_save_path("isdc_full_report.pdf", "PDF Files (*.pdf)")
        if not path:
            return
        try:
            pdf_export.export_pdf_report(self.db, self.project_id, path)
            self.lbl_export_status.setText(f"Exported: {path}")
        except Exception as exc:
            QMessageBox.critical(self, "Export failed", str(exc))

    def _on_export_fund_pdf(self):
        if not self.project_id:
            return
        project = self.db.get_project(self.project_id)
        if not (project and project.get("fp_shutdown_year")):
            QMessageBox.information(self, "Funding plan",
                                    "Set up and save the funding plan first (Reports > Funding Plan).")
            return
        path = self._choose_save_path("funding_plan_note.pdf", "PDF Files (*.pdf)")
        if not path:
            return
        try:
            pdf_export.export_pdf_funding_plan_note(self.db, self.project_id, path)
            self.lbl_export_status.setText(f"Exported: {path}")
        except Exception as exc:
            QMessageBox.critical(self, "Export failed", str(exc))

    def _on_save_snapshot(self):
        if not self.project_id:
            return
        calc, _ = self._get_calc()
        financials = calc.compute_financials()
        version = self.db.save_version_snapshot(self.project_id, financials.grand_total_eur)
        self.lbl_export_status.setText(f"Saved snapshot version {version}.")