"""
gui/dialogs.py
===============
Dialogs: new project creation, phase editing, waste stream editing,
and the ISDC code reference viewer.
"""

import datetime
import traceback

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QSpinBox, QDoubleSpinBox, QPushButton, QLabel, QDialogButtonBox,
    QMessageBox, QTreeWidget, QTreeWidgetItem
)
from PyQt5.QtCore import Qt

from core.facility_profiles import get_facility_type_list
from core.isdc_data import ISDC_HIERARCHY

STRATEGIES = ["DECON (immediate dismantling)", "SAFSTOR (deferred dismantling)", "ENTOMBMENT"]
PLAN_TYPES = ["Initial plan", "Preliminary plan", "Final plan"]
ESTIMATE_TYPES = ["Order-of-magnitude", "Budgetary", "Definitive"]


class NewProjectDialog(QDialog):
    def __init__(self, parent=None, existing=None):
        super().__init__(parent)
        self.existing = existing or {}
        self.setWindowTitle("New Decommissioning Cost Estimate Project" if not existing
                             else "Edit Project")
        self.setMinimumWidth(520)
        self._build_ui()
        if existing:
            self._load_existing()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)

        self.ed_name = QLineEdit()
        form.addRow("Project name *", self.ed_name)

        self.ed_author = QLineEdit("Marian")
        form.addRow("Author / prepared by", self.ed_author)

        self.cb_facility = QComboBox()
        for code, label in get_facility_type_list():
            self.cb_facility.addItem(f"{code} — {label}", code)
        form.addRow("Facility type *", self.cb_facility)

        self.ed_unit = QLineEdit()
        form.addRow("Unit / facility identifier", self.ed_unit)

        self.cb_strategy = QComboBox()
        self.cb_strategy.addItems(STRATEGIES)
        form.addRow("Decommissioning strategy", self.cb_strategy)

        self.cb_plan_type = QComboBox()
        self.cb_plan_type.addItems(PLAN_TYPES)
        form.addRow("Plan type", self.cb_plan_type)

        self.cb_estimate_type = QComboBox()
        self.cb_estimate_type.addItems(ESTIMATE_TYPES)
        self.cb_estimate_type.setCurrentText("Budgetary")
        form.addRow("Estimate accuracy class", self.cb_estimate_type)

        self.sp_base_year = QSpinBox()
        self.sp_base_year.setRange(1950, 2200)
        self.sp_base_year.setValue(datetime.date.today().year)
        form.addRow("Base year (cost basis)", self.sp_base_year)

        self.sp_conservation = QSpinBox()
        self.sp_conservation.setRange(0, 200)
        form.addRow("Conservation / safe-storage period (years)", self.sp_conservation)

        layout.addLayout(form)

        note = QLabel(
            "Additional project details (organisation, financial parameters, national "
            "requirements, power-unit data) can be completed on the Project Setup tab "
            "after the project is created."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color:#5a7a9a; font-style:italic; font-size:10px;")
        layout.addWidget(note)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load_existing(self):
        e = self.existing
        self.ed_name.setText(e.get("name") or "")
        self.ed_author.setText(e.get("author") or "Marian")
        idx = self.cb_facility.findData(e.get("facility_type"))
        if idx >= 0:
            self.cb_facility.setCurrentIndex(idx)
        self.ed_unit.setText(e.get("unit_id") or "")
        if e.get("strategy"):
            self.cb_strategy.setCurrentText(e["strategy"])
        if e.get("plan_type"):
            self.cb_plan_type.setCurrentText(e["plan_type"])
        if e.get("estimate_type"):
            self.cb_estimate_type.setCurrentText(e["estimate_type"])
        if e.get("base_year"):
            self.sp_base_year.setValue(int(e["base_year"]))
        if e.get("conservation_years") is not None:
            self.sp_conservation.setValue(int(e["conservation_years"]))

    def _on_accept(self):
        if not self.ed_name.text().strip():
            QMessageBox.warning(self, "Missing data", "Please enter a project name.")
            return
        try:
            self.accept()
        except Exception:
            QMessageBox.critical(self, "Error", traceback.format_exc())

    def get_data(self):
        data = {
            "name": self.ed_name.text().strip(),
            "author": self.ed_author.text().strip() or "Marian",
            "facility_type": self.cb_facility.currentData(),
            "unit_id": self.ed_unit.text().strip(),
            "strategy": self.cb_strategy.currentText(),
            "plan_type": self.cb_plan_type.currentText(),
            "estimate_type": self.cb_estimate_type.currentText(),
            "base_year": self.sp_base_year.value(),
            "conservation_years": self.sp_conservation.value(),
        }
        if self.existing.get("id"):
            data["id"] = self.existing["id"]
        return data


class PhaseDialog(QDialog):
    def __init__(self, project_id, base_year, existing=None, parent=None):
        super().__init__(parent)
        self.project_id = project_id
        self.existing = existing or {}
        self.setWindowTitle("Edit Phase" if existing else "Add Phase")
        self.setMinimumWidth(400)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.ed_name = QLineEdit(self.existing.get("phase_name", ""))
        form.addRow("Phase name", self.ed_name)

        self.cb_type = QComboBox()
        self.cb_type.addItems(["Decommissioning", "Conservation", "Pre-decommissioning", "Post-decommissioning"])
        if self.existing.get("phase_type"):
            self.cb_type.setCurrentText(self.existing["phase_type"])
        form.addRow("Phase type", self.cb_type)

        self.sp_start = QSpinBox()
        self.sp_start.setRange(1950, 2300)
        self.sp_start.setValue(int(self.existing.get("start_year", base_year)))
        form.addRow("Start year", self.sp_start)

        self.sp_end = QSpinBox()
        self.sp_end.setRange(1950, 2300)
        self.sp_end.setValue(int(self.existing.get("end_year", base_year + 1)))
        form.addRow("End year", self.sp_end)

        self.sp_order = QSpinBox()
        self.sp_order.setRange(0, 999)
        self.sp_order.setValue(int(self.existing.get("sort_order", 0)))
        form.addRow("Sort order", self.sp_order)

        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_accept(self):
        if self.sp_end.value() < self.sp_start.value():
            QMessageBox.warning(self, "Invalid range", "End year must not be before start year.")
            return
        if not self.ed_name.text().strip():
            QMessageBox.warning(self, "Missing data", "Please enter a phase name.")
            return
        self.accept()

    def get_data(self):
        data = {
            "project_id": self.project_id,
            "phase_name": self.ed_name.text().strip(),
            "phase_type": self.cb_type.currentText(),
            "start_year": self.sp_start.value(),
            "end_year": self.sp_end.value(),
            "sort_order": self.sp_order.value(),
        }
        if self.existing.get("id"):
            data["id"] = self.existing["id"]
        return data


class WasteStreamDialog(QDialog):
    WASTE_CLASSES = ["HLW", "ILW", "LLW", "VLLW", "VSLW", "EW"]

    def __init__(self, project_id, existing=None, parent=None):
        super().__init__(parent)
        self.project_id = project_id
        self.existing = existing or {}
        self.setWindowTitle("Edit Waste Stream" if existing else "Add Waste Stream")
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.cb_class = QComboBox()
        self.cb_class.addItems(self.WASTE_CLASSES)
        if self.existing.get("waste_class"):
            self.cb_class.setCurrentText(self.existing["waste_class"])
        form.addRow("Waste class (IAEA GSG-1)", self.cb_class)

        self.ed_desc = QLineEdit(self.existing.get("description", ""))
        form.addRow("Description", self.ed_desc)

        self.sp_volume = QDoubleSpinBox()
        self.sp_volume.setRange(0, 1e9)
        self.sp_volume.setDecimals(2)
        self.sp_volume.setValue(float(self.existing.get("volume_m3", 0) or 0))
        form.addRow("Estimated volume (m³)", self.sp_volume)

        self.ed_activity = QLineEdit(self.existing.get("activity_notes", ""))
        form.addRow("Activity / characterisation notes", self.ed_activity)

        self.ed_dest = QLineEdit(self.existing.get("destination", ""))
        form.addRow("Planned destination / route", self.ed_dest)

        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_data(self):
        data = {
            "project_id": self.project_id,
            "waste_class": self.cb_class.currentText(),
            "description": self.ed_desc.text().strip(),
            "volume_m3": self.sp_volume.value(),
            "activity_notes": self.ed_activity.text().strip(),
            "destination": self.ed_dest.text().strip(),
        }
        if self.existing.get("id"):
            data["id"] = self.existing["id"]
        return data


class ISDCReferenceDialog(QDialog):
    """Read-only reference viewer for the full ISDC code hierarchy."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ISDC Code Reference")
        self.resize(700, 600)
        layout = QVBoxLayout(self)

        note = QLabel(
            "NEA/OECD International Structure for Decommissioning Costing (ISDC 2012, NEA No. 7088), "
            "Appendix A. Detailed definitions of each item are in Appendix D of the publication."
        )
        note.setWordWrap(True)
        note.setStyleSheet("font-style:italic; color:#5a7a9a; font-size:10px;")
        layout.addWidget(note)

        tree = QTreeWidget()
        tree.setHeaderLabels(["Code", "Title"])
        tree.setColumnWidth(0, 110)
        for pa_code, pa in ISDC_HIERARCHY.items():
            pa_item = QTreeWidgetItem([pa_code, pa["title"]])
            for l2_code, (l2_title, l3_list) in pa["groups"].items():
                l2_item = QTreeWidgetItem([l2_code, l2_title])
                for l3_code, l3_title in l3_list:
                    l2_item.addChild(QTreeWidgetItem([l3_code, l3_title]))
                pa_item.addChild(l2_item)
            tree.addTopLevelItem(pa_item)
        tree.expandToDepth(0)
        layout.addWidget(tree)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
