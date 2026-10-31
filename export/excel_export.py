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

from core.calculator import ISDCCalculator, PA_LABELS, REFERENCE_TARIFFS_NOTE
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
            l2_labour = l2_invest = l2_expense = l2_conting = 0.0
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


def _write_fund_note_sheet(wb, project, financials, fund_data):
    ws = wb.create_sheet("Fund Adequacy Note")
    ws.cell(row=1, column=1, value="DECOMMISSIONING FUND ADEQUACY NOTE").font = Font(bold=True, size=13)
    row = 3
    _meta_row(ws, row, "Project", project.get("name")); row += 1
    _meta_row(ws, row, "Organisation", project.get("organisation")); row += 1
    _meta_row(ws, row, "Estimate type", project.get("estimate_type")); row += 1
    row += 1

    if fund_data:
        _meta_row(ws, row, "Total estimated cost (EUR)", f"{fund_data['total_estimated_cost_eur']:,.0f}"); row += 1
        _meta_row(ws, row, "Costs incurred to date (EUR)", f"{fund_data['costs_incurred_eur']:,.0f}"); row += 1
        _meta_row(ws, row, "Remaining liability (EUR)", f"{fund_data['remaining_liability_eur']:,.0f}"); row += 1
        _meta_row(ws, row, "NPV of remaining liability (EUR)", f"{fund_data['npv_remaining_eur']:,.0f}"); row += 1
        _meta_row(ws, row, "Lower bound NPV (EUR)", f"{fund_data['lower_bound_npv_eur']:,.0f}"); row += 1
        _meta_row(ws, row, "Upper bound NPV (EUR)", f"{fund_data['upper_bound_npv_eur']:,.0f}"); row += 1
        _meta_row(ws, row, "Current fund balance (EUR)", f"{fund_data['current_fund_balance_eur']:,.0f}"); row += 1
        _meta_row(ws, row, "Shortfall / surplus (EUR)", f"{fund_data['shortfall_surplus_eur']:,.0f}"); row += 1
        _meta_row(ws, row, "Required annual provision (EUR/yr)", f"{fund_data['annual_provision_eur']:,.0f}"); row += 1
        _meta_row(ws, row, "Years remaining", fund_data.get("years_remaining")); row += 1
    else:
        ws.cell(row=row, column=1, value="No fund adequacy calculation available for this export.")
        row += 1

    row += 1
    ws.cell(row=row, column=1,
            value="Note: Required contributions are indicative, based on the current estimate's "
                  "accuracy class and the discount rate defined in the project financial parameters.").font = Font(italic=True, size=9)
    ws.column_dimensions["A"].width = 35
    ws.column_dimensions["B"].width = 30
    return ws


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
    wb.save(path)


def export_full_report(db, project_id, path, fund_data=None):
    project = db.get_project(project_id)
    calc = ISDCCalculator(dict(project), db)
    financials = calc.compute_financials()
    wb = Workbook()
    wb.remove(wb.active)
    _write_cover(wb, project, financials, db=db, project_id=project_id)
    _write_matrix_sheet(wb, db, project_id)
    _write_pa_summary_sheet(wb, financials)
    _write_phases_sheet(wb, db, project_id, calc)
    _write_waste_sheet(wb, db, project_id)
    _write_assumptions_sheet(wb, db, project_id)
    _write_fund_note_sheet(wb, project, financials, fund_data)
    wb.save(path)
