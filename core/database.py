"""
core/database.py
=================
SQLite persistence layer for the ISDC Decommissioning Cost Estimation Tool.
"""

import sqlite3
import datetime
from typing import Optional, List, Dict, Any

from core.isdc_data import ISDC_HIERARCHY
from core.facility_profiles import get_facility_specific_assumptions

ASSUMPTIONS_CHECKLIST = [
    # (section, text)
    ("A. General", "The decommissioning strategy (DECON / SAFSTOR / ENTOMBMENT) is defined and documented."),
    ("A. General", "The plan type (Initial / Preliminary / Final) and its intended use are stated."),
    ("A. General", "The base year and currency of the cost estimate are defined."),
    ("A. General", "The estimate accuracy class (Order-of-magnitude / Budgetary / Definitive) is stated."),
    ("B. Facility Status", "The operational history and current condition of the facility are documented."),
    ("B. Facility Status", "The end state of the site following decommissioning is defined."),
    ("B. Facility Status", "Any facility modifications planned prior to decommissioning are identified."),
    ("C. Radiological", "A radiological characterisation of the facility and site has been performed or scheduled."),
    ("C. Radiological", "Activation and contamination assumptions are documented and justified."),
    ("C. Radiological", "Dose assessment / ALARA assumptions for the workforce are documented."),
    ("D. Waste", "Waste volumes and classifications are estimated per the applicable waste classification scheme."),
    ("D. Waste", "Waste management routes (treatment, storage, disposal) are identified and available."),
    ("D. Waste", "Clearance/exemption criteria and routes for very-low-level material are defined."),
    ("E. Dismantling", "The dismantling sequence and major techniques are defined."),
    ("E. Dismantling", "Remote-handling or special tooling requirements are identified."),
    ("F. Demolition", "The scope of structural demolition is defined, including activated concrete removal."),
    ("F. Demolition", "Demolition waste management routes are identified."),
    ("G. Management", "The project management organisation and staffing profile are defined."),
    ("G. Management", "The project schedule and major milestones are defined."),
    ("G. Management", "Contingency and uncertainty ranges are applied consistently with the estimate accuracy class."),
    ("H. Regulatory", "Applicable national requirements for decommissioning and financing have been identified by the user."),
    ("H. Regulatory", "Licensing/authorisation milestones required for decommissioning are identified."),
    ("H. Regulatory", "Financial assurance / decommissioning fund mechanisms applicable to this project are identified."),
]

PROJECT_COLUMNS = [
    ("name", "TEXT"),
    ("organisation", "TEXT"),
    ("contact_person", "TEXT"),
    ("address", "TEXT"),
    ("country", "TEXT"),
    ("competent_authority", "TEXT"),
    ("facility_type", "TEXT"),
    ("unit_id", "TEXT"),
    ("site", "TEXT"),
    ("strategy", "TEXT"),
    ("estimate_type", "TEXT"),
    ("end_state", "TEXT"),
    ("plan_type", "TEXT"),
    ("conservation_years", "INTEGER DEFAULT 0"),
    ("base_year", "INTEGER"),
    ("local_currency", "TEXT DEFAULT 'EUR'"),
    ("local_rate", "REAL DEFAULT 1.0"),
    ("discount_rate", "REAL DEFAULT 3.0"),
    ("inflation_rate", "REAL DEFAULT 2.0"),
    ("national_requirements", "TEXT"),
    ("national_fund_regulation", "TEXT"),
    ("net_capacity_mwe", "REAL DEFAULT 0"),
    ("annual_energy_mwh", "REAL DEFAULT 0"),
    ("remaining_op_years", "REAL DEFAULT 0"),
    ("user_decom_tariff", "REAL DEFAULT 0"),
    ("user_waste_tariff", "REAL DEFAULT 0"),
    ("notes", "TEXT"),
    ("author", "TEXT"),
    # Funding plan inputs (Reports > Funding Plan); all user-entered.
    ("fp_start_year", "INTEGER"),
    ("fp_shutdown_year", "INTEGER"),
    ("fp_opening_balance", "REAL DEFAULT 0"),
    ("fp_return_pct", "REAL"),
    ("fp_escalation_pct", "REAL"),
    ("fp_frequency", "TEXT DEFAULT 'Yearly'"),
    ("fp_growth_pct", "REAL DEFAULT 0"),
    ("created_at", "TEXT"),
]


