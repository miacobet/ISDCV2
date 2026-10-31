"""
gui/project_setup_tab.py
=========================
Tab 1 — Project Setup. Full project metadata, financial parameters,
national requirements, and power-unit data for the EUR/MWh levy
calculation. Every field carries a short description.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QSpinBox, QDoubleSpinBox, QTextEdit, QLabel, QTabWidget, QPushButton,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from core.database import DatabaseManager
from core.facility_profiles import get_facility_type_list, is_power_reactor
from gui.dialogs import STRATEGIES, PLAN_TYPES, ESTIMATE_TYPES


def field_with_desc(widget, description: str):
    """Wraps a widget with a small italic description label underneath."""
    container = QWidget()
    v = QVBoxLayout(container)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(1)
    v.addWidget(widget)
    desc = QLabel(description)
    desc.setProperty("desc", "true")
    desc.setWordWrap(True)
    desc.setStyleSheet("color:#5a7a9a; font-style:italic; font-size:9px;")
    v.addWidget(desc)
    return container


class ProjectSetupTab(QWidget):
    def __init__(self, db: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db = db
        self.main_window = parent
        self.project_id = None
        self._loading = False
        self._build_ui()

    # ------------------------------------------------------------------
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)

        title = QLabel("Project Setup")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        title.setStyleSheet("color:#1a3a5c;")
        outer.addWidget(title)

        self.inner_tabs = QTabWidget()
        self.inner_tabs.setElideMode(Qt.ElideNone)
        self.inner_tabs.tabBar().setUsesScrollButtons(True)
        self.inner_tabs.tabBar().setExpanding(False)
        outer.addWidget(self.inner_tabs)

        self._build_operator_tab()
        self._build_strategy_tab()
        self._build_financial_tab()
        self._build_national_tab()
        self._build_power_tab()

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.btn_save = QPushButton("Save Project Details")
        self.btn_save.clicked.connect(self._on_save)
        btn_row.addWidget(self.btn_save)
        outer.addLayout(btn_row)

    # ------------------------------------------------------------------
    def _build_operator_tab(self):
        tab = QWidget()
        form = QFormLayout(tab)

        self.ed_organisation = QLineEdit()
        form.addRow("Organisation *", field_with_desc(
            self.ed_organisation, "Legal name of the organisation responsible for the facility. Enter your own."))

        self.ed_contact = QLineEdit()
        form.addRow("Contact person", field_with_desc(
            self.ed_contact, "Name and role of the person responsible for this estimate."))

        self.ed_address = QLineEdit()
        form.addRow("Address", field_with_desc(
            self.ed_address, "Organisation or site postal address."))

        self.ed_country = QLineEdit()
        form.addRow("Country", field_with_desc(
            self.ed_country, "Country where the facility is located. Leave blank if not applicable."))

        self.ed_authority = QLineEdit()
        form.addRow("Competent authority", field_with_desc(
            self.ed_authority, "Name of the regulatory body with jurisdiction over this facility."))

        self.ed_site = QLineEdit()
        form.addRow("Site name / identifier", field_with_desc(
            self.ed_site, "User-defined site name or identifier. No default is assumed."))

        self.cb_facility_disp = QComboBox()
        for code, label in get_facility_type_list():
            self.cb_facility_disp.addItem(f"{code} — {label}", code)
        self.cb_facility_disp.setEnabled(False)
        form.addRow("Facility type", field_with_desc(
            self.cb_facility_disp, "Set at project creation. To change it, create a new project."))

        self.inner_tabs.addTab(tab, "Operator && Facility")

    def _build_strategy_tab(self):
        tab = QWidget()
        form = QFormLayout(tab)

        self.cb_strategy = QComboBox()
        self.cb_strategy.addItems(STRATEGIES)
        form.addRow("Decommissioning strategy", field_with_desc(
            self.cb_strategy, "DECON: immediate dismantling. SAFSTOR: deferred dismantling after a "
            "safe-storage period. ENTOMBMENT: permanent encasement in place."))

        self.cb_plan_type = QComboBox()
        self.cb_plan_type.addItems(PLAN_TYPES)
        form.addRow("Plan type", field_with_desc(
            self.cb_plan_type, "Initial plan: prepared before/at start of operation. Preliminary plan: "
            "updated during operation. Final plan: prepared ahead of actual decommissioning."))

        self.cb_estimate_type = QComboBox()
        self.cb_estimate_type.addItems(ESTIMATE_TYPES)
        form.addRow("Estimate accuracy class", field_with_desc(
            self.cb_estimate_type, "Order-of-magnitude (-30%/+50%), Budgetary (-15%/+30%), or "
            "Definitive (-5%/+15%) per ISDC Section 2.2 / Appendix C uncertainty guidance."))

        self.ed_end_state = QLineEdit()
        form.addRow("Planned end state", field_with_desc(
            self.ed_end_state, "Describe the intended end state of the site (e.g. unrestricted release, "
            "restricted use, greenfield)."))

        self.sp_base_year = QSpinBox()
        self.sp_base_year.setRange(1950, 2300)
        form.addRow("Base year", field_with_desc(
            self.sp_base_year, "Reference year for all costs in this estimate (constant-money basis)."))

        self.sp_conservation = QSpinBox()
        self.sp_conservation.setRange(0, 200)
        form.addRow("Conservation period (years)", field_with_desc(
            self.sp_conservation, "Length of any safe-storage/conservation period before final dismantling, if applicable."))

        self.ed_notes = QTextEdit()
        self.ed_notes.setMaximumHeight(80)
        form.addRow("General notes", field_with_desc(
            self.ed_notes, "Any additional context for this estimate."))

        self.inner_tabs.addTab(tab, "Strategy && Plan Type")

    def _build_financial_tab(self):
        tab = QWidget()
        form = QFormLayout(tab)

        lbl_primary = QLabel("Primary currency: EUR (fixed)")
        lbl_primary.setStyleSheet("font-weight:bold; color:#1a3a5c;")
        form.addRow("Primary currency", lbl_primary)

        self.ed_local_currency = QLineEdit()
        form.addRow("Local currency (secondary display)", field_with_desc(
            self.ed_local_currency, "Optional local-currency code (e.g. RON, USD, GBP) shown alongside EUR "
            "figures for information only."))

        self.sp_local_rate = QDoubleSpinBox()
        self.sp_local_rate.setRange(0.0001, 100000)
        self.sp_local_rate.setDecimals(4)
        self.sp_local_rate.setValue(1.0)
        form.addRow("Exchange rate (local / EUR)", field_with_desc(
            self.sp_local_rate, "Units of local currency per 1 EUR. Used only to display an informational "
            "secondary-currency conversion."))

        self.sp_discount_rate = QDoubleSpinBox()
        self.sp_discount_rate.setRange(0, 30)
        self.sp_discount_rate.setDecimals(2)
        self.sp_discount_rate.setSuffix(" %")
        self.sp_discount_rate.setValue(3.0)
        form.addRow("Real discount rate", field_with_desc(
            self.sp_discount_rate, "Annual real discount rate used for NPV calculations of future cash flows."))

        self.sp_inflation_rate = QDoubleSpinBox()
        self.sp_inflation_rate.setRange(0, 50)
        self.sp_inflation_rate.setDecimals(2)
        self.sp_inflation_rate.setSuffix(" %")
        self.sp_inflation_rate.setValue(2.0)
        form.addRow("Assumed long-term inflation", field_with_desc(
            self.sp_inflation_rate, "Informational — long-term inflation assumption, if escalation modelling is used."))

        self.inner_tabs.addTab(tab, "Financial Parameters")

    def _build_national_tab(self):
        tab = QWidget()
        form = QFormLayout(tab)

        note = QLabel(
            "These fields are free text. Enter the decommissioning safety and financing requirements "
            "applicable in your jurisdiction. The tool does not assume any specific national regulation."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color:#5a7a9a; font-style:italic; font-size:10px;")
        form.addRow(note)

        self.ed_national_req = QTextEdit()
        self.ed_national_req.setMaximumHeight(90)
        form.addRow("Decommissioning safety requirements", field_with_desc(
            self.ed_national_req, "Describe the applicable national decommissioning safety regulation(s), "
            "if any, that govern this estimate."))

        self.ed_national_fund = QTextEdit()
        self.ed_national_fund.setMaximumHeight(90)
        form.addRow("Fund / financing requirements", field_with_desc(
            self.ed_national_fund, "Describe the applicable national financial-assurance / "
            "decommissioning-fund regulation(s), if any."))

        self.inner_tabs.addTab(tab, "National Requirements")

    def _build_power_tab(self):
        tab = QWidget()
        form = QFormLayout(tab)

        note = QLabel(
            "These fields apply to power-generating reactor facility types and feed the EUR/MWh "
            "levy calculation on the Reports tab."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color:#5a7a9a; font-style:italic; font-size:10px;")
        form.addRow(note)

        self.sp_net_capacity = QDoubleSpinBox()
        self.sp_net_capacity.setRange(0, 20000)
        self.sp_net_capacity.setDecimals(1)
        self.sp_net_capacity.setSuffix(" MWe")
        form.addRow("Net electrical capacity", field_with_desc(
            self.sp_net_capacity, "Net electrical output of the unit, in MWe."))

        self.sp_annual_energy = QDoubleSpinBox()
        self.sp_annual_energy.setRange(0, 1e8)
        self.sp_annual_energy.setDecimals(0)
        self.sp_annual_energy.setSuffix(" MWh/yr")
        form.addRow("Annual energy production", field_with_desc(
            self.sp_annual_energy, "Average expected annual electricity production, in MWh/year."))

        self.sp_remaining_years = QDoubleSpinBox()
        self.sp_remaining_years.setRange(0, 100)
        self.sp_remaining_years.setDecimals(1)
        form.addRow("Remaining operational years", field_with_desc(
            self.sp_remaining_years, "Estimated remaining years of power operation before shutdown."))

        self.sp_user_decom_tariff = QDoubleSpinBox()
        self.sp_user_decom_tariff.setRange(0, 1000)
        self.sp_user_decom_tariff.setDecimals(3)
        self.sp_user_decom_tariff.setSuffix(" EUR/MWh")
        form.addRow("National decommissioning tariff (if applicable)", field_with_desc(
            self.sp_user_decom_tariff, "Decommissioning levy rate required by your applicable national "
            "legislation, if any. Enter your own rate — the tool does not assume a value."))

        self.sp_user_waste_tariff = QDoubleSpinBox()
        self.sp_user_waste_tariff.setRange(0, 1000)
        self.sp_user_waste_tariff.setDecimals(3)
        self.sp_user_waste_tariff.setSuffix(" EUR/MWh")
        form.addRow("National radioactive waste tariff (if applicable)", field_with_desc(
            self.sp_user_waste_tariff, "Radioactive waste management levy rate required by your applicable "
            "national legislation, if any."))

        self._power_tab_index = self.inner_tabs.addTab(tab, "Power Unit (MWh)")

    # ------------------------------------------------------------------
    def load_project(self, project_id: int):
        self.project_id = project_id
        self._loading = True
        p = self.db.get_project(project_id)
        if p:
            self.ed_organisation.setText(p.get("organisation") or "")
            self.ed_contact.setText(p.get("contact_person") or "")
            self.ed_address.setText(p.get("address") or "")
            self.ed_country.setText(p.get("country") or "")
            self.ed_authority.setText(p.get("competent_authority") or "")
            self.ed_site.setText(p.get("site") or "")
            idx = self.cb_facility_disp.findData(p.get("facility_type"))
            if idx >= 0:
                self.cb_facility_disp.setCurrentIndex(idx)
            # Graded approach: electricity/levy data only applies to power reactors.
            self.inner_tabs.setTabVisible(self._power_tab_index, is_power_reactor(p.get("facility_type")))

            if p.get("strategy"):
                self.cb_strategy.setCurrentText(p["strategy"])
            if p.get("plan_type"):
                self.cb_plan_type.setCurrentText(p["plan_type"])
            if p.get("estimate_type"):
                self.cb_estimate_type.setCurrentText(p["estimate_type"])
            self.ed_end_state.setText(p.get("end_state") or "")
            if p.get("base_year"):
                self.sp_base_year.setValue(int(p["base_year"]))
            if p.get("conservation_years") is not None:
                self.sp_conservation.setValue(int(p["conservation_years"]))
            self.ed_notes.setPlainText(p.get("notes") or "")

            self.ed_local_currency.setText(p.get("local_currency") or "")
            self.sp_local_rate.setValue(float(p.get("local_rate") or 1.0))
            self.sp_discount_rate.setValue(float(p.get("discount_rate") or 3.0))
            self.sp_inflation_rate.setValue(float(p.get("inflation_rate") or 2.0))

            self.ed_national_req.setPlainText(p.get("national_requirements") or "")
            self.ed_national_fund.setPlainText(p.get("national_fund_regulation") or "")

            self.sp_net_capacity.setValue(float(p.get("net_capacity_mwe") or 0))
            self.sp_annual_energy.setValue(float(p.get("annual_energy_mwh") or 0))
            self.sp_remaining_years.setValue(float(p.get("remaining_op_years") or 0))
            self.sp_user_decom_tariff.setValue(float(p.get("user_decom_tariff") or 0))
            self.sp_user_waste_tariff.setValue(float(p.get("user_waste_tariff") or 0))
        self._loading = False

    def _on_save(self):
        if not self.project_id:
            return
        data = {
            "organisation": self.ed_organisation.text().strip(),
            "contact_person": self.ed_contact.text().strip(),
            "address": self.ed_address.text().strip(),
            "country": self.ed_country.text().strip(),
            "competent_authority": self.ed_authority.text().strip(),
            "site": self.ed_site.text().strip(),
            "strategy": self.cb_strategy.currentText(),
            "plan_type": self.cb_plan_type.currentText(),
            "estimate_type": self.cb_estimate_type.currentText(),
            "end_state": self.ed_end_state.text().strip(),
            "base_year": self.sp_base_year.value(),
            "conservation_years": self.sp_conservation.value(),
            "notes": self.ed_notes.toPlainText().strip(),
            "local_currency": self.ed_local_currency.text().strip() or "EUR",
            "local_rate": self.sp_local_rate.value(),
            "discount_rate": self.sp_discount_rate.value(),
            "inflation_rate": self.sp_inflation_rate.value(),
            "national_requirements": self.ed_national_req.toPlainText().strip(),
            "national_fund_regulation": self.ed_national_fund.toPlainText().strip(),
            "net_capacity_mwe": self.sp_net_capacity.value(),
            "annual_energy_mwh": self.sp_annual_energy.value(),
            "remaining_op_years": self.sp_remaining_years.value(),
            "user_decom_tariff": self.sp_user_decom_tariff.value(),
            "user_waste_tariff": self.sp_user_waste_tariff.value(),
        }
        self.db.update_project(self.project_id, data)
        if self.main_window:
            self.main_window.refresh_project_list()
            self.main_window.statusBar().showMessage("Project details saved.", 4000)