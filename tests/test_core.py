"""
Tests for the ISDC cost estimation tool: database, calculator, exports
and a headless GUI smoke test.

Run from the project root:
    .venv/bin/python -m unittest discover -s tests -v
"""

import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from core.database import DatabaseManager  # noqa: E402
from core.calculator import ISDCCalculator, ESTIMATE_ACCURACY  # noqa: E402
from core.isdc_data import ISDC_HIERARCHY  # noqa: E402

BASE_PROJECT = {
    "name": "Unit Test Plant",
    "facility_type": "NPP-PWR",
    "estimate_type": "Budgetary",
    "base_year": 2026,
    "local_currency": "RON",
    "local_rate": 5.0,
    "discount_rate": 3.0,
    "inflation_rate": 2.0,
}


class DBTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db = DatabaseManager(os.path.join(self.tmp, "test.db"))
        self.db.initialize()

    def tearDown(self):
        self.db.conn.close()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def new_project(self, **overrides):
        data = dict(BASE_PROJECT, **overrides)
        pid = self.db.create_project(data)
        return pid, self.db.get_project(pid)


# ---------------------------------------------------------------------
class TestDatabase(DBTestCase):
    def test_hierarchy_seeded_matches_source(self):
        h = self.db.get_full_hierarchy()
        self.assertEqual([pa["pa_code"] for pa in h], list(ISDC_HIERARCHY.keys()))
        n_l3_db = sum(len(l2["children"]) for pa in h for l2 in pa["children"])
        n_l3_src = sum(len(l3) for pa in ISDC_HIERARCHY.values() for _, l3 in pa["groups"].values())
        self.assertEqual(n_l3_db, n_l3_src)

    def test_initialize_is_idempotent(self):
        before = len(self.db.get_assumptions_checklist())
        self.db.initialize()
        self.assertEqual(len(self.db.get_assumptions_checklist()), before)
        self.assertEqual(len(self.db.get_level1()), len(ISDC_HIERARCHY))

    def test_create_project_seeds_assumptions(self):
        pid, _ = self.new_project(facility_type="NPP-CANDU")
        rows = self.db.get_project_assumptions(pid)
        checklist = self.db.get_assumptions_checklist()
        facility_rows = [r for r in rows if r["section"] == "I. Facility-specific"]
        self.assertEqual(len(rows), len(checklist) + len(facility_rows))
        self.assertTrue(facility_rows, "CANDU should get facility-specific assumptions")

    def test_update_and_delete_project(self):
        pid, _ = self.new_project()
        self.db.update_project(pid, {"name": "Renamed", "not_a_column": 1})
        self.assertEqual(self.db.get_project(pid)["name"], "Renamed")
        self.db.save_cost_entry(pid, "03.01.01", 3, 1, 1, 1, 1)
        self.db.delete_project(pid)
        self.assertIsNone(self.db.get_project(pid))
        self.assertEqual(self.db.get_cost_entries(pid), {})
        self.assertEqual(self.db.get_project_assumptions(pid), [])

    def test_cost_entry_upsert(self):
        pid, _ = self.new_project()
        self.db.save_cost_entry(pid, "03.01.01", 3, 100, 0, 0, 0)
        self.db.save_cost_entry(pid, "03.01.01", 3, 250, 10, 0, 0, notes="revised")
        entries = self.db.get_cost_entries(pid)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries["03.01.01"]["labour_eur"], 250)
        self.assertEqual(entries["03.01.01"]["notes"], "revised")


