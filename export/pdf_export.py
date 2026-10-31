"""
export/pdf_export.py
======================
PDF export for the ISDC Decommissioning Cost Estimation Tool, using
reportlab. Produces a full report (cover, financial summary, ISDC
matrix by Principal Activity, graded-approach applicability, phase
profile, funding plan, EUR/MWh levy note for power reactors,
assumptions completeness) or a standalone funding plan note.
"""

import datetime
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from reportlab.graphics.shapes import Drawing, Line, String
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.widgets.markers import makeMarker

from core.applicability import APPLICABILITY_NOTE, WARN, build_applicability_review
from core.calculator import ISDCCalculator, ESTIMATE_ACCURACY, REFERENCE_TARIFFS_NOTE
from core.funding_plan import (
    PLAN_METHOD_NOTE, compute_funding_plan, cost_profile_for_project, inputs_from_project, sensitivity,
)
from core.isdc_data import ISDC_HIERARCHY
from core.facility_profiles import is_power_reactor

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

# Table-cell styles: text placed in a Paragraph wraps inside its column
# instead of overflowing into the neighbouring cell.
CELL_STYLE = ParagraphStyle("CellStyle", parent=styles["Normal"], fontSize=7.5, leading=9)
CELL_BOLD = ParagraphStyle("CellBold", parent=CELL_STYLE, fontName="Helvetica-Bold")
CELL_9 = ParagraphStyle("Cell9", parent=styles["Normal"], fontSize=9, leading=11)
CELL_8 = ParagraphStyle("Cell8", parent=styles["Normal"], fontSize=8, leading=10)
CELL_8_WHITE = ParagraphStyle("Cell8White", parent=CELL_8, textColor=colors.white)


def _p(text, style=CELL_STYLE):
    """Wrap text in a Paragraph so it wraps within its table column."""
    return Paragraph(escape(str(text)), style)


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
    data = [[_p(k, CELL_9), _p(v, CELL_9)] for k, v in data]
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
            own = entries.get(l2_code) or {}
            own_vals = [own.get(k) or 0.0 for k in ("labour_eur", "investment_eur", "expenses_eur", "contingency_eur")]
            if sum(own_vals):
                # Lump-sum entry on the Level-2 code itself (allowed by the cost matrix).
                data.append([l2_code, _p(f"{l2_title} — lump sum (Level 2)")]
                            + [f"{v:,.0f}" for v in own_vals] + [f"{sum(own_vals):,.0f}"])
                l2_total += sum(own_vals)
            for l3_code, l3_title in l3_list:
                e = entries.get(l3_code, {})
                labour = e.get("labour_eur") or 0.0
                invest = e.get("investment_eur") or 0.0
                expense = e.get("expenses_eur") or 0.0
                conting = e.get("contingency_eur") or 0.0
                total = labour + invest + expense + conting
                if total == 0:
                    continue
                data.append([l3_code, _p(l3_title), f"{labour:,.0f}", f"{invest:,.0f}",
                             f"{expense:,.0f}", f"{conting:,.0f}", f"{total:,.0f}"])
                l2_total += total
            pa_total += l2_total
        if len(data) == 1:
            continue  # no costs entered for this PA
        data.insert(0, [f"PA {pa_code}", _p(pa["title"], CELL_BOLD), "", "", "", "", f"{pa_total:,.0f}"])
        # Widths sum to the 174 mm usable A4 width (210 mm - 2 x 18 mm margins).
        table = Table(data, colWidths=[16 * mm, 56 * mm, 20 * mm, 21 * mm, 20 * mm, 21 * mm, 20 * mm],
                      repeatRows=2)
        table.setStyle(TableStyle([
            ("SPAN", (1, 0), (5, 0)),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
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


def build_applicability_section(db, project):
    """Graded-approach table: rating, basis, cost and status for every PA and Level-2 item."""
    rows = build_applicability_review(project, db)
    n_warn = sum(1 for r in rows if r.severity == WARN)
    out = [Paragraph("Graded Approach — Applicability of ISDC Activities", H2_STYLE),
           Paragraph(escape(APPLICABILITY_NOTE), ITALIC_STYLE), Spacer(1, 2 * mm),
           Paragraph(f"Facility type: <b>{escape(project.get('facility_type') or '-')}</b> &nbsp;&nbsp; "
                     f"Items flagged for review: <b>{n_warn}</b>", NORMAL_STYLE),
           Spacer(1, 2 * mm)]
    data = [[_p(h, CELL_8_WHITE) for h in ("Code", "Activity", "Rating", "Basis", "Cost (EUR)",
                                           "Status / justification")]]
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.lightgrey),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (2, 1), (3, -1), "CENTER"),
        ("ALIGN", (4, 1), (4, -1), "RIGHT"),
    ]
    for i, r in enumerate(rows, start=1):
        status = r.status
        if r.justification and r.justification not in status:
            status += f" — {r.justification}"
        title_style = CELL_BOLD if r.level == 1 else CELL_STYLE
        indent = "" if r.level == 1 else ("&nbsp;&nbsp;" if r.level == 2 else "&nbsp;&nbsp;&nbsp;&nbsp;")
        data.append([r.code, Paragraph(indent + escape(r.title), title_style), r.rating, r.source,
                     f"{r.cost_eur:,.0f}" if r.cost_eur else "-", _p(status)])
        if r.severity == WARN:
            style.append(("BACKGROUND", (0, i), (-1, i), RED))
        elif r.level == 1:
            style.append(("BACKGROUND", (0, i), (-1, i), BLUE2))
        if r.rating == "N" and r.severity != WARN:
            style.append(("TEXTCOLOR", (0, i), (-1, i), colors.grey))
    t = Table(data, colWidths=[16 * mm, 52 * mm, 13 * mm, 15 * mm, 24 * mm, 54 * mm], repeatRows=1)
    t.setStyle(TableStyle(style))
    out.append(t)
    out.append(Spacer(1, 1 * mm))
    out.append(Paragraph("M = Mandatory, D = Dominant cost driver, A = Applicable, C = Conditional, "
                         "N = Not applicable. Basis: Default = generic default for the facility type; "
                         "User = set for this project.", ITALIC_STYLE))
    return out


