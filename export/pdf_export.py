"""
export/pdf_export.py
======================
PDF export for the ISDC Decommissioning Cost Estimation Tool, using
reportlab. Produces a full report (cover, financial summary, ISDC
matrix by Principal Activity, phase profile, fund adequacy note,
EUR/MWh levy, assumptions completeness) or a standalone fund
adequacy note.
"""

import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from core.calculator import ISDCCalculator, REFERENCE_TARIFFS_NOTE
from core.isdc_data import ISDC_HIERARCHY

NAVY = colors.HexColor("#1A3A5C")
BLUE1 = colors.HexColor("#2A5A8C")
BLUE2 = colors.HexColor("#D0E4F5")
BLUE3 = colors.HexColor("#E8F0F8")
AMBER = colors.HexColor("#FFF3CD")
GREEN = colors.HexColor("#E8F5E9")
RED = colors.HexColor("#FFCCCC")
GREY = colors.HexColor("#F4F6F9")

styles = getSampleStyleSheet()
TITLE_STYLE = ParagraphStyle("TitleStyle", parent=styles["Title"], textColor=NAVY, fontSize=18)
H2_STYLE = ParagraphStyle("H2Style", parent=styles["Heading2"], textColor=NAVY)
NORMAL_STYLE = styles["Normal"]
ITALIC_STYLE = ParagraphStyle("ItalicStyle", parent=styles["Normal"], fontSize=8, textColor=colors.grey, italic=True)


class _HeaderFooter:
    def __init__(self, project_name):
        self.project_name = project_name

    def on_page(self, canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.grey)
        canvas.drawString(20 * mm, 10 * mm, f"ISDC Decommissioning Cost Estimate — {self.project_name}")
        canvas.drawRightString(190 * mm, 10 * mm, f"Page {doc.page}")
        canvas.drawString(20 * mm, 287 * mm,
                           f"Generated {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
        canvas.restoreState()

    def on_first_page(self, canvas, doc):
        self.on_page(canvas, doc)

    def on_later_pages(self, canvas, doc):
        self.on_page(canvas, doc)


def _money(v):
    try:
        return f"{v:,.0f} EUR"
    except (TypeError, ValueError):
        return "-"


def _build_cover_table(project):
    data = [
        ["Project name", project.get("name") or ""],
        ["Organisation", project.get("organisation") or ""],
        ["Contact person", project.get("contact_person") or ""],
        ["Country", project.get("country") or ""],
        ["Competent authority", project.get("competent_authority") or ""],
        ["Facility type", project.get("facility_type") or ""],
        ["Decommissioning strategy", project.get("strategy") or ""],
        ["Plan type", project.get("plan_type") or ""],
        ["Estimate accuracy class", project.get("estimate_type") or ""],
        ["Base year", str(project.get("base_year") or "")],
        ["Author", project.get("author") or "Marian"],
        ["Report date", datetime.date.today().isoformat()],
    ]
    table = Table(data, colWidths=[55 * mm, 110 * mm])
    table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (0, -1), BLUE3),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return table


def _build_financial_summary_table(financials):
    data = [["Category", "Amount (EUR)"]]
    data.append(["Labour", f"{financials.labour_total_eur:,.0f}"])
    data.append(["Investment", f"{financials.investment_total_eur:,.0f}"])
    data.append(["Expenses", f"{financials.expenses_total_eur:,.0f}"])
    data.append(["Contingency", f"{financials.contingency_total_eur:,.0f}"])
    data.append(["GRAND TOTAL", f"{financials.grand_total_eur:,.0f}"])
    data.append(["Lower bound", f"{financials.lower_bound:,.0f}"])
    data.append(["Upper bound", f"{financials.upper_bound:,.0f}"])
    data.append(["NPV (base year)", f"{financials.npv_total:,.0f}"])
    table = Table(data, colWidths=[80 * mm, 80 * mm])
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("BACKGROUND", (0, 5), (-1, 5), AMBER),
        ("FONTNAME", (0, 5), (-1, 5), "Helvetica-Bold"),
    ]
    table.setStyle(TableStyle(style))
    return table


def _build_matrix_tables(db, project_id):
    entries = db.get_cost_entries(project_id)
    tables = []
    for pa_code, pa in ISDC_HIERARCHY.items():
        data = [["Code", "Title", "Labour", "Investment", "Expenses", "Contingency", "Total"]]
        pa_total = 0.0
        for l2_code, (l2_title, l3_list) in pa["groups"].items():
            l2_total = 0.0
            for l3_code, l3_title in l3_list:
                e = entries.get(l3_code, {})
                labour = e.get("labour_eur") or 0.0
                invest = e.get("investment_eur") or 0.0
                expense = e.get("expenses_eur") or 0.0
                conting = e.get("contingency_eur") or 0.0
                total = labour + invest + expense + conting
                if total == 0:
                    continue
                data.append([l3_code, l3_title, f"{labour:,.0f}", f"{invest:,.0f}",
                             f"{expense:,.0f}", f"{conting:,.0f}", f"{total:,.0f}"])
                l2_total += total
            pa_total += l2_total
        if len(data) == 1:
            continue  # no costs entered for this PA
        data.insert(0, [f"PA {pa_code}", pa["title"], "", "", "", "", f"{pa_total:,.0f}"])
        table = Table(data, colWidths=[20 * mm, 55 * mm, 20 * mm, 22 * mm, 20 * mm, 22 * mm, 20 * mm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BLUE2),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("BACKGROUND", (0, 1), (-1, 1), GREY),
            ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7.5),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.lightgrey),
            ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ]))
        tables.append(table)
    return tables


