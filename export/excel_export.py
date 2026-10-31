"""
export/excel_export.py
=========================
Excel (.xlsx) export for the ISDC Decommissioning Cost Estimation Tool.
Uses openpyxl. All monetary figures are presented in EUR, with an
optional secondary local-currency column/line for information only.
"""

import datetime

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

from core.applicability import APPLICABILITY_NOTE, WARN, build_applicability_review
from core.calculator import ISDCCalculator, ESTIMATE_ACCURACY
from core.funding_plan import (
    PLAN_METHOD_NOTE, compute_funding_plan, cost_profile_for_project, inputs_from_project, sensitivity,
)
from core.isdc_data import ISDC_HIERARCHY

HEADER_FILL = PatternFill("solid", fgColor="1A3A5C")
HEADER_FONT = Font(color="FFFFFF", bold=True)
PA_FILL = PatternFill("solid", fgColor="D0E4F5")
BOLD = Font(bold=True)


def _meta_row(ws, row, label, value):
    ws.cell(row=row, column=1, value=label).font = BOLD
    ws.cell(row=row, column=2, value=value)


def _write_cover(wb, project, financials, db=None, project_id=None):
    ws = wb.create_sheet("Cover", 0)
    ws.column_dimensions["A"].width = 32
    ws.column_dimensions["B"].width = 50

    ws.cell(row=1, column=1, value="ISDC Decommissioning Cost Estimate").font = Font(bold=True, size=14)
    row = 3
    _meta_row(ws, row, "Project name", project.get("name")); row += 1
    _meta_row(ws, row, "Organisation", project.get("organisation")); row += 1
    _meta_row(ws, row, "Contact person", project.get("contact_person")); row += 1
    _meta_row(ws, row, "Country", project.get("country")); row += 1
    _meta_row(ws, row, "Competent authority", project.get("competent_authority")); row += 1
    _meta_row(ws, row, "Facility type", project.get("facility_type")); row += 1
    _meta_row(ws, row, "Decommissioning strategy", project.get("strategy")); row += 1
    _meta_row(ws, row, "Plan type", project.get("plan_type")); row += 1
    _meta_row(ws, row, "Estimate accuracy class", project.get("estimate_type")); row += 1
    _meta_row(ws, row, "Base year", project.get("base_year")); row += 1
    _meta_row(ws, row, "Primary currency", "EUR"); row += 1
    _meta_row(ws, row, "Local currency (secondary)", project.get("local_currency")); row += 1
    _meta_row(ws, row, "Exchange rate (local/EUR)", project.get("local_rate")); row += 1
    row += 1
    _meta_row(ws, row, "GRAND TOTAL (EUR)", f"{financials.grand_total_eur:,.0f}"); row += 1
    if project.get("local_currency") and project.get("local_currency") != "EUR":
        _meta_row(ws, row, f"GRAND TOTAL ({project.get('local_currency')})",
                   f"{financials.grand_total_local:,.0f}")
        row += 1
    _meta_row(ws, row, "Lower bound (EUR)", f"{financials.lower_bound:,.0f}"); row += 1
    _meta_row(ws, row, "Upper bound (EUR)", f"{financials.upper_bound:,.0f}"); row += 1
    row += 1

    version_no = 1
    if db is not None and project_id is not None:
        version_no = db.get_version_count(project_id) + 1
    _meta_row(ws, row, "Export version/snapshot", version_no); row += 1
    _meta_row(ws, row, "Export timestamp", datetime.datetime.now().isoformat(timespec="seconds")); row += 1
    _meta_row(ws, row, "Author", project.get("author") or "Marian"); row += 1

    ws.cell(row=row + 1, column=1,
            value="Based on the NEA/OECD ISDC 2012 (NEA No. 7088) cost structure.").font = Font(italic=True, size=9)
    return ws


