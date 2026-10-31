"""
core/facility_profiles.py
==========================
Facility-type profiles for the ISDC cost estimation tool.

Defines the facility types the tool supports and, for each, the
applicability of ISDC cost codes (Mandatory / Dominant / Applicable /
Conditional / Not-applicable) plus facility-specific additional items
for the Appendix-B style assumptions register.

No plant, company, or country is referenced anywhere in this module.
Applicability mappings are generic engineering defaults the user should
review and adjust for their own facility and national requirements.
"""

# Applicability codes
M = "M"   # Mandatory
D = "D"   # Dominant cost driver
A = "A"   # Applicable
C = "C"   # Conditional (depends on facility specifics)
N = "N"   # Not applicable

FACILITY_TYPES = {
    "NPP-CANDU": "Nuclear Power Plant – Pressurised Heavy Water Reactor (CANDU type)",
    "NPP-PWR":   "Nuclear Power Plant – Pressurised Water Reactor",
    "NPP-BWR":   "Nuclear Power Plant – Boiling Water Reactor",
    "NPP-VVER":  "Nuclear Power Plant – VVER (PWR-type, Russian design lineage)",
    "RR":        "Research Reactor",
    "FCF-UF":    "Fuel Cycle Facility – Fuel Fabrication",
    "FCF-ENR":   "Fuel Cycle Facility – Enrichment",
    "FCF-REP":   "Fuel Cycle Facility – Reprocessing",
    "WSF":       "Radioactive Waste Storage Facility (interim, wet or dry)",
    "SFS":       "Independent Spent Fuel Storage Facility (ISFSI, dry or wet cask type)",
    "WDF":       "Radioactive Waste Disposal Facility",
    "OTHER":     "Other nuclear or radiological facility",
}

# Default PA-level applicability pattern used as a base before facility-
# specific overrides below. PA codes follow the ISDC 2012 structure:
PA_DEFAULT = {
    "01": D,  # Pre-decommissioning actions
    "02": D,  # Facility shutdown activities
    "03": D,  # Dismantling activities within the controlled area
    "04": D,  # Waste processing, storage and disposal
    "05": A,  # Site infrastructure and operation
    "06": M,  # Project management, engineering and site support
    "07": C,  # Research and development
    "08": C,  # Fuel and nuclear material
    "09": A,  # Miscellaneous expenditures
    "10": C,  # Income
    "11": M,  # Unplanned costs (contingency)
}

# Facility-type overrides at PA level (codes not listed inherit PA_DEFAULT).
CODE_APPLICABILITY = {
    "NPP-CANDU": dict(PA_DEFAULT, **{"08": D}),
    "NPP-PWR":   dict(PA_DEFAULT, **{"08": D}),
    "NPP-BWR":   dict(PA_DEFAULT, **{"08": D}),
    "NPP-VVER":  dict(PA_DEFAULT, **{"08": D}),
    "RR":        dict(PA_DEFAULT, **{"03": A, "08": D, "05": A}),
    "FCF-UF":    dict(PA_DEFAULT, **{"03": D, "08": D, "04": D}),
    "FCF-ENR":   dict(PA_DEFAULT, **{"03": D, "08": A, "04": D}),
    "FCF-REP":   dict(PA_DEFAULT, **{"03": D, "08": D, "04": D}),
    "WSF":       dict(PA_DEFAULT, **{"02": A, "03": A, "04": D, "08": N}),
    "SFS":       dict(PA_DEFAULT, **{"02": A, "03": A, "04": D, "08": D}),
    "WDF":       dict(PA_DEFAULT, **{"02": A, "03": A, "04": D, "08": N}),
    "OTHER":     dict(PA_DEFAULT),
}

POWER_REACTOR_TYPES = {"NPP-CANDU", "NPP-PWR", "NPP-BWR", "NPP-VVER"}

# ---------------------------------------------------------------------
# Facility-specific additional assumption items (Appendix-B style)
# ---------------------------------------------------------------------

CANDU_ASSUMPTIONS = [
    "Heavy-water (D2O) moderator and primary-coolant inventory recovery, upgrading, "
    "and disposition strategy is defined.",
    "Pressure-tube and calandria-tube removal method and waste routing are defined.",
    "End-fitting and feeder-pipe segmentation approach is defined.",
    "On-power-refuelling related systems (fuelling machine, etc.) decontamination "
    "and dismantling sequence is defined.",
]

