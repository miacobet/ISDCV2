"""
core/funding_plan.py
=====================
Decommissioning funding plan: how much must be paid into a segregated
decommissioning fund (monthly, quarterly or yearly) so that the fund can
pay for every decommissioning cost when it falls due.

Generic method (no country-specific rules). All rates are entered by the
user; the applicable national legislation decides which values are
acceptable (allowed fund return, escalation index, review period, ...).

Method
------
1. Cost profile: the cost estimate (base-year prices) is spread evenly
   over the years of each phase (same convention as the phase cost
   profile: a phase covers max(end - start, 1) years from its start year).
   Costs not allocated to a phase are spread over all phases pro rata to
   duration, exactly as in ISDCCalculator.compute_phase_profiles().
2. Escalation: each year's cost is escalated from the base year to the
   year it is spent:  cost_nominal = cost_base * (1 + e) ** (year - base_year).
3. Fund simulation, month by month from the plan start year until the
   last year with costs:
     - the balance earns the fund return, compounded monthly
       (monthly rate = (1 + r) ** (1/12) - 1);
     - contributions are paid at the end of each payment period
       (month / quarter / year) until the shutdown year;
       contributions may grow each year by a user-defined rate;
     - each year's cost is paid out in 12 equal monthly instalments.
4. Required contribution: the fund balance is linear in the payment
   amount, so the smallest first-year payment that keeps the balance
   >= 0 at every month-end is found exactly (no iteration).

Costs falling before the plan start year are treated as already paid.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from core.facility_profiles import is_power_reactor

FREQUENCIES = {"Monthly": 12, "Quarterly": 4, "Yearly": 1}


@dataclass
class FundingPlanInputs:
    start_year: int                       # first year contributions are paid
    shutdown_year: int                    # contributions stop at the start of this year
    base_year: int                        # price base of the cost estimate
    opening_balance_eur: float = 0.0      # fund balance at the start of start_year
    fund_return_pct: float = 4.0          # nominal annual return on the fund
    cost_escalation_pct: float = 2.0      # annual escalation of decommissioning costs
    frequency: str = "Yearly"             # Monthly / Quarterly / Yearly
    contribution_growth_pct: float = 0.0  # 0 = level payments; e.g. inflation = indexed payments
    annual_energy_mwh: float = 0.0        # optional, for an EUR/MWh equivalent


@dataclass
class FundingYear:
    year: int
    opening_balance: float
    contributions: float
    returns: float
    costs_paid: float
    closing_balance: float
    stage: str  # "Accumulation" or "Spending"


@dataclass
class FundingPlanResult:
    feasible: bool
    message: str
    payment_per_period: float             # first-year payment per period
    periods_per_year: int
    first_year_annual_contribution: float
    contribution_years: int
    total_contributions: float
    total_returns: float
    total_costs_nominal: float
    total_costs_base: float
    balance_at_shutdown: float
    final_balance: float
    shortfall_without_contributions: float
    eur_per_mwh: float
    schedule: List[FundingYear] = field(default_factory=list)


# ---------------------------------------------------------------------
def build_cost_profile(phases: List[Dict], phase_costs: Dict[int, float],
                       unallocated: float, fallback_year: int) -> Dict[int, float]:
    """Spread costs (base-year prices) over calendar years.

    phases: dicts with id, start_year, end_year.
    phase_costs: {phase_id: allocated cost}.
    unallocated: cost not linked to a phase (spread pro rata to duration).
    fallback_year: if no phases exist, all costs fall in this year.
    """
    profile: Dict[int, float] = {}
    if not phases:
        total = sum(phase_costs.values()) + unallocated
        if total:
            profile[fallback_year] = total
        return profile
    durations = {ph["id"]: max(int(ph["end_year"]) - int(ph["start_year"]), 1) for ph in phases}
    total_duration = sum(durations.values())
    for ph in phases:
        d = durations[ph["id"]]
        cost = phase_costs.get(ph["id"], 0.0)
        if unallocated and total_duration:
            cost += unallocated * d / total_duration
        for k in range(d):
            y = int(ph["start_year"]) + k
            profile[y] = profile.get(y, 0.0) + cost / d
    return profile


def cost_profile_for_project(project: Dict, db) -> Dict[int, float]:
    """Cost profile (base-year prices) for a stored project."""
    phases = db.get_phases(project["id"])
    entries = db.get_cost_entries(project["id"])
    phase_ids = {ph["id"] for ph in phases}
    phase_costs: Dict[int, float] = {}
    unallocated = 0.0
    for e in entries.values():
        total = sum((e.get(k) or 0.0) for k in
                    ("labour_eur", "investment_eur", "expenses_eur", "contingency_eur"))
        pid = e.get("phase_id")
        if pid in phase_ids:
            phase_costs[pid] = phase_costs.get(pid, 0.0) + total
        else:
            unallocated += total
    fallback = int(project.get("fp_shutdown_year") or project.get("base_year") or 0)
    return build_cost_profile(phases, phase_costs, unallocated, fallback)


# ---------------------------------------------------------------------
def _simulate(inp: FundingPlanInputs, cost_profile: Dict[int, float], payment: float,
              record: bool = False) -> Tuple[List[float], List[FundingYear]]:
    """Run the fund month by month. Returns month-end balances (and the
    yearly schedule if record=True)."""
    ppy = FREQUENCIES.get(inp.frequency, 1)
    months_per_period = 12 // ppy
    r_m = (1 + inp.fund_return_pct / 100.0) ** (1 / 12.0) - 1
    e = inp.cost_escalation_pct / 100.0
    g = inp.contribution_growth_pct / 100.0
    years_with_costs = [y for y, c in cost_profile.items() if c and y >= inp.start_year]
    last_year = max([inp.shutdown_year] + years_with_costs)

    balance = inp.opening_balance_eur
    balances: List[float] = []
    schedule: List[FundingYear] = []
    for year in range(inp.start_year, last_year + 1):
        opening = balance
        y_contrib = y_ret = y_cost = 0.0
        annual_cost = cost_profile.get(year, 0.0) * (1 + e) ** (year - inp.base_year)
        pay = payment * (1 + g) ** (year - inp.start_year) if year < inp.shutdown_year else 0.0
        for m in range(1, 13):
            ret = balance * r_m
            cost = annual_cost / 12.0
            contrib = pay if (pay and m % months_per_period == 0) else 0.0
            balance += ret + contrib - cost
            y_ret += ret
            y_cost += cost
            y_contrib += contrib
            balances.append(balance)
        if record:
            schedule.append(FundingYear(
                year=year, opening_balance=opening, contributions=y_contrib, returns=y_ret,
                costs_paid=y_cost, closing_balance=balance,
                stage="Accumulation" if year < inp.shutdown_year else "Spending",
            ))
    return balances, schedule


def compute_funding_plan(inp: FundingPlanInputs, cost_profile: Dict[int, float]) -> FundingPlanResult:
    ppy = FREQUENCIES.get(inp.frequency, 1)
    contribution_years = max(inp.shutdown_year - inp.start_year, 0)
    total_base = sum(c for y, c in cost_profile.items() if y >= inp.start_year)

    b0, _ = _simulate(inp, cost_profile, 0.0)
    b1, _ = _simulate(inp, cost_profile, 1.0)
    unit = [x1 - x0 for x0, x1 in zip(b0, b1)]  # balance gained per 1 EUR of first payment
    shortfall0 = max(-min(b0), 0.0) if b0 else 0.0

    feasible = True
    message = ""
    payment = 0.0
    if shortfall0 > 0:
        needed = []
        for x0, u in zip(b0, unit):
            if x0 < 0:
                if u <= 1e-12:
                    feasible = False
                    break
                needed.append(-x0 / u)
        if feasible:
            # tiny margin so float rounding never leaves a -1 EUR final balance
            payment = max(needed) * (1 + 1e-9) + 0.01
        else:
            message = ("Costs fall due before any contribution can be paid "
                       "(check the plan start year and shutdown year).")
    else:
        message = "The current fund balance already covers all future costs; no contributions are needed."

    _, schedule = _simulate(inp, cost_profile, payment, record=True)
    at_shutdown = next((s.opening_balance for s in schedule if s.year == inp.shutdown_year),
                       schedule[-1].closing_balance if schedule else inp.opening_balance_eur)
    first_year_annual = payment * ppy if contribution_years else 0.0
    return FundingPlanResult(
        feasible=feasible,
        message=message,
        payment_per_period=payment,
        periods_per_year=ppy,
        first_year_annual_contribution=first_year_annual,
        contribution_years=contribution_years,
        total_contributions=sum(s.contributions for s in schedule),
        total_returns=sum(s.returns for s in schedule),
        total_costs_nominal=sum(s.costs_paid for s in schedule),
        total_costs_base=total_base,
        balance_at_shutdown=at_shutdown,
        final_balance=schedule[-1].closing_balance if schedule else inp.opening_balance_eur,
        shortfall_without_contributions=shortfall0,
        eur_per_mwh=(first_year_annual / inp.annual_energy_mwh) if inp.annual_energy_mwh > 0 else 0.0,
        schedule=schedule,
    )


# ---------------------------------------------------------------------
def inputs_from_project(project: Dict) -> Optional[FundingPlanInputs]:
    """Build inputs from saved project fields; None if no plan was set up."""
    if not project or not project.get("fp_shutdown_year"):
        return None
    base_year = int(project.get("base_year") or project.get("fp_start_year") or 0)
    return FundingPlanInputs(
        start_year=int(project.get("fp_start_year") or base_year),
        shutdown_year=int(project["fp_shutdown_year"]),
        base_year=base_year,
        opening_balance_eur=float(project.get("fp_opening_balance") or 0.0),
        fund_return_pct=float(project.get("fp_return_pct") or 0.0),
        cost_escalation_pct=float(project.get("fp_escalation_pct") or 0.0),
        frequency=project.get("fp_frequency") or "Yearly",
        contribution_growth_pct=float(project.get("fp_growth_pct") or 0.0),
        # EUR/MWh equivalent only for electricity-generating facilities.
        annual_energy_mwh=(float(project.get("annual_energy_mwh") or 0.0)
                           if is_power_reactor(project.get("facility_type")) else 0.0),
    )


def sensitivity(inp: FundingPlanInputs, cost_profile: Dict[int, float],
                upper_bound_factor: float) -> List[Tuple[str, float]]:
    """First-year annual contribution under a few what-if cases."""
    from dataclasses import replace
    cases = [
        ("As entered", inp, cost_profile),
        (f"Fund return {inp.fund_return_pct - 1:.1f}% (-1 pp)",
         replace(inp, fund_return_pct=inp.fund_return_pct - 1), cost_profile),
        (f"Fund return {inp.fund_return_pct + 1:.1f}% (+1 pp)",
         replace(inp, fund_return_pct=inp.fund_return_pct + 1), cost_profile),
        (f"Cost escalation {inp.cost_escalation_pct + 1:.1f}% (+1 pp)",
         replace(inp, cost_escalation_pct=inp.cost_escalation_pct + 1), cost_profile),
        ("Costs at upper bound of accuracy range", inp,
         {y: c * upper_bound_factor for y, c in cost_profile.items()}),
    ]
    return [(label, compute_funding_plan(i, p).first_year_annual_contribution)
            for label, i, p in cases]


PLAN_METHOD_NOTE = (
    "Generic sinking-fund method. Costs (base-year prices) are spread over the phase years, "
    "escalated to the year they are spent, and paid monthly from the fund. The fund earns the "
    "stated return (compounded monthly); contributions are paid at the end of each period until "
    "the shutdown year. The required contribution is the smallest payment that keeps the fund "
    "balance at or above zero at every month-end. Rates are user inputs; the applicable national "
    "legislation governs acceptable returns, escalation indices and review frequency."
)