def _write_matrix_sheet(wb, db, project_id, title="ISDC Matrix"):
    ws = wb.create_sheet(title)
    headers = ["Code", "Title", "Labour (EUR)", "Investment (EUR)", "Expenses (EUR)",
               "Contingency (EUR)", "Total (EUR)"]
    for col, h in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
    widths = [10, 55, 16, 16, 16, 16, 16]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w

    entries = db.get_cost_entries(project_id)
    row = 2
    for pa_code, pa in ISDC_HIERARCHY.items():
        pa_labour = pa_invest = pa_expense = pa_conting = 0.0
        pa_row = row
        ws.cell(row=row, column=1, value=pa_code).font = BOLD
        ws.cell(row=row, column=2, value=pa["title"]).font = BOLD
        for c in range(1, 8):
            ws.cell(row=row, column=c).fill = PA_FILL
        row += 1

        for l2_code, (l2_title, l3_list) in pa["groups"].items():
            l2_row = row
            ws.cell(row=row, column=1, value=l2_code)
            ws.cell(row=row, column=2, value=l2_title).font = BOLD
            row += 1
            # Lump-sum entry on the Level-2 code itself (allowed by the cost matrix).
            own = entries.get(l2_code) or {}
            l2_labour = own.get("labour_eur") or 0.0
            l2_invest = own.get("investment_eur") or 0.0
            l2_expense = own.get("expenses_eur") or 0.0
            l2_conting = own.get("contingency_eur") or 0.0
            if l2_labour + l2_invest + l2_expense + l2_conting:
                ws.cell(row=row, column=1, value=l2_code)
                ws.cell(row=row, column=2, value=f"{l2_title} — lump sum (Level 2)")
                for c, v in zip(range(3, 8), (l2_labour, l2_invest, l2_expense, l2_conting,
                                              l2_labour + l2_invest + l2_expense + l2_conting)):
                    ws.cell(row=row, column=c, value=v)
                row += 1
            for l3_code, l3_title in l3_list:
                entry = entries.get(l3_code, {})
                labour = entry.get("labour_eur") or 0.0
                invest = entry.get("investment_eur") or 0.0
                expense = entry.get("expenses_eur") or 0.0
                conting = entry.get("contingency_eur") or 0.0
                total = labour + invest + expense + conting
                ws.cell(row=row, column=1, value=l3_code)
                ws.cell(row=row, column=2, value=l3_title)
                ws.cell(row=row, column=3, value=labour)
                ws.cell(row=row, column=4, value=invest)
                ws.cell(row=row, column=5, value=expense)
                ws.cell(row=row, column=6, value=conting)
                ws.cell(row=row, column=7, value=total)
                l2_labour += labour
                l2_invest += invest
                l2_expense += expense
                l2_conting += conting
                row += 1
            ws.cell(row=l2_row, column=3, value=l2_labour)
            ws.cell(row=l2_row, column=4, value=l2_invest)
            ws.cell(row=l2_row, column=5, value=l2_expense)
            ws.cell(row=l2_row, column=6, value=l2_conting)
            ws.cell(row=l2_row, column=7, value=l2_labour + l2_invest + l2_expense + l2_conting)
            pa_labour += l2_labour
            pa_invest += l2_invest
            pa_expense += l2_expense
            pa_conting += l2_conting

        ws.cell(row=pa_row, column=3, value=pa_labour)
        ws.cell(row=pa_row, column=4, value=pa_invest)
        ws.cell(row=pa_row, column=5, value=pa_expense)
        ws.cell(row=pa_row, column=6, value=pa_conting)
        ws.cell(row=pa_row, column=7, value=pa_labour + pa_invest + pa_expense + pa_conting)

    ws.freeze_panes = "A2"
    return ws


def _write_pa_summary_sheet(wb, financials):
    ws = wb.create_sheet("PA Summary")
    headers = ["PA Code", "Title", "Labour (EUR)", "Investment (EUR)", "Expenses (EUR)",
               "Contingency (EUR)", "Total (EUR)"]
    for col, h in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
    row = 2
    for pa in financials.pa_totals:
        ws.cell(row=row, column=1, value=pa.pa_code)
        ws.cell(row=row, column=2, value=pa.title)
        ws.cell(row=row, column=3, value=pa.labour_eur)
        ws.cell(row=row, column=4, value=pa.investment_eur)
        ws.cell(row=row, column=5, value=pa.expenses_eur)
        ws.cell(row=row, column=6, value=pa.contingency_eur)
        ws.cell(row=row, column=7, value=pa.total_eur)
        row += 1
    ws.cell(row=row, column=2, value="GRAND TOTAL").font = BOLD
    ws.cell(row=row, column=3, value=financials.labour_total_eur).font = BOLD
    ws.cell(row=row, column=4, value=financials.investment_total_eur).font = BOLD
    ws.cell(row=row, column=5, value=financials.expenses_total_eur).font = BOLD
    ws.cell(row=row, column=6, value=financials.contingency_total_eur).font = BOLD
    ws.cell(row=row, column=7, value=financials.grand_total_eur).font = BOLD
    ws.column_dimensions["B"].width = 55
    return ws