SFS_ASSUMPTIONS = [
    "Cask or module inventory (dry/wet storage type) at end of storage period is defined.",
    "Final disposition path for stored spent fuel (transfer to disposal facility, "
    "long-term storage extension, etc.) is defined and consistent with the cost estimate.",
    "Cask/canister retrieval, inspection, and transport methodology is defined.",
]

# Items common to all fuel cycle facilities.
FCF_COMMON_ASSUMPTIONS = [
    "Process-specific contamination profile has been characterised.",
    "Special nuclear material inventory reconciliation and safeguards termination "
    "approach is defined.",
    "Process equipment decontamination factors and waste classification assumptions "
    "are defined.",
]

FCF_UF_ASSUMPTIONS = [
    "Uranium hold-up in process equipment, ventilation ducts, filters and drains has been "
    "quantified (e.g. by hold-up measurements) and its recovery method is defined.",
    "Criticality safety controls (mass/geometry limits) during dismantling of equipment "
    "containing enriched-uranium hold-up are defined.",
    "Alpha (uranium) contamination control during dismantling — containment, ventilation "
    "and respiratory protection — is defined.",
    "Disposition of residual fuel materials (powder, pellets, scrap, rejected fuel) is defined.",
    "Chemical and conventional hazards of the process (e.g. HF, ammonia, solvents) have been "
    "identified for the dismantling work.",
    "Clearance strategy for uranium-contaminated materials (surface vs. volumetric "
    "contamination, applicable clearance levels) is defined.",
    "Soil and groundwater contamination (uranium, process chemicals) is characterised or "
    "a characterisation programme is costed.",
] + FCF_COMMON_ASSUMPTIONS

FCF_ENR_ASSUMPTIONS = [
    "Removal of UF6 inventory from cascades, process piping and cylinders, including "
    "cylinder heels, is defined.",
    "Disposition strategy for depleted uranium tails (storage, deconversion, disposal or "
    "reuse) and responsibility for its cost are defined.",
    "Uranium deposits (e.g. UO2F2) in process equipment have been quantified, with "
    "criticality safety controls for enriched deposits.",
    "Hazards from residual UF6 reacting with moist air (HF release) when process "
    "equipment is opened are addressed.",
    "Protection and disposal of sensitive enrichment technology (centrifuges, diffusion "
    "barriers, design information) meet security and export-control requirements.",
    "Strategy for the large volume of slightly contaminated metal (decontamination, "
    "melting/recycling, clearance or disposal) is defined.",
] + FCF_COMMON_ASSUMPTIONS

FCF_REP_ASSUMPTIONS = [
    "Highly active liquid waste and process residues in tanks are retrieved and conditioned "
    "(e.g. vitrified) before decommissioning, or this work is included in the estimate.",
    "Remote or semi-remote dismantling methods for hot cells and high-dose-rate areas are "
    "defined, including shielding and tooling.",
    "Dismantling approach for alpha-contaminated (plutonium, americium) equipment and "
    "gloveboxes is defined.",
    "Disposition of separated plutonium and uranium product inventories is defined.",
    "Criticality safety controls for plutonium and enriched-uranium hold-up are defined.",
    "Retrieval of legacy wastes (e.g. ponds, silos, historic stores) is defined and "
    "included where relevant.",
    "Classification and disposal route for long-lived alpha-bearing and high-level wastes "
    "are defined, including availability of a disposal facility.",
    "Chemical hazards (nitric acid, organic solvents, risk of red-oil reactions) are "
    "addressed for draining and dismantling of process systems.",
] + FCF_COMMON_ASSUMPTIONS

FCF_ASSUMPTIONS = {
    "FCF-UF": FCF_UF_ASSUMPTIONS,
    "FCF-ENR": FCF_ENR_ASSUMPTIONS,
    "FCF-REP": FCF_REP_ASSUMPTIONS,
}

WSF_ASSUMPTIONS = [
    "Waste package inventory and condition at the time of decommissioning is defined.",
    "Retrieval and repackaging strategy for stored waste is defined.",
    "Final destination of retrieved waste (disposal facility, another storage facility) "
    "is defined and consistent with the cost estimate.",
]


def get_facility_type_list():
    return list(FACILITY_TYPES.items())


def get_profile(facility_type: str) -> str:
    return FACILITY_TYPES.get(facility_type, "Unknown facility type")


# ---------------------------------------------------------------------
# Activity-level (Level-2) defaults for the graded approach
# ---------------------------------------------------------------------
# Level-3 codes inherit their Level-2 rating; Level-2 codes inherit their
# PA rating unless listed here. Each entry is (rating, justification).
# These are generic engineering defaults; users can override any code
# per project with their own justification.

