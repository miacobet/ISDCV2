"""
core/applicability.py
======================
Graded-approach review of a project's cost estimate: for every Principal
Activity and Activity Group, the effective applicability rating (default
for the facility type and strategy, or the user's override with
justification), the cost entered, and a status that flags items a
reviewer would question. Also checks contingency, which ISDC treats as a
cost category applied to the activities.

Used by the cost matrix (colours and warnings), the PDF report and the
Excel export, so all three always agree.
"""

from dataclasses import dataclass
from typing import Dict, List

from core.facility_profiles import APPLICABILITY_LABELS, effective_applicability
from core.isdc_data import ISDC_HIERARCHY, is_within

OK, INFO, WARN = "ok", "info", "warn"
COST_KEYS = ("labour_eur", "investment_eur", "expenses_eur", "contingency_eur")


@dataclass
class ApplicabilityRow:
    code: str
    level: int                # 1 = Principal Activity, 2 = Activity Group, 3 = Typical Activity (user-rated)
    title: str
    rating: str               # M / D / A / C / N
    source: str               # "Default" or "User"
    justification: str
    explicit: bool            # rating defined at this code (not inherited)
    cost_eur: float
    status: str
    severity: str             # ok / info / warn

    @property
    def rating_label(self) -> str:
        return APPLICABILITY_LABELS.get(self.rating, self.rating)


def _entry_total(e: Dict) -> float:
    return sum((e.get(k) or 0.0) for k in COST_KEYS)


def contingency_summary(entries: Dict[str, Dict]):
    """(contingency EUR, base cost EUR excluding contingency, contingency % of base)."""
    conting = sum((e.get("contingency_eur") or 0.0) for e in entries.values())
    base = sum(_entry_total(e) for e in entries.values()) - conting
    return conting, base, (100.0 * conting / base) if base > 0 else 0.0


def _status(level: int, rating: str, explicit: bool, cost: float, justification: str, source: str):
    if rating == "N":
        if cost != 0:
            return "Cost entered on an item rated Not applicable", WARN
        return "Excluded (not applicable)", OK
    if cost != 0:
        return "Included", OK
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
    strategy = project.get("strategy")
    overrides = db.get_applicability_overrides(project["id"])
    entries = db.get_cost_entries(project["id"])

    def cost_under(code: str) -> float:
        return sum(_entry_total(e) for c, e in entries.items() if is_within(c, code))

    rows: List[ApplicabilityRow] = []
    for pa_code, pa in ISDC_HIERARCHY.items():
        codes = [(pa_code, 1, pa["title"])]
        for group, (title, items) in pa["groups"].items():
            codes.append((group, 2, title))
            # Typical Activities are listed when they carry their own rating
            # (user override, or a default rule specific to that activity).
            for code, t in items:
                eff = effective_applicability(facility_type, code, overrides, strategy)
                if eff["rule_code"] == code:
                    codes.append((code, 3, t))
        for code, level, title in codes:
            eff = effective_applicability(facility_type, code, overrides, strategy)
            explicit = eff["rule_code"] == code
            cost = cost_under(code)
            status, severity = _status(level, eff["rating"], explicit, cost,
                                       eff["justification"], eff["source"])
            rows.append(ApplicabilityRow(
                code=code, level=level, title=title, rating=eff["rating"], source=eff["source"],
                justification=eff["justification"], explicit=explicit, cost_eur=cost,
                status=status, severity=severity,
            ))
    return rows


def contingency_check(project: Dict, db):
    """(message, severity) about the Contingency cost category for the whole estimate."""
    conting, base, pct = contingency_summary(db.get_cost_entries(project["id"]))
    if base <= 0:
        return "No costs entered yet", INFO
    if conting <= 0:
        return "No contingency entered on any activity", WARN
    return f"Contingency {conting:,.0f} EUR = {pct:.1f}% of the base cost", OK


def level3_cost_on_not_applicable(project: Dict, db) -> List[str]:
    """Codes with costs whose effective rating is N (rated at any level)."""
    overrides = db.get_applicability_overrides(project["id"])
    out = []
    for code, e in db.get_cost_entries(project["id"]).items():
        if _entry_total(e) != 0 and effective_applicability(
                project.get("facility_type"), code, overrides, project.get("strategy"))["rating"] == "N":
            out.append(code)
    return sorted(out)


APPLICABILITY_NOTE = (
    "Graded approach: each ISDC item is rated for this facility type and decommissioning strategy as "
    "Mandatory (M), Dominant cost driver (D), Applicable (A), Conditional (C) or Not applicable (N). "
    "Ratings marked 'Default' are generic engineering defaults; ratings marked 'User' were set for this "
    "project with the justification shown. Items flagged for review should be costed or justified before "
    "submission. Contingency is a cost category (ISDC 2012) and is checked for the estimate as a whole."
)