# ---------------------------------------------------------------------
class TestCalculator(DBTestCase):
    def test_totals_and_accuracy_bounds(self):
        for cls, bounds in ESTIMATE_ACCURACY.items():
            pid, project = self.new_project(estimate_type=cls)
            self.db.save_cost_entry(pid, "03.01.01", 3, 400, 300, 200, 100)
            self.db.save_cost_entry(pid, "06.01.01", 3, 1000, 0, 0, 0)
            f = ISDCCalculator(project, self.db).compute_financials()
            self.assertAlmostEqual(f.grand_total_eur, 2000)
            self.assertAlmostEqual(f.labour_total_eur, 1400)
            self.assertAlmostEqual(f.grand_total_local, 10000)  # rate 5.0
            self.assertAlmostEqual(f.lower_bound, 2000 * (1 + bounds["lower_pct"] / 100))
            self.assertAlmostEqual(f.upper_bound, 2000 * (1 + bounds["upper_pct"] / 100))
            pa03 = next(p for p in f.pa_totals if p.pa_code == "03")
            self.assertAlmostEqual(pa03.total_eur, 1000)

    def test_bad_rate_falls_back_to_one(self):
        pid, project = self.new_project(local_rate=0)
        self.db.save_cost_entry(pid, "03.01.01", 3, 100, 0, 0, 0)
        f = ISDCCalculator(project, self.db).compute_financials()
        self.assertAlmostEqual(f.grand_total_local, 100)

    def test_phase_npv_and_unallocated_spread(self):
        pid, project = self.new_project(base_year=2026, discount_rate=3.0)
        p1 = self.db.save_phase({"project_id": pid, "phase_name": "A", "phase_type": "Decommissioning",
                                 "start_year": 2026, "end_year": 2030})
        self.db.save_phase({"project_id": pid, "phase_name": "B", "phase_type": "Decommissioning",
                            "start_year": 2030, "end_year": 2036})
        self.db.save_cost_entry(pid, "03.01.01", 3, 1000, 0, 0, 0, phase_id=p1)
        self.db.save_cost_entry(pid, "06.01.01", 3, 1000, 0, 0, 0)  # unallocated
        calc = ISDCCalculator(project, self.db)
        profiles = calc.compute_phase_profiles()
        a, b = profiles
        # Unallocated 1000 split by duration 4:6
        self.assertAlmostEqual(a.total_cost_eur, 1000 + 400)
        self.assertAlmostEqual(b.total_cost_eur, 600)
        self.assertAlmostEqual(a.npv_cost_eur, 1400 / 1.03 ** 2)
        self.assertAlmostEqual(b.npv_cost_eur, 600 / 1.03 ** 7)
        self.assertAlmostEqual(sum(p.total_cost_eur for p in profiles), 2000)
        self.assertAlmostEqual(calc.compute_financials().npv_total, a.npv_cost_eur + b.npv_cost_eur)

    def test_mwh_levy(self):
        pid, project = self.new_project(discount_rate=3.0, local_rate=5.0)
        self.db.save_cost_entry(pid, "03.01.01", 3, 1_000_000, 0, 0, 0)
        m = ISDCCalculator(project, self.db).compute_mwh_levy(10_000, 20, 0)
        annuity = (1 - 1.03 ** -20) / 0.03
        self.assertAlmostEqual(m.annual_fund_contribution_eur, 1_000_000 / annuity)
        self.assertAlmostEqual(m.required_levy_eur_per_mwh, 1_000_000 / annuity / 10_000)
        self.assertAlmostEqual(m.required_levy_local_per_mwh, m.required_levy_eur_per_mwh * 5)
        self.assertEqual(ISDCCalculator(project, self.db).compute_mwh_levy(0, 20, 0).required_levy_eur_per_mwh, 0)