def _build_phase_table(calc):
    profiles = calc.compute_phase_profiles()
    if not profiles:
        return None
    data = [["Phase", "Type", "Start", "End", "Total (EUR)", "NPV (EUR)"]]
    for p in profiles:
        data.append([_p(p.phase_name, CELL_8), _p(p.phase_type, CELL_8), str(p.start_year), str(p.end_year),
                     f"{p.total_cost_eur:,.0f}", f"{p.npv_cost_eur:,.0f}"])
    table = Table(data, colWidths=[48 * mm, 34 * mm, 16 * mm, 16 * mm, 30 * mm, 30 * mm], repeatRows=1)
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.lightgrey),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
    ]))
    return table


def _kv_table(rows, highlight_rows=()):
    table = Table([[_p(k, CELL_9), _p(v, CELL_9)] for k, v in rows], colWidths=[95 * mm, 70 * mm])
    style = [
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("BACKGROUND", (0, 0), (0, -1), BLUE3),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]
    for r in highlight_rows:
        style += [("BACKGROUND", (0, r), (-1, r), AMBER)]
    table.setStyle(TableStyle(style))
    return table


def _balance_chart(schedule, shutdown_year):
    years = [s.year for s in schedule]
    balances = [s.closing_balance / 1e6 for s in schedule]
    d = Drawing(170 * mm, 62 * mm)
    lp = LinePlot()
    lp.x, lp.y = 18 * mm, 10 * mm
    lp.width, lp.height = 145 * mm, 45 * mm
    lp.data = [list(zip(years, balances))]
    lp.lines[0].strokeColor = BLUE1
    lp.lines[0].strokeWidth = 1.5
    lp.lines[0].symbol = makeMarker("Circle", size=2)
    lp.xValueAxis.valueMin, lp.xValueAxis.valueMax = min(years), max(years)
    span = max(years) - min(years)
    lp.xValueAxis.valueStep = 5 if span > 15 else (2 if span > 6 else 1)
    lp.xValueAxis.labels.fontSize = 7
    lp.xValueAxis.labelTextFormat = "%d"
    lp.yValueAxis.valueMin = 0
    top = max(max(balances), 1.0)
    magnitude = 10 ** (len(str(int(top))) - 1)
    step = next(m * magnitude for m in (0.2, 0.25, 0.5, 1, 2, 2.5, 5, 10) if top / (m * magnitude) <= 6)
    lp.yValueAxis.valueStep = step
    lp.yValueAxis.valueMax = step * (int(top / step) + 1)
    lp.yValueAxis.labels.fontSize = 7
    lp.yValueAxis.labelTextFormat = "{:,.0f}".format
    lp.yValueAxis.visibleGrid = True
    lp.yValueAxis.gridStrokeColor = colors.HexColor("#E0E0E0")
    d.add(lp)
    d.add(String(0, 58 * mm, "Fund balance at year end (million EUR)", fontSize=8, fillColor=NAVY))
    if min(years) <= shutdown_year <= max(years):
        x = lp.x + lp.width * (shutdown_year - min(years)) / max(span, 1)
        d.add(Line(x, lp.y, x, lp.y + lp.height, strokeColor=colors.HexColor("#B03030"),
                   strokeDashArray=[3, 2], strokeWidth=0.8))
        d.add(String(x + 3, lp.y + 4, f"Shutdown {shutdown_year}", fontSize=7,
                     fillColor=colors.HexColor("#B03030")))
    return d