def _write_phases_sheet(wb, db, project_id, calc):
    ws = wb.create_sheet("Phases")
    headers = ["Phase Name", "Type", "Start Year", "End Year", "Total Cost (EUR)", "NPV Cost (EUR)"]
    for col, h in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
    profiles = calc.compute_phase_profiles()
    for row, p in enumerate(profiles, start=2):
        ws.cell(row=row, column=1, value=p.phase_name)
        ws.cell(row=row, column=2, value=p.phase_type)
        ws.cell(row=row, column=3, value=p.start_year)
        ws.cell(row=row, column=4, value=p.end_year)
        ws.cell(row=row, column=5, value=p.total_cost_eur)
        ws.cell(row=row, column=6, value=p.npv_cost_eur)
    ws.column_dimensions["A"].width = 35
    return ws


def _write_waste_sheet(wb, db, project_id):
    ws = wb.create_sheet("Waste Streams")
    headers = ["Class", "Description", "Volume (m3)", "Activity / Characterisation Notes", "Destination"]
    for col, h in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
    for row, w in enumerate(db.get_waste_streams(project_id), start=2):
        ws.cell(row=row, column=1, value=w["waste_class"])
        ws.cell(row=row, column=2, value=w.get("description"))
        ws.cell(row=row, column=3, value=w.get("volume_m3"))
        ws.cell(row=row, column=4, value=w.get("activity_notes"))
        ws.cell(row=row, column=5, value=w.get("destination"))
    ws.column_dimensions["B"].width = 40
    ws.column_dimensions["D"].width = 40
    return ws


def _write_assumptions_sheet(wb, db, project_id):
    ws = wb.create_sheet("Assumptions Register")
    headers = ["Section", "Assumption", "Documented", "Notes"]
    for col, h in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
    rows = db.get_project_assumptions(project_id)
    checklist = {c["id"]: c["text"] for c in db.get_assumptions_checklist()}
    for row, r in enumerate(rows, start=2):
        text = r.get("custom_text") or checklist.get(r.get("checklist_id"), "")
        ws.cell(row=row, column=1, value=r.get("section"))
        ws.cell(row=row, column=2, value=text)
        ws.cell(row=row, column=3, value="Yes" if r.get("documented") else "No")
        ws.cell(row=row, column=4, value=r.get("notes"))
    ws.column_dimensions["B"].width = 70
    ws.column_dimensions["D"].width = 30
    return ws


def _write_funding_plan_sheet(wb, db, project):
    """Funding plan sheet (numbers stored as numbers so users can chart/extend them)."""
    inp = inputs_from_project(project)
    profile = cost_profile_for_project(project, db) if inp else {}
    if not inp or not profile:
        return None
    res = compute_funding_plan(inp, profile)
    unit = {12: "month", 4: "quarter", 1: "year"}[res.periods_per_year]
    ws = wb.create_sheet("Funding Plan")
    ws.cell(row=1, column=1, value="DECOMMISSIONING FUNDING PLAN").font = Font(bold=True, size=13)
    ws.cell(row=2, column=1, value=PLAN_METHOD_NOTE).font = Font(italic=True, size=9)
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=7)
    ws.row_dimensions[2].height = 48
    money = "#,##0"
    rows = [
        ("Plan inputs", None, None),
        ("Plan start year (first contribution)", inp.start_year, "0"),
        ("Shutdown year (contributions stop)", inp.shutdown_year, "0"),
        ("Cost estimate price base year", inp.base_year, "0"),
        ("Fund balance at plan start (EUR)", inp.opening_balance_eur, money),
        ("Expected fund return (% per year)", inp.fund_return_pct, "0.00"),
        ("Cost escalation / inflation (% per year)", inp.cost_escalation_pct, "0.00"),
        ("Payment frequency", inp.frequency, None),
        ("Yearly increase of payments (%)", inp.contribution_growth_pct, "0.00"),
        (None, None, None),
        ("Results", None, None),
        (f"Required payment per {unit} (EUR)", res.payment_per_period, money),
        ("Equivalent per year, first year (EUR)", res.first_year_annual_contribution, money),
        ("Number of contribution years", res.contribution_years, "0"),
        ("Fund balance needed at shutdown (EUR)", res.balance_at_shutdown, money),
        ("Total contributions (EUR)", res.total_contributions, money),
        ("Total fund returns (EUR)", res.total_returns, money),
        ("Costs, base-year prices (EUR)", res.total_costs_base, money),
        ("Costs, escalated nominal (EUR)", res.total_costs_nominal, money),
    ]
    if res.eur_per_mwh:
        rows.insert(rows.index(("Number of contribution years", res.contribution_years, "0")),
                    ("Equivalent per MWh, first year (EUR/MWh)", res.eur_per_mwh, "0.000"))
    if res.message:
        rows.append(("Note", res.message, None))
    bounds = ESTIMATE_ACCURACY.get(project.get("estimate_type") or "Budgetary", ESTIMATE_ACCURACY["Budgetary"])
    rows += [(None, None, None), ("Sensitivity: first-year contribution per year (EUR)", None, None)]
    rows += [(label, v, money) for label, v in sensitivity(inp, profile, 1 + bounds["upper_pct"] / 100.0)]

    r = 4
    for label, value, fmt in rows:
        if label is not None:
            c = ws.cell(row=r, column=1, value=label)
            if value is None:
                c.font = Font(bold=True, color="1A3A5C")
            else:
                c.font = BOLD
                v = ws.cell(row=r, column=2, value=value)
                if fmt:
                    v.number_format = fmt
        r += 1

    r += 1
    headers = ["Year", "Stage", "Opening balance", "Contributions", "Fund return", "Costs paid", "Closing balance"]
    for col, h in enumerate(headers, start=1):
        cell = ws.cell(row=r, column=col, value=h)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
    shutdown_fill = PatternFill("solid", fgColor="FFF3CD")
    for srow in res.schedule:
        r += 1
        values = [srow.year, srow.stage, srow.opening_balance, srow.contributions, srow.returns,
                  srow.costs_paid, srow.closing_balance]
        for col, v in enumerate(values, start=1):
            cell = ws.cell(row=r, column=col, value=v)
            if col >= 3:
                cell.number_format = money
            if srow.year == inp.shutdown_year:
                cell.fill = shutdown_fill
    ws.column_dimensions["A"].width = 46
    for col in "BCDEFG":
        ws.column_dimensions[col].width = 18
    return ws


