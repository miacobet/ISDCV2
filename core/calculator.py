"""
core/calculator.py
===================
Financial calculation engine for the ISDC Decommissioning Cost
Estimation Tool. All monetary calculations are performed in EUR as the
primary currency; local-currency figures are derived informationally
using the project's user-entered conversion rate.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any

from core.isdc_data import ISDC_HIERARCHY

# ---------------------------------------------------------------------
# Reference constants
# ---------------------------------------------------------------------

ESTIMATE_ACCURACY = {
    "Order-of-magnitude": {"lower_pct": -30.0, "upper_pct": 50.0},
    "Budgetary":           {"lower_pct": -15.0, "upper_pct": 30.0},
    "Definitive":          {"lower_pct": -5.0,  "upper_pct": 15.0},
}

CONTINGENCY_RANGES = {
    "Order-of-magnitude": (20.0, 35.0),
    "Budgetary":           (10.0, 20.0),
    "Definitive":           (5.0, 10.0),
}

WASTE_CLASSES = ["HLW", "ILW", "LLW", "VLLW", "VSLW", "EW"]
WASTE_CLASS_LABELS = {
    "HLW":  "High Level Waste",
    "ILW":  "Intermediate Level Waste",
    "LLW":  "Low Level Waste",
    "VLLW": "Very Low Level Waste",
    "VSLW": "Very Short Lived Waste",
    "EW":   "Exempt Waste",
}

PA_LABELS = {pa_code: pa["title"] for pa_code, pa in ISDC_HIERARCHY.items()}

# Informational only — NOT a substitute for applicable national legislation.
REFERENCE_TARIFFS_NOTE = (
    "Reference values shown for comparison purposes only. Users must apply the "
    "tariff rates required by their applicable national legislation and enter "
    "their own rates in the project settings."
)
REFERENCE_TARIFFS = {
    "decom_eur_per_mwh_low": 1.0,
    "decom_eur_per_mwh_high": 3.0,
    "waste_eur_per_mwh_low": 0.2,
    "waste_eur_per_mwh_high": 1.0,
}


# ---------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------

@dataclass
class PATotal:
    pa_code: str
    title: str
    labour_eur: float = 0.0
    investment_eur: float = 0.0
    expenses_eur: float = 0.0
    contingency_eur: float = 0.0

    @property
    def total_eur(self) -> float:
        return self.labour_eur + self.investment_eur + self.expenses_eur + self.contingency_eur


@dataclass
class ProjectFinancials:
    pa_totals: List[PATotal] = field(default_factory=list)
    labour_total_eur: float = 0.0
    investment_total_eur: float = 0.0
    expenses_total_eur: float = 0.0
    contingency_total_eur: float = 0.0
    grand_total_eur: float = 0.0
    grand_total_local: float = 0.0
    lower_bound: float = 0.0
    upper_bound: float = 0.0
    npv_total: float = 0.0
    outturn_total: float = 0.0
    accuracy_class: str = "Budgetary"


@dataclass
class PhaseProfile:
    phase_id: int
    phase_name: str
    phase_type: str
    start_year: int
    end_year: int
    total_cost_eur: float = 0.0
    npv_cost_eur: float = 0.0


@dataclass
class MWhCalculation:
    annual_fund_contribution_eur: float = 0.0
    required_levy_eur_per_mwh: float = 0.0
    required_levy_local_per_mwh: float = 0.0
    reference_decom_tariff_low: float = 0.0
    reference_decom_tariff_high: float = 0.0
    reference_waste_tariff_low: float = 0.0
    reference_waste_tariff_high: float = 0.0
    remaining_liability_eur: float = 0.0


class ISDCCalculator:
    def __init__(self, project: Dict[str, Any], db):
        self.project = project or {}
        self.db = db
        self.project_id = self.project.get("id")

    # ------------------------------------------------------------------
    def _rate(self) -> float:
        try:
            r = float(self.project.get("local_rate") or 1.0)
            return r if r > 0 else 1.0
        except (TypeError, ValueError):
            return 1.0

    def _discount_rate(self) -> float:
        try:
            return float(self.project.get("discount_rate") or 3.0) / 100.0
        except (TypeError, ValueError):
            return 0.03

    def _inflation_rate(self) -> float:
        try:
            return float(self.project.get("inflation_rate") or 2.0) / 100.0
        except (TypeError, ValueError):
            return 0.02

    def _accuracy_class(self) -> str:
        return self.project.get("estimate_type") or "Budgetary"

    # ------------------------------------------------------------------
    def compute_financials(self) -> ProjectFinancials:
        entries = self.db.get_cost_entries(self.project_id) if self.project_id else {}
        pa_map: Dict[str, PATotal] = {
            pa_code: PATotal(pa_code=pa_code, title=pa["title"])
            for pa_code, pa in ISDC_HIERARCHY.items()
        }

        for code, entry in entries.items():
            pa_code = code.split(".")[0]
            pa = pa_map.get(pa_code)
            if not pa:
                continue
            pa.labour_eur += entry.get("labour_eur") or 0.0
            pa.investment_eur += entry.get("investment_eur") or 0.0
            pa.expenses_eur += entry.get("expenses_eur") or 0.0
            pa.contingency_eur += entry.get("contingency_eur") or 0.0

        financials = ProjectFinancials()
        financials.pa_totals = list(pa_map.values())
        financials.labour_total_eur = sum(p.labour_eur for p in financials.pa_totals)
        financials.investment_total_eur = sum(p.investment_eur for p in financials.pa_totals)
        financials.expenses_total_eur = sum(p.expenses_eur for p in financials.pa_totals)
        financials.contingency_total_eur = sum(p.contingency_eur for p in financials.pa_totals)
        financials.grand_total_eur = (
            financials.labour_total_eur + financials.investment_total_eur
            + financials.expenses_total_eur + financials.contingency_total_eur
        )
        financials.grand_total_local = financials.grand_total_eur * self._rate()

        accuracy_class = self._accuracy_class()
        financials.accuracy_class = accuracy_class
        bounds = ESTIMATE_ACCURACY.get(accuracy_class, ESTIMATE_ACCURACY["Budgetary"])
        financials.lower_bound = financials.grand_total_eur * (1 + bounds["lower_pct"] / 100.0)
        financials.upper_bound = financials.grand_total_eur * (1 + bounds["upper_pct"] / 100.0)

        phase_profiles = self.compute_phase_profiles()
        if phase_profiles:
            financials.npv_total = sum(p.npv_cost_eur for p in phase_profiles)
        else:
            # Default: assume a flat 10-year midpoint discounting if no phases defined.
            financials.npv_total = financials.grand_total_eur / ((1 + self._discount_rate()) ** 5)
        financials.outturn_total = financials.grand_total_eur

        return financials

    # ------------------------------------------------------------------
    def compute_phase_profiles(self) -> List[PhaseProfile]:
        if not self.project_id:
            return []
        phases = self.db.get_phases(self.project_id)
        if not phases:
            return []
        entries = self.db.get_cost_entries(self.project_id)
        base_year = int(self.project.get("base_year") or phases[0]["start_year"])
        discount_rate = self._discount_rate()

        # Sum cost entries by phase_id
        phase_cost: Dict[int, float] = {}
        unallocated = 0.0
        for code, entry in entries.items():
            total = (entry.get("labour_eur") or 0) + (entry.get("investment_eur") or 0) \
                + (entry.get("expenses_eur") or 0) + (entry.get("contingency_eur") or 0)
            pid = entry.get("phase_id")
            if pid:
                phase_cost[pid] = phase_cost.get(pid, 0.0) + total
            else:
                unallocated += total

        profiles = []
        total_duration = sum(max(ph["end_year"] - ph["start_year"], 1) for ph in phases)
        for ph in phases:
            cost_eur = phase_cost.get(ph["id"], 0.0)
            if unallocated and total_duration:
                duration = max(ph["end_year"] - ph["start_year"], 1)
                cost_eur += unallocated * (duration / total_duration)
            midpoint_year = (ph["start_year"] + ph["end_year"]) / 2.0
            years_from_base = max(midpoint_year - base_year, 0)
            npv_cost = cost_eur / ((1 + discount_rate) ** years_from_base)
            profiles.append(PhaseProfile(
                phase_id=ph["id"], phase_name=ph["phase_name"], phase_type=ph["phase_type"],
                start_year=ph["start_year"], end_year=ph["end_year"],
                total_cost_eur=cost_eur, npv_cost_eur=npv_cost,
            ))
        return profiles

    # ------------------------------------------------------------------
    def compute_fund_adequacy(self, costs_incurred_eur: float, fund_balance_eur: float,
                               years_remaining: float) -> Dict[str, Any]:
        financials = self.compute_financials()
        total_estimated_cost_eur = financials.grand_total_eur
        remaining_liability_eur = max(total_estimated_cost_eur - costs_incurred_eur, 0.0)

        discount_rate = self._discount_rate()
        years_remaining = max(years_remaining, 0.0)
        npv_remaining_eur = remaining_liability_eur / ((1 + discount_rate) ** years_remaining) \
            if years_remaining > 0 else remaining_liability_eur

        bounds = ESTIMATE_ACCURACY.get(financials.accuracy_class, ESTIMATE_ACCURACY["Budgetary"])
        lower_bound_npv_eur = npv_remaining_eur * (1 + bounds["lower_pct"] / 100.0)
        upper_bound_npv_eur = npv_remaining_eur * (1 + bounds["upper_pct"] / 100.0)

        shortfall_surplus_eur = fund_balance_eur - npv_remaining_eur

        if years_remaining > 0 and discount_rate > 0:
            annuity_factor = (1 - (1 + discount_rate) ** (-years_remaining)) / discount_rate
        else:
            annuity_factor = years_remaining if years_remaining > 0 else 1.0
        funding_gap_eur = max(npv_remaining_eur - fund_balance_eur, 0.0)
        annual_provision_eur = funding_gap_eur / annuity_factor if annuity_factor > 0 else funding_gap_eur

        return {
            "total_estimated_cost_eur": total_estimated_cost_eur,
            "costs_incurred_eur": costs_incurred_eur,
            "remaining_liability_eur": remaining_liability_eur,
            "npv_remaining_eur": npv_remaining_eur,
            "lower_bound_npv_eur": lower_bound_npv_eur,
            "upper_bound_npv_eur": upper_bound_npv_eur,
            "current_fund_balance_eur": fund_balance_eur,
            "shortfall_surplus_eur": shortfall_surplus_eur,
            "annual_provision_eur": annual_provision_eur,
            "years_remaining": years_remaining,
        }

    # ------------------------------------------------------------------
    def compute_mwh_levy(self, annual_energy_mwh: float, remaining_operational_years: float,
                          current_fund_balance_eur: float, user_decom_tariff: float = 0.0,
                          user_waste_tariff: float = 0.0) -> MWhCalculation:
        financials = self.compute_financials()
        total_cost_eur = financials.grand_total_eur
        remaining_liability_eur = max(total_cost_eur - current_fund_balance_eur, 0.0)

        discount_rate = self._discount_rate()
        years = max(remaining_operational_years, 0.0)
        if years > 0 and discount_rate > 0:
            annuity_factor = (1 - (1 + discount_rate) ** (-years)) / discount_rate
        else:
            annuity_factor = years if years > 0 else 1.0

        annual_fund_contribution_eur = remaining_liability_eur / annuity_factor if annuity_factor > 0 else remaining_liability_eur

        required_levy_eur_per_mwh = (
            annual_fund_contribution_eur / annual_energy_mwh if annual_energy_mwh > 0 else 0.0
        )
        rate = self._rate()

        result = MWhCalculation()
        result.annual_fund_contribution_eur = annual_fund_contribution_eur
        result.required_levy_eur_per_mwh = required_levy_eur_per_mwh
        result.required_levy_local_per_mwh = required_levy_eur_per_mwh * rate
        result.reference_decom_tariff_low = REFERENCE_TARIFFS["decom_eur_per_mwh_low"]
        result.reference_decom_tariff_high = REFERENCE_TARIFFS["decom_eur_per_mwh_high"]
        result.reference_waste_tariff_low = REFERENCE_TARIFFS["waste_eur_per_mwh_low"]
        result.reference_waste_tariff_high = REFERENCE_TARIFFS["waste_eur_per_mwh_high"]
        result.remaining_liability_eur = remaining_liability_eur
        return result