def build_funding_plan_section(db, project):
    """Flowables for the funding plan, or [] if no plan has been set up."""
    inp = inputs_from_project(project)
    if not inp:
        return []
    profile = cost_profile_for_project(project, db)
    if not profile:
        return []
    res = compute_funding_plan(inp, profile)
    unit = {12: "month", 4: "quarter", 1: "year"}[res.periods_per_year]
    out = [Paragraph("Decommissioning Funding Plan", H2_STYLE), Spacer(1, 1 * mm),
           Paragraph(PLAN_METHOD_NOTE, ITALIC_STYLE), Spacer(1, 3 * mm)]

    out.append(Paragraph("<b>Plan inputs</b>", NORMAL_STYLE))
    out.append(Spacer(1, 1 * mm))
    out.append(_kv_table([
        ["Plan start year (first contribution)", str(inp.start_year)],
        ["Shutdown year (contributions stop)", str(inp.shutdown_year)],
        ["Cost estimate price base year", str(inp.base_year)],
        ["Fund balance at plan start", _money(inp.opening_balance_eur)],
        ["Expected fund return (nominal, per year)", f"{inp.fund_return_pct:.2f} %"],
        ["Cost escalation / inflation (per year)", f"{inp.cost_escalation_pct:.2f} %"],
        ["Payment frequency", inp.frequency],
        ["Yearly increase of payments", f"{inp.contribution_growth_pct:.2f} %"
         + (" (level payments)" if not inp.contribution_growth_pct else "")],
    ]))
    out.append(Spacer(1, 4 * mm))

    out.append(Paragraph("<b>Required contributions</b>", NORMAL_STYLE))
    out.append(Spacer(1, 1 * mm))
    rows = [
        [f"Required payment per {unit}", _money(res.payment_per_period)],
        ["Equivalent per year (first year)", _money(res.first_year_annual_contribution)],
    ]
    if res.eur_per_mwh:
        rows.append(["Equivalent per MWh generated (first year)", f"{res.eur_per_mwh:,.3f} EUR/MWh"])
    rows += [
        ["Number of contribution years", str(res.contribution_years)],
        ["Fund balance needed at shutdown", _money(res.balance_at_shutdown)],
        ["Total contributions paid", _money(res.total_contributions)],
        ["Total fund returns earned", _money(res.total_returns)],
        ["Decommissioning costs, base-year prices", _money(res.total_costs_base)],
        ["Decommissioning costs, escalated (nominal)", _money(res.total_costs_nominal)],
    ]
    out.append(_kv_table(rows, highlight_rows=(0,)))
    if res.message:
        out.append(Spacer(1, 1 * mm))
        out.append(Paragraph(escape(res.message), ITALIC_STYLE))
    out.append(Spacer(1, 4 * mm))

    bounds = ESTIMATE_ACCURACY.get(project.get("estimate_type") or "Budgetary", ESTIMATE_ACCURACY["Budgetary"])
    out.append(Paragraph("<b>Sensitivity</b> — first-year contribution per year", NORMAL_STYLE))
    out.append(Spacer(1, 1 * mm))
    out.append(_kv_table([[label, _money(v)] for label, v in
                          sensitivity(inp, profile, 1 + bounds["upper_pct"] / 100.0)]))
    out.append(PageBreak())

    out.append(Paragraph("Funding Plan — Fund Balance and Yearly Schedule", H2_STYLE))
    out.append(_balance_chart(res.schedule, inp.shutdown_year))
    out.append(Spacer(1, 3 * mm))
    data = [[_p(h, CELL_8_WHITE) for h in
             ["Year", "Stage", "Opening balance", "Contributions", "Fund return", "Costs paid", "Closing balance"]]]
    for srow in res.schedule:
        data.append([str(srow.year), srow.stage] + [f"{v:,.0f}" for v in (
            srow.opening_balance, srow.contributions, srow.returns, srow.costs_paid, srow.closing_balance)])
    t = Table(data, colWidths=[14 * mm, 24 * mm, 28 * mm, 27 * mm, 26 * mm, 27 * mm, 28 * mm], repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.lightgrey),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]
    for i, srow in enumerate(res.schedule, start=1):
        if srow.year == inp.shutdown_year:
            style.append(("BACKGROUND", (0, i), (-1, i), AMBER))
    t.setStyle(TableStyle(style))
    out.append(t)
    return out