# ---------------------------------------------------------------------
class TestExports(DBTestCase):
    def _project_with_data(self):
        pid, project = self.new_project()
        ph = self.db.save_phase({"project_id": pid, "phase_name": "Dismantling",
                                 "phase_type": "Decommissioning", "start_year": 2027, "end_year": 2035})
        self.db.save_cost_entry(pid, "03.01.01", 3, 5000, 1000, 500, 650, phase_id=ph)
        self.db.save_waste_stream({"project_id": pid, "waste_class": "LLW", "description": "Concrete",
                                   "volume_m3": 120.5, "activity_notes": "", "destination": "Repository"})
        return pid

    def test_excel_exports_open(self):
        from openpyxl import load_workbook
        from export.excel_export import export_isdc_matrix, export_full_report
        pid = self._project_with_data()
        for fn in (lambda p: export_isdc_matrix(self.db, pid, p),
                   lambda p: export_full_report(self.db, pid, p)):
            path = os.path.join(self.tmp, "out.xlsx")
            fn(path)
            sheets = load_workbook(path).sheetnames
            self.assertTrue(sheets)
            self.assertNotIn("Fund Adequacy Note", sheets)  # old method removed

    def test_pdf_exports_valid(self):
        from export.pdf_export import export_pdf_report, export_pdf_funding_plan_note
        pid = self._project_with_data()
        self.db.update_project(pid, {"fp_start_year": 2026, "fp_shutdown_year": 2027,
                                     "fp_return_pct": 3, "fp_escalation_pct": 2})
        for name, fn in (("r.pdf", lambda p: export_pdf_report(self.db, pid, p)),
                         ("r2.pdf", lambda p: export_pdf_report(self.db, pid, p, include_matrix=False)),
                         ("f.pdf", lambda p: export_pdf_funding_plan_note(self.db, pid, p))):
            path = os.path.join(self.tmp, name)
            fn(path)
            with open(path, "rb") as fh:
                self.assertEqual(fh.read(5), b"%PDF-")
            self.assertGreater(os.path.getsize(path), 1500)

    def test_matrix_breakdown_reconciles_with_grand_total(self):
        """Costs entered on a Level-2 code must appear in the matrix breakdown,
        otherwise the report's matrix does not add up to its grand total."""
        from export.pdf_export import _build_matrix_tables
        pid, project = self.new_project()
        self.db.save_cost_entry(pid, "03.01.01", 3, 1000, 0, 0, 0)
        self.db.save_cost_entry(pid, "03.02", 2, 500, 0, 0, 0)  # GUI allows Level-2 entries
        grand = ISDCCalculator(project, self.db).compute_financials().grand_total_eur
        pa_rows = [t._cellvalues[0] for t in _build_matrix_tables(self.db, pid)]
        matrix_sum = sum(float(r[-1].replace(",", "")) for r in pa_rows)
        self.assertAlmostEqual(matrix_sum, grand)