class DatabaseManager:
    def __init__(self, db_path: str = "isdc_tool.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------
    def initialize(self):
        self._create_schema()
        self._migrate_schema()
        self._seed_isdc_hierarchy()
        self._seed_assumptions_checklist()

    def _create_schema(self):
        c = self.conn.cursor()
        c.executescript("""
        CREATE TABLE IF NOT EXISTS isdc_level1 (
            pa_code TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT
        );

        CREATE TABLE IF NOT EXISTS isdc_level2 (
            code TEXT PRIMARY KEY,
            pa_code TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT
        );

        CREATE TABLE IF NOT EXISTS isdc_level3 (
            code TEXT PRIMARY KEY,
            level2_code TEXT NOT NULL,
            pa_code TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT
        );

        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS phases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            phase_name TEXT NOT NULL,
            phase_type TEXT DEFAULT 'Decommissioning',
            start_year INTEGER,
            end_year INTEGER,
            sort_order INTEGER DEFAULT 0,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS cost_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            isdc_code TEXT NOT NULL,
            level INTEGER NOT NULL,
            labour_eur REAL DEFAULT 0,
            investment_eur REAL DEFAULT 0,
            expenses_eur REAL DEFAULT 0,
            contingency_eur REAL DEFAULT 0,
            phase_id INTEGER,
            notes TEXT,
            UNIQUE(project_id, isdc_code),
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS assumptions_checklist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            section TEXT NOT NULL,
            text TEXT NOT NULL,
            facility_type TEXT,
            sort_order INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS project_assumptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            checklist_id INTEGER,
            custom_text TEXT,
            section TEXT,
            documented INTEGER DEFAULT 0,
            notes TEXT,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS waste_streams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            waste_class TEXT NOT NULL,
            description TEXT,
            volume_m3 REAL DEFAULT 0,
            activity_notes TEXT,
            destination TEXT,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS estimate_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            version_no INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            snapshot_note TEXT,
            grand_total_eur REAL,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        );

        -- Graded approach: per-project applicability overrides with justification.
        CREATE TABLE IF NOT EXISTS applicability_overrides (
            project_id INTEGER NOT NULL,
            code TEXT NOT NULL,
            rating TEXT NOT NULL,
            justification TEXT,
            PRIMARY KEY (project_id, code),
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        );
        """)
        self.conn.commit()

    def _migrate_schema(self):
        """Idempotent ALTER TABLE based migration for backward compatibility."""
        c = self.conn.cursor()
        for col, coltype in PROJECT_COLUMNS:
            try:
                c.execute(f"ALTER TABLE projects ADD COLUMN {col} {coltype}")
            except sqlite3.OperationalError:
                pass
        self.conn.commit()

    def _seed_isdc_hierarchy(self):
        c = self.conn.cursor()
        c.execute("SELECT COUNT(*) FROM isdc_level1")
        if c.fetchone()[0] > 0:
            return
        for pa_code, pa in ISDC_HIERARCHY.items():
            c.execute(
                "INSERT INTO isdc_level1 (pa_code, title, description) VALUES (?, ?, ?)",
                (pa_code, pa["title"], ""),
            )
            for l2_code, (l2_title, l3_list) in pa["groups"].items():
                c.execute(
                    "INSERT INTO isdc_level2 (code, pa_code, title, description) VALUES (?, ?, ?, ?)",
                    (l2_code, pa_code, l2_title, ""),
                )
                for l3_code, l3_title in l3_list:
                    c.execute(
                        "INSERT INTO isdc_level3 (code, level2_code, pa_code, title, description) "
                        "VALUES (?, ?, ?, ?, ?)",
                        (l3_code, l2_code, pa_code, l3_title, ""),
                    )
        self.conn.commit()

    def _seed_assumptions_checklist(self):
        c = self.conn.cursor()
        c.execute("SELECT COUNT(*) FROM assumptions_checklist")
        if c.fetchone()[0] > 0:
            return
        for i, (section, text) in enumerate(ASSUMPTIONS_CHECKLIST):
            c.execute(
                "INSERT INTO assumptions_checklist (section, text, facility_type, sort_order) "
                "VALUES (?, ?, NULL, ?)",
                (section, text, i),
            )
        self.conn.commit()

    # ------------------------------------------------------------------
    # ISDC hierarchy accessors
    # ------------------------------------------------------------------
    def get_level1(self) -> List[Dict[str, Any]]:
        c = self.conn.cursor()
        c.execute("SELECT * FROM isdc_level1 ORDER BY pa_code")
        return [dict(r) for r in c.fetchall()]

    def get_level2(self, pa_code: Optional[str] = None) -> List[Dict[str, Any]]:
        c = self.conn.cursor()
        if pa_code:
            c.execute("SELECT * FROM isdc_level2 WHERE pa_code=? ORDER BY code", (pa_code,))
        else:
            c.execute("SELECT * FROM isdc_level2 ORDER BY code")
        return [dict(r) for r in c.fetchall()]

    def get_level3(self, level2_code: Optional[str] = None) -> List[Dict[str, Any]]:
        c = self.conn.cursor()
        if level2_code:
            c.execute("SELECT * FROM isdc_level3 WHERE level2_code=? ORDER BY code", (level2_code,))
        else:
            c.execute("SELECT * FROM isdc_level3 ORDER BY code")
        return [dict(r) for r in c.fetchall()]

    def get_full_hierarchy(self) -> List[Dict[str, Any]]:
        """Returns full L1->L2->L3 nested structure."""
        l1 = self.get_level1()
        for pa in l1:
            pa["children"] = self.get_level2(pa["pa_code"])
            for l2 in pa["children"]:
                l2["children"] = self.get_level3(l2["code"])
        return l1

    # ------------------------------------------------------------------
    # Projects
    # ------------------------------------------------------------------
    def create_project(self, data: Dict[str, Any]) -> int:
        c = self.conn.cursor()
        cols = ["name"] + [col for col, _ in PROJECT_COLUMNS if col != "name"]
        cols = list(dict.fromkeys(cols))
        data = dict(data)
        data.setdefault("created_at", datetime.datetime.now().isoformat(timespec="seconds"))
        placeholders = ", ".join(["?"] * len(cols))
        values = [data.get(col) for col in cols]
        c.execute(f"INSERT INTO projects ({', '.join(cols)}) VALUES ({placeholders})", values)
        self.conn.commit()
        project_id = c.lastrowid

        facility_type = data.get("facility_type")
        extra_assumptions = get_facility_specific_assumptions(facility_type)
        for text in extra_assumptions:
            c.execute(
                "INSERT INTO project_assumptions (project_id, checklist_id, custom_text, section, documented) "
                "VALUES (?, NULL, ?, ?, 0)",
                (project_id, text, "I. Facility-specific"),
            )
        checklist = self.get_assumptions_checklist()
        for item in checklist:
            c.execute(
                "INSERT INTO project_assumptions (project_id, checklist_id, custom_text, section, documented) "
                "VALUES (?, ?, NULL, ?, 0)",
                (project_id, item["id"], item["section"]),
            )
        self.conn.commit()
        return project_id

    def update_project(self, project_id: int, data: Dict[str, Any]):
        c = self.conn.cursor()
        valid_cols = [col for col, _ in PROJECT_COLUMNS]
        cols = [k for k in data.keys() if k in valid_cols]
        if not cols:
            return
        set_clause = ", ".join(f"{col}=?" for col in cols)
        values = [data[col] for col in cols] + [project_id]
        c.execute(f"UPDATE projects SET {set_clause} WHERE id=?", values)
        self.conn.commit()

    def get_project(self, project_id: int) -> Optional[Dict[str, Any]]:
        c = self.conn.cursor()
        c.execute("SELECT * FROM projects WHERE id=?", (project_id,))
        row = c.fetchone()
        return dict(row) if row else None

    def get_projects(self) -> List[Dict[str, Any]]:
        c = self.conn.cursor()
        c.execute("SELECT * FROM projects ORDER BY id DESC")
        return [dict(r) for r in c.fetchall()]

    def delete_project(self, project_id: int):
        c = self.conn.cursor()
        for table in ("phases", "cost_entries", "project_assumptions", "waste_streams", "estimate_versions",
                      "applicability_overrides"):
            c.execute(f"DELETE FROM {table} WHERE project_id=?", (project_id,))
        c.execute("DELETE FROM projects WHERE id=?", (project_id,))
        self.conn.commit()

    # ------------------------------------------------------------------
    # Phases
    # ------------------------------------------------------------------
    def get_phases(self, project_id: int) -> List[Dict[str, Any]]:
        c = self.conn.cursor()
        c.execute(
            "SELECT * FROM phases WHERE project_id=? ORDER BY sort_order, start_year",
            (project_id,),
        )
        return [dict(r) for r in c.fetchall()]

    def save_phase(self, data: Dict[str, Any]) -> int:
        c = self.conn.cursor()
        if data.get("id"):
            c.execute(
                "UPDATE phases SET phase_name=?, phase_type=?, start_year=?, end_year=?, sort_order=? "
                "WHERE id=?",
                (data["phase_name"], data["phase_type"], data["start_year"],
                 data["end_year"], data.get("sort_order", 0), data["id"]),
            )
            self.conn.commit()
            return data["id"]
        c.execute(
            "INSERT INTO phases (project_id, phase_name, phase_type, start_year, end_year, sort_order) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (data["project_id"], data["phase_name"], data["phase_type"],
             data["start_year"], data["end_year"], data.get("sort_order", 0)),
        )
        self.conn.commit()
        return c.lastrowid

    def delete_phase(self, phase_id: int):
        c = self.conn.cursor()
        c.execute("UPDATE cost_entries SET phase_id=NULL WHERE phase_id=?", (phase_id,))
        c.execute("DELETE FROM phases WHERE id=?", (phase_id,))
        self.conn.commit()

    # ------------------------------------------------------------------
    # Cost entries
    # ------------------------------------------------------------------
    def get_cost_entries(self, project_id: int) -> Dict[str, Dict[str, Any]]:
        c = self.conn.cursor()
        c.execute("SELECT * FROM cost_entries WHERE project_id=?", (project_id,))
        return {row["isdc_code"]: dict(row) for row in c.fetchall()}

    def save_cost_entry(self, project_id: int, isdc_code: str, level: int,
                         labour_eur: float, investment_eur: float,
                         expenses_eur: float, contingency_eur: float,
                         phase_id: Optional[int] = None, notes: str = ""):
        c = self.conn.cursor()
        c.execute(
            """INSERT INTO cost_entries
               (project_id, isdc_code, level, labour_eur, investment_eur, expenses_eur, contingency_eur, phase_id, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(project_id, isdc_code) DO UPDATE SET
                 labour_eur=excluded.labour_eur,
                 investment_eur=excluded.investment_eur,
                 expenses_eur=excluded.expenses_eur,
                 contingency_eur=excluded.contingency_eur,
                 phase_id=excluded.phase_id,
                 notes=excluded.notes""",
            (project_id, isdc_code, level, labour_eur, investment_eur,
             expenses_eur, contingency_eur, phase_id, notes),
        )
        self.conn.commit()

    # ------------------------------------------------------------------
    # Applicability overrides (graded approach)
    # ------------------------------------------------------------------
    def get_applicability_overrides(self, project_id: int) -> Dict[str, Dict[str, Any]]:
        c = self.conn.cursor()
        c.execute("SELECT code, rating, justification FROM applicability_overrides WHERE project_id=?",
                  (project_id,))
        return {r["code"]: {"rating": r["rating"], "justification": r["justification"] or ""}
                for r in c.fetchall()}

    def set_applicability_override(self, project_id: int, code: str,
                                   rating: Optional[str], justification: str = ""):
        """Set a user rating for a code; rating=None removes the override (back to default)."""
        c = self.conn.cursor()
        if rating:
            c.execute(
                """INSERT INTO applicability_overrides (project_id, code, rating, justification)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(project_id, code) DO UPDATE SET
                     rating=excluded.rating, justification=excluded.justification""",
                (project_id, code, rating, justification),
            )
        else:
            c.execute("DELETE FROM applicability_overrides WHERE project_id=? AND code=?", (project_id, code))
        self.conn.commit()

    # ------------------------------------------------------------------
    # Assumptions
    # ------------------------------------------------------------------
    def get_assumptions_checklist(self) -> List[Dict[str, Any]]:
        c = self.conn.cursor()
        c.execute("SELECT * FROM assumptions_checklist ORDER BY sort_order")
        return [dict(r) for r in c.fetchall()]

    def get_project_assumptions(self, project_id: int) -> List[Dict[str, Any]]:
        c = self.conn.cursor()
        c.execute(
            "SELECT * FROM project_assumptions WHERE project_id=? ORDER BY section, id",
            (project_id,),
        )
        return [dict(r) for r in c.fetchall()]

    def set_assumption_documented(self, assumption_id: int, documented: bool, notes: str = ""):
        c = self.conn.cursor()
        c.execute(
            "UPDATE project_assumptions SET documented=?, notes=? WHERE id=?",
            (1 if documented else 0, notes, assumption_id),
        )
        self.conn.commit()

    def bulk_set_documented(self, project_id: int, section: Optional[str], documented: bool):
        c = self.conn.cursor()
        if section and section != "All sections":
            c.execute(
                "UPDATE project_assumptions SET documented=? WHERE project_id=? AND section=?",
                (1 if documented else 0, project_id, section),
            )
        else:
            c.execute(
                "UPDATE project_assumptions SET documented=? WHERE project_id=?",
                (1 if documented else 0, project_id),
            )
        self.conn.commit()

    # ------------------------------------------------------------------
    # Waste streams
    # ------------------------------------------------------------------
    def get_waste_streams(self, project_id: int) -> List[Dict[str, Any]]:
        c = self.conn.cursor()
        c.execute("SELECT * FROM waste_streams WHERE project_id=? ORDER BY id", (project_id,))
        return [dict(r) for r in c.fetchall()]

    def save_waste_stream(self, data: Dict[str, Any]) -> int:
        c = self.conn.cursor()
        if data.get("id"):
            c.execute(
                "UPDATE waste_streams SET waste_class=?, description=?, volume_m3=?, "
                "activity_notes=?, destination=? WHERE id=?",
                (data["waste_class"], data["description"], data["volume_m3"],
                 data["activity_notes"], data["destination"], data["id"]),
            )
            self.conn.commit()
            return data["id"]
        c.execute(
            "INSERT INTO waste_streams (project_id, waste_class, description, volume_m3, "
            "activity_notes, destination) VALUES (?, ?, ?, ?, ?, ?)",
            (data["project_id"], data["waste_class"], data["description"], data["volume_m3"],
             data["activity_notes"], data["destination"]),
        )
        self.conn.commit()
        return c.lastrowid

    def delete_waste_stream(self, waste_id: int):
        c = self.conn.cursor()
        c.execute("DELETE FROM waste_streams WHERE id=?", (waste_id,))
        self.conn.commit()

    # ------------------------------------------------------------------
    # Estimate versions / snapshots
    # ------------------------------------------------------------------
    def save_version_snapshot(self, project_id: int, grand_total_eur: float, note: str = "") -> int:
        c = self.conn.cursor()
        c.execute(
            "SELECT COALESCE(MAX(version_no), 0) FROM estimate_versions WHERE project_id=?",
            (project_id,),
        )
        next_version = c.fetchone()[0] + 1
        c.execute(
            "INSERT INTO estimate_versions (project_id, version_no, created_at, snapshot_note, grand_total_eur) "
            "VALUES (?, ?, ?, ?, ?)",
            (project_id, next_version, datetime.datetime.now().isoformat(timespec="seconds"),
             note, grand_total_eur),
        )
        self.conn.commit()
        return next_version

    def get_version_count(self, project_id: int) -> int:
        c = self.conn.cursor()
        c.execute("SELECT COUNT(*) FROM estimate_versions WHERE project_id=?", (project_id,))
        return c.fetchone()[0]

    def get_versions(self, project_id: int) -> List[Dict[str, Any]]:
        c = self.conn.cursor()
        c.execute(
            "SELECT * FROM estimate_versions WHERE project_id=? ORDER BY version_no DESC",
            (project_id,),
        )
        return [dict(r) for r in c.fetchall()]