def _build_assumptions_summary(db, project_id):
    rows = db.get_project_assumptions(project_id)
    total = len(rows)
    documented = sum(1 for r in rows if r.get("documented"))
    pct = (100 * documented / total) if total else 0
    return f"Assumptions documented: {documented} / {total} ({pct:.0f}%)"


# ---------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------

def export_pdf_report(db, project_id, path, include_matrix=True):
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
        story.extend(build_applicability_section(db, project))
        story.append(PageBreak())

    story.append(Paragraph("Phase Cost Profile", H2_STYLE))
    story.append(Spacer(1, 2 * mm))
    phase_table = _build_phase_table(calc)
    story.append(phase_table if phase_table else Paragraph("No phases defined.", NORMAL_STYLE))
    story.append(Spacer(1, 6 * mm))

    plan = build_funding_plan_section(db, project)
    if plan:
        story.append(PageBreak())
        story.extend(plan)
        story.append(Spacer(1, 6 * mm))

    if is_power_reactor(project.get("facility_type")):
        story.append(Paragraph("EUR/MWh Levy Reference Note", H2_STYLE))
        story.append(Paragraph(REFERENCE_TARIFFS_NOTE, ITALIC_STYLE))
        story.append(Spacer(1, 6 * mm))

    story.append(Paragraph("Assumptions Completeness", H2_STYLE))
    story.append(Paragraph(_build_assumptions_summary(db, project_id), NORMAL_STYLE))

    doc.build(story, onFirstPage=hf.on_first_page, onLaterPages=hf.on_later_pages)


def export_pdf_funding_plan_note(db, project_id, path):
    """Standalone note: project cover table plus the funding plan section."""
    project = db.get_project(project_id)
    doc = SimpleDocTemplate(path, pagesize=A4, topMargin=25 * mm, bottomMargin=20 * mm,
                             leftMargin=18 * mm, rightMargin=18 * mm)
    hf = _HeaderFooter(project.get("name") or "")
    story = [
        Paragraph("Decommissioning Funding Plan Note", TITLE_STYLE),
        Spacer(1, 6 * mm),
        _build_cover_table(project),
        PageBreak(),
    ]
    plan = build_funding_plan_section(db, project)
    story.extend(plan if plan else [Paragraph(
        "No funding plan has been set up for this project (Reports > Funding Plan).", NORMAL_STYLE)])
    doc.build(story, onFirstPage=hf.on_first_page, onLaterPages=hf.on_later_pages)