# ---------------------------------------------------------------------
class TestFundingPlan(DBTestCase):
    def plan(self, profile, **kw):
        from core.funding_plan import FundingPlanInputs, compute_funding_plan
        args = dict(start_year=2026, shutdown_year=2046, base_year=2026,
                    fund_return_pct=4.0, cost_escalation_pct=0.0, frequency="Yearly")
        args.update(kw)
        return compute_funding_plan(FundingPlanInputs(**args), profile)

    def test_zero_return_is_simple_division(self):
        r = self.plan({2050: 2e9}, fund_return_pct=0)
        self.assertAlmostEqual(r.payment_per_period, 100e6, delta=1)
        self.assertEqual(r.contribution_years, 20)

    def test_fund_never_negative_and_ends_near_zero(self):
        r = self.plan({2046: 3e8, 2047: 5e8, 2048: 4e8}, cost_escalation_pct=2.0, frequency="Monthly")
        self.assertTrue(r.feasible)
        self.assertGreaterEqual(min(s.closing_balance for s in r.schedule), -1)
        self.assertAlmostEqual(r.final_balance, 0, delta=1000)
        self.assertAlmostEqual(r.total_contributions + r.total_returns, r.total_costs_nominal, delta=1000)

    def test_monthly_cheaper_than_yearly_with_positive_return(self):
        y = self.plan({2046: 1e9}, frequency="Yearly")
        m = self.plan({2046: 1e9}, frequency="Monthly")
        self.assertLess(m.first_year_annual_contribution, y.first_year_annual_contribution)
        self.assertEqual(m.periods_per_year, 12)

    def test_escalation_and_return_directions(self):
        base = self.plan({2050: 1e9}).first_year_annual_contribution
        self.assertGreater(self.plan({2050: 1e9}, cost_escalation_pct=2).first_year_annual_contribution, base)
        self.assertLess(self.plan({2050: 1e9}, fund_return_pct=5).first_year_annual_contribution, base)

    def test_growing_payments_start_lower(self):
        level = self.plan({2050: 1e9}).payment_per_period
        growing = self.plan({2050: 1e9}, contribution_growth_pct=2).payment_per_period
        self.assertLess(growing, level)

    def test_large_opening_balance_needs_nothing(self):
        r = self.plan({2050: 1e9}, opening_balance_eur=2e9)
        self.assertEqual(r.payment_per_period, 0)
        self.assertTrue(r.message)

    def test_cost_before_any_contribution_is_infeasible(self):
        r = self.plan({2026: 1e9})
        self.assertFalse(r.feasible)

    def test_project_profile_matches_estimate_total(self):
        from core.funding_plan import cost_profile_for_project
        pid, _ = self.new_project()
        ph = self.db.save_phase({"project_id": pid, "phase_name": "D", "phase_type": "Decommissioning",
                                 "start_year": 2040, "end_year": 2045})
        self.db.save_cost_entry(pid, "03.01.01", 3, 1000, 0, 0, 0, phase_id=ph)
        self.db.save_cost_entry(pid, "06.01.01", 3, 500, 0, 0, 0)
        profile = cost_profile_for_project(self.db.get_project(pid), self.db)
        self.assertEqual(sorted(profile), list(range(2040, 2045)))
        self.assertAlmostEqual(sum(profile.values()), 1500)

    def test_plan_saved_on_project_appears_in_exports(self):
        from openpyxl import load_workbook
        from export.excel_export import export_full_report
        from export.pdf_export import export_pdf_report, build_funding_plan_section
        pid, _ = self.new_project()
        self.db.save_phase({"project_id": pid, "phase_name": "D", "phase_type": "Decommissioning",
                            "start_year": 2040, "end_year": 2045})
        self.db.save_cost_entry(pid, "03.01.01", 3, 1e6, 0, 0, 0)
        project = self.db.get_project(pid)
        self.assertEqual(build_funding_plan_section(self.db, project), [])  # not set up yet
        self.db.update_project(pid, {"fp_start_year": 2026, "fp_shutdown_year": 2040, "fp_return_pct": 4,
                                     "fp_escalation_pct": 2, "fp_frequency": "Monthly"})
        project = self.db.get_project(pid)
        self.assertTrue(build_funding_plan_section(self.db, project))
        xlsx = os.path.join(self.tmp, "p.xlsx")
        export_full_report(self.db, pid, xlsx)
        self.assertIn("Funding Plan", load_workbook(xlsx).sheetnames)
        export_pdf_report(self.db, pid, os.path.join(self.tmp, "p.pdf"))