APPLICABILITY_LABELS = {
    M: "Mandatory",
    D: "Dominant cost driver",
    A: "Applicable",
    C: "Conditional",
    N: "Not applicable",
}

_NO_SPENT_FUEL = (N, "No irradiated (spent) fuel is handled at this facility type.")
_SAFE_STORAGE = (C, "Only applies if a deferred-dismantling (safe storage) period is planned.")

L2_COMMON = {
    "05.03": _SAFE_STORAGE,
}

L2_APPLICABILITY = {
    "NPP-CANDU": {"08.01": (D, "Spent fuel removal from the reactor and pools/dry storage.")},
    "NPP-PWR":   {"08.01": (D, "Spent fuel removal from the reactor and pools/dry storage.")},
    "NPP-BWR":   {"08.01": (D, "Spent fuel removal from the reactor and pools/dry storage.")},
    "NPP-VVER":  {"08.01": (D, "Spent fuel removal from the reactor and pools/dry storage.")},
    "RR":        {"08.01": (A, "Research reactor fuel inventory is usually small.")},
    "FCF-UF": {
        "08.01": _NO_SPENT_FUEL,
        "08.02": (D, "Recovery and disposition of uranium inventory and hold-up in process equipment."),
    },
    "FCF-ENR": {
        "08.01": _NO_SPENT_FUEL,
        "08.02": (D, "Removal and disposition of UF6 inventory and hold-up."),
    },
    "FCF-REP": {
        "08.01": (D, "Spent fuel receipt and storage pools must be emptied."),
        "08.02": (D, "Recovery and disposition of separated nuclear materials."),
    },
    "SFS": {
        "08.01": (D, "Spent fuel casks/canisters must be transferred before decommissioning."),
        "08.02": (C, "Only if special nuclear material other than spent fuel is stored."),
    },
    "WDF": {
        "03.02": (C, "Limited process systems; work is mainly closure and capping."),
        "04.02": (C, "Interim storage only if operational waste remains at closure."),
    },
}


def default_applicability(facility_type: str, code: str):
    """(rating, justification, rule_code) from the generic defaults.

    rule_code is the code the rating was defined at (PA or Level-2), so
    callers can tell an explicit rating from an inherited one.
    """
    pa_code = code[:2]
    l2_code = code[:5] if len(code) >= 5 else None
    if l2_code:
        table = dict(L2_COMMON, **L2_APPLICABILITY.get(facility_type, {}))
        if l2_code in table:
            rating, why = table[l2_code]
            return rating, why, l2_code
    rating = CODE_APPLICABILITY.get(facility_type, PA_DEFAULT).get(pa_code, A)
    why = "Not applicable to this facility type." if rating == N else ""
    return rating, why, pa_code


def effective_applicability(facility_type: str, code: str, overrides=None):
    """Applicability of a PA / Level-2 / Level-3 code for a project.

    overrides: {code: {"rating": str, "justification": str}} set by the user.
    User overrides win over defaults; within each, the most specific code wins.
    Returns dict(rating, justification, source, rule_code).
    """
    overrides = overrides or {}
    chain = [c for c in (code, code[:5] if len(code) >= 5 else None, code[:2]) if c]
    for c in dict.fromkeys(chain):
        o = overrides.get(c)
        if o and o.get("rating"):
            return {"rating": o["rating"], "justification": o.get("justification") or "",
                    "source": "User", "rule_code": c}
    rating, why, rule = default_applicability(facility_type, code)
    return {"rating": rating, "justification": why, "source": "Default", "rule_code": rule}


def get_code_applicability(facility_type: str, code: str) -> str:
    """Default rating for a PA, Level-2 or Level-3 code."""
    return default_applicability(facility_type, code)[0]


def get_dominant_pas(facility_type: str):
    table = CODE_APPLICABILITY.get(facility_type, PA_DEFAULT)
    return [pa for pa, level in table.items() if level == D]


def is_power_reactor(facility_type: str) -> bool:
    return facility_type in POWER_REACTOR_TYPES


def get_facility_specific_assumptions(facility_type: str):
    if facility_type == "NPP-CANDU":
        return CANDU_ASSUMPTIONS
    if facility_type == "SFS":
        return SFS_ASSUMPTIONS
    if facility_type in FCF_ASSUMPTIONS:
        return FCF_ASSUMPTIONS[facility_type]
    if facility_type in ("WSF", "WDF"):
        return WSF_ASSUMPTIONS
    return []
