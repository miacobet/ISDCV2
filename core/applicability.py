"""
core/applicability.py
======================
Graded-approach review of a project's cost estimate: for every Principal
Activity (PA) and Level-2 group, the effective applicability rating
(default for the facility type, or the user's override with
justification), the cost entered, and a status that flags items a
reviewer would question.

Used by the cost matrix (colours and warnings), the PDF report and the
Excel export, so all three always agree.
"""

from dataclasses import dataclass
from typing import Dict, List

from core.facility_profiles import APPLICABILITY_LABELS, effective_applicability
from core.isdc_data import ISDC_HIERARCHY

CONTINGENCY_PA = "11"

OK, INFO, WARN = "ok", "info", "warn"


@dataclass
class ApplicabilityRow:
    code: str
    level: int                # 1 = Principal Activity, 2 = Level-2 group, 3 = Level-3 (user-rated)
    title: str
    rating: str               # M / D / A / C / N
    source: str               # "Default" or "User"
    justification: str
    explicit: bool            # rating defined at this code (not inherited from the PA)
    cost_eur: float
    status: str
    severity: str             # ok / info / warn

    @property
    def rating_label(self) -> str:
        return APPLICABILITY_LABELS.get(self.rating, self.rating)


def _entry_total(e: Dict) -> float:
    return sum((e.get(k) or 0.0) for k in ("labour_eur", "investment_eur", "expenses_eur", "contingency_eur"))


def line_item_contingency(entries: Dict[str, Dict]) -> float:
    """Contingency entered in the Contingency column of activities outside PA 11."""
    return sum((e.get("contingency_eur") or 0.0) for code, e in entries.items()
               if not code.startswith(CONTINGENCY_PA))


def _status(code: str, level: int, rating: str, explicit: bool, cost: float,
            justification: str, source: str, line_contingency: float):
    if code == CONTINGENCY_PA:
        if cost == 0 and line_contingency > 0:
            return f"Covered by contingency entered on each activity ({line_contingency:,.0f} EUR)", OK
        if cost > 0 and line_contingency > 0:
            return ("Contingency entered both here and on individual activities — "
                    "check it is not counted twice"), WARN
        if cost == 0:
            return "No contingency entered anywhere in the estimate", WARN
    if code.startswith(CONTINGENCY_PA + ".") and cost == 0 and line_contingency > 0:
        return "Covered by contingency entered on each activity", OK
    if rating == "N":
        if cost > 0:
            return "Cost entered on an item rated Not applicable", WARN
        return "Excluded (not applicable)", OK
    if cost > 0:
        return "Included", OK
    # No cost entered:
    if source == "User" and justification:
        return "No cost — justified by user", OK
    if rating in ("M", "D") and (level == 1 or explicit):
        return ("Mandatory item with no cost — enter costs or justify" if rating == "M"
                else "Dominant cost driver with no cost — enter costs or justify"), WARN
    if rating == "C":
        return "Not included (conditional)", INFO
    return "No cost entered", INFO


def build_applicability_review(project: Dict, db) -> List[ApplicabilityRow]:
    facility_type = project.get("facility_type")
    overrides = db.get_applicability_overrides(project["id"])
    entries = db.get_cost_entries(project["id"])
    line_contingency = line_item_contingency(entries)

    def cost_under(code: str) -> float:
        return sum(_entry_total(e) for c, e in entries.items() if c == code or c.startswith(code + "."))

    rows: List[ApplicabilityRow] = []
    for pa_code, pa in ISDC_HIERARCHY.items():
        codes = [(pa_code, 1, pa["title"])]
        for l2, (t, l3_list) in pa["groups"].items():
            codes.append((l2, 2, t))
            # Level-3 items only appear when the user rated them individually.
            codes += [(l3, 3, t3) for l3, t3 in l3_list if l3 in overrides]
        for code, level, title in codes:
            eff = effective_applicability(facility_type, code, overrides)
            explicit = eff["rule_code"] == code
            cost = cost_under(code)
            status, severity = _status(code, level, eff["rating"], explicit, cost,
                                       eff["justification"], eff["source"], line_contingency)
            rows.append(ApplicabilityRow(
                code=code, level=level, title=title, rating=eff["rating"], source=eff["source"],
                justification=eff["justification"], explicit=explicit, cost_eur=cost,
                status=status, severity=severity,
            ))
    return rows


def level3_cost_on_not_applicable(project: Dict, db) -> List[str]:
    """Level-3 codes with costs whose effective rating is N (rated at any level)."""
    overrides = db.get_applicability_overrides(project["id"])
    out = []
    for code, e in db.get_cost_entries(project["id"]).items():
        if _entry_total(e) > 0 and effective_applicability(
                project.get("facility_type"), code, overrides)["rating"] == "N":
            out.append(code)
    return sorted(out)


APPLICABILITY_NOTE = (
    "Graded approach: each ISDC item is rated for this facility type as Mandatory (M), Dominant cost "
    "driver (D), Applicable (A), Conditional (C) or Not applicable (N). Ratings marked 'Default' are generic "
    "engineering defaults for the facility type; ratings marked 'User' were set for this project with the "
    "justification shown. Items flagged for review should be costed or justified before submission."
)
