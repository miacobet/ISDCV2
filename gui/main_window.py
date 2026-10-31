"""
gui/main_window.py
=====================
Main application window: project sidebar + tabbed workspace.
"""

import traceback

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QListWidget,
    QListWidgetItem, QPushButton, QTabWidget, QLabel, QDialog, QMessageBox,
    QAction, QMenuBar, QSplitter
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from core.database import DatabaseManager
from gui.dialogs import NewProjectDialog, ISDCReferenceDialog
from gui.project_setup_tab import ProjectSetupTab
from gui.cost_matrix_tab import CostMatrixTab
from gui.phases_tab import PhasesTab
from gui.waste_tab import WasteTab
from gui.assumptions_tab import AssumptionsTab
from gui.reports_tab import ReportsTab


class MainWindow(QMainWindow):
    def __init__(self, db: DatabaseManager):
        super().__init__()
        self.db = db
        self.current_project_id = None
        self.setWindowTitle("ISDC Decommissioning Cost Estimation Tool")
        self.resize(1300, 850)
        self._build_menu()
        self._build_ui()
        self.refresh_project_list()
        self.statusBar().showMessage("Ready.")

    # ------------------------------------------------------------------
    def _build_menu(self):
        menubar = self.menuBar()
        help_menu = menubar.addMenu("Help")
        act_about = QAction("About", self)
        act_about.triggered.connect(self._show_about)
        help_menu.addAction(act_about)
        act_ref = QAction("ISDC Code Reference", self)
        act_ref.triggered.connect(self._show_isdc_reference)
        help_menu.addAction(act_ref)

    def _show_about(self):
        QMessageBox.information(
            self, "About",
            "ISDC Decommissioning Cost Estimation Tool\n\n"
            "Implements the general structure of the NEA/OECD International Structure "
            "for Decommissioning Costing (ISDC 2012, NEA No. 7088), with reference to "
            "IAEA GSG-1 waste classification and related IAEA safety guides.\n\n"
            "Author: Marian\n\n"
            "This tool is provided as an engineering aid. Users are responsible for "
            "verifying all cost-code definitions, assumptions, and results against "
            "the applicable methodology and their own national requirements."
        )

    def _show_isdc_reference(self):
        dlg = ISDCReferenceDialog(self)
        dlg.exec_()

    # ------------------------------------------------------------------
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        outer = QHBoxLayout(central)

        splitter = QSplitter(Qt.Horizontal)
        outer.addWidget(splitter)

        # Sidebar
        sidebar = QWidget()
        sb_layout = QVBoxLayout(sidebar)
        lbl = QLabel("Projects")
        lbl.setFont(QFont("Arial", 11, QFont.Bold))
        lbl.setStyleSheet("color:#1a3a5c;")
        sb_layout.addWidget(lbl)

        self.project_list = QListWidget()
        self.project_list.itemClicked.connect(self._on_project_selected)
        sb_layout.addWidget(self.project_list)

        btn_new = QPushButton("New Project")
        btn_new.clicked.connect(self._on_new_project)
        sb_layout.addWidget(btn_new)

        btn_edit = QPushButton("Edit Project Info")
        btn_edit.clicked.connect(self._on_edit_project)
        sb_layout.addWidget(btn_edit)

        btn_delete = QPushButton("Delete Project")
        btn_delete.setStyleSheet("background-color:#7a3030;")
        btn_delete.clicked.connect(self._on_delete_project)
        sb_layout.addWidget(btn_delete)

        splitter.addWidget(sidebar)

        # Workspace tabs
        self.tabs = QTabWidget()
        self.tabs.setElideMode(Qt.ElideNone)
        self.tabs.tabBar().setUsesScrollButtons(True)
        self.tab_setup = ProjectSetupTab(self.db, self)
        self.tab_matrix = CostMatrixTab(self.db, self)
        self.tab_phases = PhasesTab(self.db, self)
        self.tab_waste = WasteTab(self.db, self)
        self.tab_assumptions = AssumptionsTab(self.db, self)
        self.tab_reports = ReportsTab(self.db, self)

        self.tabs.addTab(self.tab_setup, "Project Setup")
        self.tabs.addTab(self.tab_matrix, "ISDC Cost Matrix")
        self.tabs.addTab(self.tab_phases, "Phases & Timeline")
        self.tabs.addTab(self.tab_waste, "Waste Streams")
        self.tabs.addTab(self.tab_assumptions, "Assumptions Register")
        self.tabs.addTab(self.tab_reports, "Reports")
        self.tabs.currentChanged.connect(self._on_tab_changed)

        splitter.addWidget(self.tabs)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 4)

    # ------------------------------------------------------------------
    def refresh_project_list(self):
        self.project_list.clear()
        for p in self.db.get_projects():
            item = QListWidgetItem(f"{p['name']}  [{p.get('facility_type') or ''}]")
            item.setData(Qt.UserRole, p["id"])
            self.project_list.addItem(item)
            if p["id"] == self.current_project_id:
                self.project_list.setCurrentItem(item)

    def _on_project_selected(self, item):
        project_id = item.data(Qt.UserRole)
        self._load_project(project_id)

    def _load_project(self, project_id):
        self.current_project_id = project_id
        try:
            self.tab_setup.load_project(project_id)
            self.tab_matrix.load_project(project_id)
            self.tab_phases.load_project(project_id)
            self.tab_waste.load_project(project_id)
            self.tab_assumptions.load_project(project_id)
            self.tab_reports.load_project(project_id)
            project = self.db.get_project(project_id)
            self.statusBar().showMessage(f"Loaded project: {project.get('name') if project else ''}")
        except Exception:
            QMessageBox.critical(self, "Error loading project", traceback.format_exc())

    def _on_tab_changed(self, index):
        if self.current_project_id and self.tabs.widget(index) is self.tab_reports:
            self.tab_reports.load_project(self.current_project_id)

    # ------------------------------------------------------------------
    def _on_new_project(self):
        dlg = NewProjectDialog(self)
        if dlg.exec_() == QDialog.Accepted:
            try:
                data = dlg.get_data()
                project_id = self.db.create_project(data)
                self.refresh_project_list()
                self._select_project_in_list(project_id)
                self._load_project(project_id)
            except Exception:
                QMessageBox.critical(self, "Error creating project", traceback.format_exc())

    def _on_edit_project(self):
        if not self.current_project_id:
            QMessageBox.information(self, "No project", "Select a project first.")
            return
        project = self.db.get_project(self.current_project_id)
        dlg = NewProjectDialog(self, existing=project)
        if dlg.exec_() == QDialog.Accepted:
            try:
                data = dlg.get_data()
                self.db.update_project(self.current_project_id, data)
                self.refresh_project_list()
                self._load_project(self.current_project_id)
            except Exception:
                QMessageBox.critical(self, "Error updating project", traceback.format_exc())

    def _on_delete_project(self):
        if not self.current_project_id:
            QMessageBox.information(self, "No project", "Select a project first.")
            return
        reply = QMessageBox.question(
            self, "Confirm delete",
            "Delete this project and all its data? This cannot be undone.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.db.delete_project(self.current_project_id)
            self.current_project_id = None
            self.refresh_project_list()

    def _select_project_in_list(self, project_id):
        for i in range(self.project_list.count()):
            item = self.project_list.item(i)
            if item.data(Qt.UserRole) == project_id:
                self.project_list.setCurrentItem(item)
                return