"""
gui/reports_tab.py
====================
Tab 6 — Reports. Financial Summary, Fund Adequacy, EUR/MWh Levy and
Export sub-tabs.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget, QLabel, QFormLayout,
    QDoubleSpinBox, QPushButton, QFileDialog, QMessageBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from core.database import DatabaseManager
from core.calculator import ISDCCalculator, REFERENCE_TARIFFS_NOTE
from export import excel_export, pdf_export


class ReportsTab(QWidget):
    _costs_incurred_eur = 0.0
    _fund_balance_eur = 0.0
    _years_remaining = 0.0

    def __init__(self, db: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db = db
        self.main_window = parent
        self.project_id = None
        self._costs_incurred_eur = 0.0
        self._fund_balance_eur = 0.0
        self._years_remaining = 0.0
        self._last_fund_result = None
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
        self._build_fund_adequacy_tab()
        self._build_mwh_tab()
        self._build_export_tab()

    # ------------------------------------------------------------------
    def _build_financial_summary_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.lbl_summary = QLabel("Load a project to view the financial summary.")
        self.lbl_summary.setWordWrap(True)
        self.lbl_summary.setStyleSheet("font-family: monospace; font-size: 11px;")
        layout.addWidget(self.lbl_summary)
        layout.addStretch()
        self.inner_tabs.addTab(tab, "Financial Summary")

    def _build_fund_adequacy_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        form = QFormLayout()

        self.sp_costs_incurred = QDoubleSpinBox()
        self.sp_costs_incurred.setRange(0, 1e13)
        self.sp_costs_incurred.setSuffix(" EUR")
        form.addRow("Costs incurred to date", self.sp_costs_incurred)

        self.sp_fund_balance = QDoubleSpinBox()
        self.sp_fund_balance.setRange(0, 1e13)
        self.sp_fund_balance.setSuffix(" EUR")
        form.addRow("Current fund balance", self.sp_fund_balance)

        self.sp_years_remaining = QDoubleSpinBox()
        self.sp_years_remaining.setRange(0, 200)
        self.sp_years_remaining.setDecimals(1)
        form.addRow("Years remaining to completion", self.sp_years_remaining)

        layout.addLayout(form)

        btn = QPushButton("Calculate Fund Adequacy")
        btn.clicked.connect(self._on_fund_tab_calculate)
        layout.addWidget(btn)

        self.lbl_fund_result = QLabel("")
        self.lbl_fund_result.setWordWrap(True)
        self.lbl_fund_result.setStyleSheet("font-family: monospace; font-size: 11px;")
        layout.addWidget(self.lbl_fund_result)
        layout.addStretch()
        self.inner_tabs.addTab(tab, "Fund Adequacy")

    def _build_mwh_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        note = QLabel(REFERENCE_TARIFFS_NOTE)
        note.setWordWrap(True)
        note.setStyleSheet("color:#5a7a9a; font-style:italic; font-size:10px;")
        layout.addWidget(note)

        form = QFormLayout()
        self.sp_mwh_energy = QDoubleSpinBox()
        self.sp_mwh_energy.setRange(0, 1e8)
        self.sp_mwh_energy.setSuffix(" MWh/yr")
        form.addRow("Annual energy production", self.sp_mwh_energy)

        self.sp_mwh_years = QDoubleSpinBox()
        self.sp_mwh_years.setRange(0, 100)
        self.sp_mwh_years.setDecimals(1)
        form.addRow("Remaining operational years", self.sp_mwh_years)

        self.sp_mwh_fund = QDoubleSpinBox()
        self.sp_mwh_fund.setRange(0, 1e13)
        self.sp_mwh_fund.setSuffix(" EUR")
        form.addRow("Current fund balance", self.sp_mwh_fund)

        layout.addLayout(form)

        btn = QPushButton("Calculate Required Levy")
        btn.clicked.connect(self._on_calculate_mwh)
        layout.addWidget(btn)

        self.lbl_mwh_result = QLabel("")
        self.lbl_mwh_result.setWordWrap(True)
        self.lbl_mwh_result.setStyleSheet("font-family: monospace; font-size: 11px;")
        layout.addWidget(self.lbl_mwh_result)
        layout.addStretch()
        self.inner_tabs.addTab(tab, "EUR/MWh Levy")

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

        btn_fund_pdf = QPushButton("Export Fund Adequacy Note (.pdf)")
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
            self.sp_mwh_energy.setValue(float(project.get("annual_energy_mwh") or 0))
            self.sp_mwh_years.setValue(float(project.get("remaining_op_years") or 0))
        self._on_calculate()

    def _get_calc(self):
        project = self.db.get_project(self.project_id)
        return ISDCCalculator(dict(project) if project else {}, self.db), project

    def _on_calculate_mwh(self):
        if not self.project_id:
            return
        calc, project = self._get_calc()
        result = calc.compute_mwh_levy(
            self.sp_mwh_energy.value(), self.sp_mwh_years.value(), self.sp_mwh_fund.value(),
        )
        currency = (project.get("local_currency") or "EUR") if project else "EUR"
        lines = [
            f"Remaining liability:          {result.remaining_liability_eur:>16,.0f} EUR",
            f"Required annual fund contribution: {result.annual_fund_contribution_eur:>12,.0f} EUR",
            f"Required levy:                 {result.required_levy_eur_per_mwh:>16,.4f} EUR/MWh",
        ]
        if currency and currency != "EUR":
            lines.append(f"Required levy:                 {result.required_levy_local_per_mwh:>16,.4f} {currency}/MWh")
        lines += [
            "",
            "Reference tariffs (informational only, see note above):",
            f"  Decommissioning: {result.reference_decom_tariff_low:.2f} - {result.reference_decom_tariff_high:.2f} EUR/MWh",
            f"  Radioactive waste: {result.reference_waste_tariff_low:.2f} - {result.reference_waste_tariff_high:.2f} EUR/MWh",
        ]
        self.lbl_mwh_result.setText("\n".join(lines))

    def _on_fund_tab_calculate(self):
        self._costs_incurred_eur = self.sp_costs_incurred.value()
        self._fund_balance_eur = self.sp_fund_balance.value()
        self._years_remaining = self.sp_years_remaining.value()
        calc, project = self._get_calc()
        result = calc.compute_fund_adequacy(
            self._costs_incurred_eur, self._fund_balance_eur, self._years_remaining
        )
        self._last_fund_result = result
        lines = [
            f"Total estimated cost:        {result['total_estimated_cost_eur']:>16,.0f} EUR",
            f"Costs incurred to date:      {result['costs_incurred_eur']:>16,.0f} EUR",
            f"Remaining liability:         {result['remaining_liability_eur']:>16,.0f} EUR",
            f"NPV of remaining liability:  {result['npv_remaining_eur']:>16,.0f} EUR",
            f"  Lower bound:               {result['lower_bound_npv_eur']:>16,.0f} EUR",
            f"  Upper bound:               {result['upper_bound_npv_eur']:>16,.0f} EUR",
            f"Current fund balance:        {result['current_fund_balance_eur']:>16,.0f} EUR",
            f"Shortfall / surplus:         {result['shortfall_surplus_eur']:>16,.0f} EUR",
            f"Required annual provision:   {result['annual_provision_eur']:>16,.0f} EUR/yr",
        ]
        self.lbl_fund_result.setText("\n".join(lines))
        return result

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
            fund_data = self._last_fund_result
            excel_export.export_full_report(self.db, self.project_id, path, fund_data=fund_data)
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
            pdf_export.export_pdf_report(self.db, self.project_id, path, fund_data=self._last_fund_result)
            self.lbl_export_status.setText(f"Exported: {path}")
        except Exception as exc:
            QMessageBox.critical(self, "Export failed", str(exc))

    def _on_export_fund_pdf(self):
        if not self.project_id:
            return
        result = self._on_fund_tab_calculate()
        path = self._choose_save_path("fund_adequacy_note.pdf", "PDF Files (*.pdf)")
        if not path:
            return
        try:
            pdf_export.export_pdf_fund_note(self.db, self.project_id, path, result)
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