def _write_applicability_sheet(wb, db, project):
    ws = wb.create_sheet("Applicability")
    ws.cell(row=1, column=1, value="GRADED APPROACH — APPLICABILITY OF ISDC ACTIVITIES").font = Font(bold=True, size=13)
    ws.cell(row=2, column=1, value=f"Facility type: {project.get('facility_type') or ''}").font = BOLD
    ws.cell(row=3, column=1, value=APPLICABILITY_NOTE).font = Font(italic=True, size=9)
    ws.merge_cells(start_row=3, start_column=1, end_row=3, end_column=7)
    ws.row_dimensions[3].height = 45
    headers = ["Code", "Activity", "Rating", "Basis", "Cost (EUR)", "Status", "Justification"]
    r = 5
    for col, h in enumerate(headers, start=1):
        cell = ws.cell(row=r, column=col, value=h)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
    warn_fill = PatternFill("solid", fgColor="FFE0E0")
    na_font = Font(color="7A8590")
    for row in build_applicability_review(project, db):
        r += 1
        values = [row.code, row.title, f"{row.rating} — {row.rating_label}", row.source,
                  row.cost_eur, row.status, row.justification]
        for col, v in enumerate(values, start=1):
            cell = ws.cell(row=r, column=col, value=v)
            if col == 5:
                cell.number_format = "#,##0"
            if row.level == 1:
                cell.fill = PA_FILL
                cell.font = BOLD
            if row.severity == WARN:
                cell.fill = warn_fill
            elif row.rating == "N":
                cell.font = na_font
    for col, w in zip("ABCDEFG", (10, 45, 24, 10, 16, 45, 50)):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = "A6"
    return ws


def _wrap_text_cells(wb):
    """Wrap text cells so long titles/descriptions stay inside their column
    (rows grow taller in Excel) instead of being cut off. Numbers keep
    their alignment; existing horizontal alignment is preserved."""
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                if isinstance(cell.value, str):
                    cell.alignment = Alignment(horizontal=cell.alignment.horizontal,
                                               vertical="top", wrap_text=True)


# ---------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------

def export_isdc_matrix(db, project_id, path):
    project = db.get_project(project_id)
    calc = ISDCCalculator(dict(project), db)
    financials = calc.compute_financials()
    wb = Workbook()
    wb.remove(wb.active)
    _write_cover(wb, project, financials, db=db, project_id=project_id)
    _write_matrix_sheet(wb, db, project_id)
    _wrap_text_cells(wb)
    wb.save(path)


def export_full_report(db, project_id, path):
    project = db.get_project(project_id)
    calc = ISDCCalculator(dict(project), db)
    financials = calc.compute_financials()
    wb = Workbook()
    wb.remove(wb.active)
    _write_cover(wb, project, financials, db=db, project_id=project_id)
    _write_matrix_sheet(wb, db, project_id)
    _write_applicability_sheet(wb, db, project)
    _write_pa_summary_sheet(wb, financials)
    _write_phases_sheet(wb, db, project_id, calc)
    _write_waste_sheet(wb, db, project_id)
    _write_assumptions_sheet(wb, db, project_id)
    _write_funding_plan_sheet(wb, db, project)
    _wrap_text_cells(wb)
    wb.save(path)