def _build_phase_table(calc):
    profiles = calc.compute_phase_profiles()
    if not profiles:
        return None
    data = [["Phase", "Type", "Start", "End", "Total (EUR)", "NPV (EUR)"]]
    for p in profiles:
        data.append([p.phase_name, p.phase_type, str(p.start_year), str(p.end_year),
                     f"{p.total_cost_eur:,.0f}", f"{p.npv_cost_eur:,.0f}"])
    table = Table(data, colWidths=[40 * mm, 28 * mm, 18 * mm, 18 * mm, 30 * mm, 30 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.lightgrey),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
    ]))
    return table


def _build_fund_table(fund_data):
    if not fund_data:
        return None
    rows = [
        ["Total estimated cost", _money(fund_data["total_estimated_cost_eur"])],
        ["Costs incurred to date", _money(fund_data["costs_incurred_eur"])],
        ["Remaining liability", _money(fund_data["remaining_liability_eur"])],
        ["NPV of remaining liability", _money(fund_data["npv_remaining_eur"])],
        ["Lower bound NPV", _money(fund_data["lower_bound_npv_eur"])],
        ["Upper bound NPV", _money(fund_data["upper_bound_npv_eur"])],
        ["Current fund balance", _money(fund_data["current_fund_balance_eur"])],
        ["Shortfall / surplus", _money(fund_data["shortfall_surplus_eur"])],
        ["Required annual provision (EUR/yr)", _money(fund_data["annual_provision_eur"])],
        ["Years remaining", str(fund_data.get("years_remaining", ""))],
    ]
    table = Table(rows, colWidths=[80 * mm, 80 * mm])
    table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("BACKGROUND", (0, 0), (0, -1), BLUE3),
    ]))
    return table


def _build_assumptions_summary(db, project_id):
    rows = db.get_project_assumptions(project_id)
    total = len(rows)
    documented = sum(1 for r in rows if r.get("documented"))
    pct = (100 * documented / total) if total else 0
    return f"Assumptions documented: {documented} / {total} ({pct:.0f}%)"


# ---------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------

def export_pdf_report(db, project_id, path, fund_data=None, include_matrix=True):
    project = db.get_project(project_id)
    calc = ISDCCalculator(dict(project), db)
    financials = calc.compute_financials()

    doc = SimpleDocTemplate(path, pagesize=A4, topMargin=25 * mm, bottomMargin=20 * mm,
                             leftMargin=18 * mm, rightMargin=18 * mm)
    hf = _HeaderFooter(project.get("name") or "")
    story = []

    story.append(Paragraph("Decommissioning Cost Estimate Report", TITLE_STYLE))
    story.append(Spacer(1, 6 * mm))
    story.append(_build_cover_table(project))
    story.append(PageBreak())

    story.append(Paragraph("Executive Financial Summary", H2_STYLE))
    story.append(Spacer(1, 3 * mm))
    story.append(_build_financial_summary_table(financials))
    story.append(Spacer(1, 6 * mm))

    if include_matrix:
        story.append(Paragraph("ISDC Cost Matrix by Principal Activity", H2_STYLE))
        story.append(Spacer(1, 2 * mm))
        matrix_tables = _build_matrix_tables(db, project_id)
        if matrix_tables:
            for t in matrix_tables:
                story.append(t)
                story.append(Spacer(1, 3 * mm))
        else:
            story.append(Paragraph("No cost entries recorded yet.", NORMAL_STYLE))
        story.append(PageBreak())

    story.append(Paragraph("Phase Cost Profile", H2_STYLE))
    story.append(Spacer(1, 2 * mm))
    phase_table = _build_phase_table(calc)
    story.append(phase_table if phase_table else Paragraph("No phases defined.", NORMAL_STYLE))
    story.append(Spacer(1, 6 * mm))

    story.append(Paragraph("Decommissioning Fund Adequacy Note", H2_STYLE))
    story.append(Spacer(1, 2 * mm))
    fund_table = _build_fund_table(fund_data)
    story.append(fund_table if fund_table else Paragraph(
        "No fund adequacy calculation available for this export.", NORMAL_STYLE))
    story.append(Spacer(1, 6 * mm))

    story.append(Paragraph("EUR/MWh Levy Reference Note", H2_STYLE))
    story.append(Paragraph(REFERENCE_TARIFFS_NOTE, ITALIC_STYLE))
    story.append(Spacer(1, 6 * mm))

    story.append(Paragraph("Assumptions Completeness", H2_STYLE))
    story.append(Paragraph(_build_assumptions_summary(db, project_id), NORMAL_STYLE))

    doc.build(story, onFirstPage=hf.on_first_page, onLaterPages=hf.on_later_pages)


def export_pdf_fund_note(db, project_id, path, fund_data):
    project = db.get_project(project_id)
    doc = SimpleDocTemplate(path, pagesize=A4, topMargin=25 * mm, bottomMargin=20 * mm,
                             leftMargin=18 * mm, rightMargin=18 * mm)
    hf = _HeaderFooter(project.get("name") or "")
    story = [
        Paragraph("DECOMMISSIONING FUND ADEQUACY NOTE", TITLE_STYLE),
        Spacer(1, 6 * mm),
        _build_cover_table(project),
        Spacer(1, 6 * mm),
        Paragraph("Fund Adequacy Assessment", H2_STYLE),
        Spacer(1, 2 * mm),
    ]
    fund_table = _build_fund_table(fund_data)
    story.append(fund_table if fund_table else Paragraph("No data provided.", NORMAL_STYLE))
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph(
        "Required contributions are indicative, based on the current estimate's accuracy "
        "class and the discount rate defined in the project financial parameters.",
        ITALIC_STYLE))
    doc.build(story, onFirstPage=hf.on_first_page, onLaterPages=hf.on_later_pages)