# ---------------------------------------------------------------------
class TestFacilityProfiles(DBTestCase):
    def test_every_facility_type_rates_every_pa(self):
        from core.facility_profiles import FACILITY_TYPES, get_code_applicability
        for ft in FACILITY_TYPES:
            for pa in ISDC_HIERARCHY:
                self.assertIn(get_code_applicability(ft, pa), {"M", "D", "A", "C", "N"}, (ft, pa))

    def test_fuel_cycle_facilities_get_their_own_assumptions(self):
        from core.facility_profiles import FCF_ASSUMPTIONS, FCF_COMMON_ASSUMPTIONS
        seeded = {}
        for ft in ("FCF-UF", "FCF-ENR", "FCF-REP"):
            pid, _ = self.new_project(facility_type=ft)
            texts = [r["custom_text"] for r in self.db.get_project_assumptions(pid)
                     if r["section"] == "I. Facility-specific"]
            self.assertEqual(sorted(texts), sorted(FCF_ASSUMPTIONS[ft]), ft)
            for common in FCF_COMMON_ASSUMPTIONS:
                self.assertIn(common, texts)
            seeded[ft] = set(texts) - set(FCF_COMMON_ASSUMPTIONS)
        # each type has its own specific items, none shared between types
        self.assertTrue(all(seeded.values()))
        self.assertFalse(seeded["FCF-UF"] & seeded["FCF-ENR"])
        self.assertFalse(seeded["FCF-ENR"] & seeded["FCF-REP"])
        self.assertTrue(any("UF6" in t for t in seeded["FCF-ENR"]))
        self.assertTrue(any("plutonium" in t for t in seeded["FCF-REP"]))
        self.assertFalse(any("reprocessing" in t.lower() for t in seeded["FCF-UF"]))

    def test_fuel_fabrication_is_not_a_power_reactor(self):
        from core.facility_profiles import is_power_reactor, get_code_applicability
        self.assertFalse(is_power_reactor("FCF-UF"))
        self.assertEqual(get_code_applicability("FCF-UF", "03"), "D")  # process dismantling dominates
        self.assertEqual(get_code_applicability("FCF-UF", "04"), "D")  # waste dominates

    def test_fuel_fabrication_full_workflow_without_power_data(self):
        """Non-power facility: no MWh data; funding plan must not report EUR/MWh, exports must work."""
        from core.funding_plan import compute_funding_plan, inputs_from_project, cost_profile_for_project
        from export.pdf_export import export_pdf_report
        from export.excel_export import export_full_report
        pid, _ = self.new_project(facility_type="FCF-UF", estimate_type="Order-of-magnitude",
                                  local_currency="EUR", local_rate=1.0)
        ph = self.db.save_phase({"project_id": pid, "phase_name": "D&D", "phase_type": "Decommissioning",
                                 "start_year": 2032, "end_year": 2038})
        for code in ("03.02.02", "04.01.03", "08.02.02"):
            self.db.save_cost_entry(pid, code, 3, 1e6, 2e5, 1e5, 2e5, phase_id=ph)
        self.db.update_project(pid, {"fp_start_year": 2026, "fp_shutdown_year": 2032, "fp_return_pct": 3.5,
                                     "fp_escalation_pct": 2.5, "fp_frequency": "Quarterly"})
        project = self.db.get_project(pid)
        self.assertFalse(project["annual_energy_mwh"])
        res = compute_funding_plan(inputs_from_project(project), cost_profile_for_project(project, self.db))
        self.assertTrue(res.feasible)
        self.assertEqual(res.eur_per_mwh, 0)
        self.assertEqual(res.periods_per_year, 4)
        export_pdf_report(self.db, pid, os.path.join(self.tmp, "fcf.pdf"))
        export_full_report(self.db, pid, os.path.join(self.tmp, "fcf.xlsx"))


# ---------------------------------------------------------------------
class TestGradedApproach(DBTestCase):
    def review(self, pid):
        from core.applicability import build_applicability_review
        return {r.code: r for r in build_applicability_review(self.db.get_project(pid), self.db)}

    def test_level2_defaults_and_inheritance(self):
        from core.facility_profiles import get_code_applicability as g
        self.assertEqual(g("FCF-UF", "08"), "D")
        self.assertEqual(g("FCF-UF", "08.01"), "N")       # no spent fuel at a fuel fab
        self.assertEqual(g("FCF-UF", "08.01.02"), "N")    # Level-3 inherits Level-2
        self.assertEqual(g("FCF-UF", "08.02"), "D")
        self.assertEqual(g("NPP-PWR", "08.01"), "D")
        self.assertEqual(g("FCF-REP", "08.01"), "D")
        self.assertEqual(g("WSF", "08.02.01"), "N")       # inherits PA-level N
        for ft in ("NPP-PWR", "FCF-UF", "WDF"):
            self.assertEqual(g(ft, "05.03"), "C")         # safe-storage period is conditional
        self.assertEqual(g("FCF-UF", "03.02.01"), "D")    # no Level-2 rule -> PA rating

    def test_user_override_most_specific_wins_and_reset(self):
        from core.facility_profiles import effective_applicability as eff
        pid, _ = self.new_project(facility_type="FCF-UF")
        self.db.set_applicability_override(pid, "08", "N", "No nuclear material on site")
        self.db.set_applicability_override(pid, "08.03", "A", "Safeguards close-out still required")
        ov = self.db.get_applicability_overrides(pid)
        self.assertEqual(eff("FCF-UF", "08.02", ov)["rating"], "N")    # user PA beats default L2
        self.assertEqual(eff("FCF-UF", "08.03.01", ov)["rating"], "A")  # more specific user wins
        self.assertEqual(eff("FCF-UF", "08.03.01", ov)["source"], "User")
        self.db.set_applicability_override(pid, "08", None)
        self.assertEqual(eff("FCF-UF", "08.02", self.db.get_applicability_overrides(pid))["rating"], "D")
        self.db.delete_project(pid)
        self.assertEqual(self.db.get_applicability_overrides(pid), {})

    def test_contingency_check(self):
        pid, _ = self.new_project(facility_type="FCF-UF")
        self.assertEqual(self.review(pid)["11"].severity, "warn")       # nothing anywhere
        self.db.save_cost_entry(pid, "03.02.02", 3, 1000, 0, 0, 150)
        r = self.review(pid)["11"]
        self.assertEqual(r.severity, "ok")                              # line contingency covers it
        self.assertIn("Covered", r.status)
        self.db.save_cost_entry(pid, "11.01.01", 3, 0, 0, 0, 500)
        self.assertIn("counted twice", self.review(pid)["11"].status)   # double counting risk

    def test_review_flags(self):
        pid, _ = self.new_project(facility_type="FCF-UF")
        self.db.save_cost_entry(pid, "08.01.02", 3, 1000, 0, 0, 0)      # spent fuel transport at a fuel fab
        rv = self.review(pid)
        self.assertEqual(rv["08.01"].severity, "warn")
        self.assertIn("Not applicable", rv["08.01"].status)
        self.assertEqual(rv["08.02"].severity, "warn")                  # dominant, explicit, empty
        self.assertEqual(rv["06.02"].severity, "info")                  # inherited M, not flagged per group
        self.assertEqual(rv["05.03"].severity, "info")                  # conditional
        self.db.set_applicability_override(pid, "08.02", "A", "Uranium inventory already shipped")
        self.db.set_applicability_override(pid, "03.02.03", "N", "No large components")
        rv = self.review(pid)
        self.assertEqual(rv["08.02"].severity, "ok")
        self.assertEqual(rv["08.02"].source, "User")
        self.assertIn("03.02.03", rv)                                   # user-rated Level-3 is listed
        self.assertEqual(rv["03.02.03"].level, 3)

    def test_level2_lump_sum_counted_in_review(self):
        pid, _ = self.new_project()
        self.db.save_cost_entry(pid, "03.02", 2, 500, 0, 0, 0)
        self.assertAlmostEqual(self.review(pid)["03.02"].cost_eur, 500)
        self.assertAlmostEqual(self.review(pid)["03"].cost_eur, 500)

    def test_exports_include_applicability(self):
        from openpyxl import load_workbook
        from export.excel_export import export_full_report
        from export.pdf_export import export_pdf_report, build_applicability_section
        pid, _ = self.new_project(facility_type="FCF-UF")
        self.db.save_cost_entry(pid, "03.02.02", 3, 1000, 0, 0, 100)
        project = self.db.get_project(pid)
        self.assertTrue(build_applicability_section(self.db, project))
        xlsx = os.path.join(self.tmp, "a.xlsx")
        export_full_report(self.db, pid, xlsx)
        ws = load_workbook(xlsx)["Applicability"]
        codes = [ws.cell(row=r, column=1).value for r in range(6, ws.max_row + 1)]
        self.assertIn("08.01", codes)
        export_pdf_report(self.db, pid, os.path.join(self.tmp, "a.pdf"))

    def test_funding_plan_ignores_mwh_for_non_power(self):
        from core.funding_plan import inputs_from_project
        pid, _ = self.new_project(facility_type="FCF-UF", annual_energy_mwh=5e6)
        self.db.update_project(pid, {"fp_start_year": 2026, "fp_shutdown_year": 2030})
        self.assertEqual(inputs_from_project(self.db.get_project(pid)).annual_energy_mwh, 0)


# ---------------------------------------------------------------------
class TestGUISmoke(DBTestCase):
    def test_main_window_loads_project_in_all_tabs(self):
        from PyQt5.QtWidgets import QApplication, QMessageBox
        from gui.main_window import MainWindow
        app = QApplication.instance() or QApplication([])
        errors = []
        orig = QMessageBox.critical
        QMessageBox.critical = staticmethod(lambda *a, **k: errors.append(a[2] if len(a) > 2 else a))
        try:
            pid, _ = self.new_project()
            self.db.save_cost_entry(pid, "03.01.01", 3, 100, 0, 0, 0)
            w = MainWindow(self.db)
            w._load_project(pid)
            rt = w.tab_reports  # exercise the Funding Plan sub-tab end to end
            rt.fp_start.setValue(2026)
            rt.fp_shutdown.setValue(2040)
            rt._on_funding_plan_calculate()
            self.assertEqual(self.db.get_project(pid)["fp_shutdown_year"], 2040)
            self.assertGreater(rt.fp_table.rowCount(), 0)
            for i in range(w.tabs.count()):
                w.tabs.setCurrentIndex(i)
                app.processEvents()
            w.close()
        finally:
            QMessageBox.critical = orig
        self.assertEqual(errors, [])

    def test_power_items_hidden_for_non_power_facilities(self):
        from PyQt5.QtWidgets import QApplication
        from gui.main_window import MainWindow
        app = QApplication.instance() or QApplication([])
        fcf, _ = self.new_project(facility_type="FCF-UF")
        npp, _ = self.new_project(facility_type="NPP-PWR")
        w = MainWindow(self.db)
        st, rt = w.tab_setup, w.tab_reports
        w._load_project(fcf)
        app.processEvents()
        self.assertFalse(st.inner_tabs.isTabVisible(st._power_tab_index))
        self.assertFalse(rt.inner_tabs.isTabVisible(rt._mwh_tab_index))
        w._load_project(npp)
        self.assertTrue(st.inner_tabs.isTabVisible(st._power_tab_index))
        self.assertTrue(rt.inner_tabs.isTabVisible(rt._mwh_tab_index))
        w.close()

    def test_cost_matrix_applicability_editing(self):
        from PyQt5.QtWidgets import QApplication, QMessageBox
        from gui.main_window import MainWindow
        app = QApplication.instance() or QApplication([])
        pid, _ = self.new_project(facility_type="FCF-UF")
        w = MainWindow(self.db)
        w._load_project(pid)
        mt = w.tab_matrix
        mt._scroll_to_code("08.01")
        item = mt.tree.currentItem()
        self.assertEqual(item.text(2), "N")
        self.assertIn("need review", mt.lbl_warning.text())
        mt._scroll_to_code("08.02")
        self.assertIn("Dominant", mt.tree.currentItem().toolTip(1))  # dominant item without cost flagged
        mt.cb_appl.setCurrentIndex(mt.cb_appl.findData("A"))
        mt.ed_justification.setText("")
        warned = []
        orig = QMessageBox.warning
        QMessageBox.warning = staticmethod(lambda *a, **k: warned.append(a))
        try:
            mt._on_save_applicability()                             # refused: no justification
        finally:
            QMessageBox.warning = orig
        self.assertTrue(warned)
        self.assertEqual(self.db.get_applicability_overrides(pid), {})
        mt.ed_justification.setText("Uranium inventory removed during operation")
        mt._on_save_applicability()
        self.assertEqual(self.db.get_applicability_overrides(pid)["08.02"]["rating"], "A")
        self.assertEqual(mt.tree.currentItem().text(2), "A *")
        self.assertIn("justified", mt.tree.currentItem().toolTip(1))
        app.processEvents()
        w.close()


if __name__ == "__main__":
    unittest.main()
