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

from core.isdc_data import ancestors, pa_of

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

# Default PA-level applicability (ISDC 2012 Principal Activities) used as a
# base before facility-specific overrides below.
PA_DEFAULT = {
    "01": D,  # Pre-decommissioning actions
    "02": D,  # Facility shutdown activities
    "03": C,  # Additional activities for safe enclosure or entombment (depends on strategy)
    "04": D,  # Dismantling activities within the controlled area
    "05": D,  # Waste processing, storage and disposal
    "06": A,  # Site infrastructure and operation
    "07": A,  # Conventional dismantling, demolition and site restoration
    "08": M,  # Project management, engineering and support
    "09": C,  # Research and development
    "10": C,  # Fuel and nuclear material
    "11": A,  # Miscellaneous expenditures
}

# Facility-type overrides at PA level (codes not listed inherit PA_DEFAULT).
CODE_APPLICABILITY = {
    "NPP-CANDU": dict(PA_DEFAULT, **{"10": D}),
    "NPP-PWR":   dict(PA_DEFAULT, **{"10": D}),
    "NPP-BWR":   dict(PA_DEFAULT, **{"10": D}),
    "NPP-VVER":  dict(PA_DEFAULT, **{"10": D}),
    "RR":        dict(PA_DEFAULT, **{"04": A, "10": D}),
    "FCF-UF":    dict(PA_DEFAULT, **{"10": D}),
    "FCF-ENR":   dict(PA_DEFAULT, **{"10": D}),
    "FCF-REP":   dict(PA_DEFAULT, **{"10": D}),
    "WSF":       dict(PA_DEFAULT, **{"02": A, "04": A, "10": N}),
    "SFS":       dict(PA_DEFAULT, **{"02": A, "04": A, "10": D}),
    "WDF":       dict(PA_DEFAULT, **{"02": A, "04": A, "07": D, "10": N}),
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
# Activity-level defaults for the graded approach
# ---------------------------------------------------------------------
# Typical Activities inherit their Activity Group rating, which inherits
# the Principal Activity rating, unless a more specific rule is listed.
# Each rule is (rating, justification). PA 03 follows the decommissioning
# strategy. These are generic engineering defaults; users can override
# any code per project with their own justification.

APPLICABILITY_LABELS = {
    M: "Mandatory",
    D: "Dominant cost driver",
    A: "Applicable",
    C: "Conditional",
    N: "Not applicable",
}

REACTOR_TYPES = {"NPP-CANDU", "NPP-PWR", "NPP-BWR", "NPP-VVER", "RR"}
FUEL_CYCLE_TYPES = {"FCF-UF", "FCF-ENR", "FCF-REP"}
NO_SPENT_FUEL_TYPES = {"FCF-UF", "FCF-ENR", "WSF", "WDF"}

_NO_REACTOR = (N, "No reactor at this facility type.")
_FCF_ONLY = (N, "Applies to fuel cycle facilities only.")
_NO_SPENT_FUEL = (N, "No irradiated (spent) fuel is handled at this facility type.")
_NO_POWER = (N, "No electricity-generating system at this facility type.")

# Defaults for every facility type (Activity Group or Typical Activity codes).
ACTIVITY_COMMON = {
    "07.0600": (C, "Only if the end state is limited or restricted release of the site."),
    "08.0600": (C, "Only if work is contracted out."),
    "08.0700": (C, "Only if work is contracted out."),
    "08.0800": (C, "Only if work is contracted out."),
    "08.0900": (C, "Only if work is contracted out."),
    "08.1000": (C, "Only if work is contracted out."),
    "10.0200": (C, "Only if a dedicated buffer storage for fuel/nuclear material is built."),
    "10.0300": (C, "Only if a dedicated buffer storage for fuel/nuclear material is built."),
    "11.0400": (C, "Only if equipment, materials, buildings or the site will be sold or reused."),
}


def _activity_defaults(facility_type: str):
    t = dict(ACTIVITY_COMMON)
    reactor = facility_type in REACTOR_TYPES
    if facility_type and not reactor:
        for code in ("04.0103", "04.0501", "04.0502", "04.0503"):
            t[code] = _NO_REACTOR
    if facility_type in REACTOR_TYPES or facility_type in {"WSF", "SFS", "WDF"}:
        for code in ("02.0506", "04.0104", "04.0504"):
            t[code] = _FCF_ONLY
    if facility_type in NO_SPENT_FUEL_TYPES:
        for code in ("02.0102", "02.0103", "02.0202"):
            t[code] = _NO_SPENT_FUEL
    if facility_type and not is_power_reactor(facility_type):
        t["07.0201"] = _NO_POWER
    if is_power_reactor(facility_type):
        t["02.0100"] = (D, "Defueling, spent fuel cooling and plant stabilisation after final shutdown.")
        t["10.0100"] = (D, "Spent fuel removal from the reactor and pools to external storage.")
    if facility_type == "RR":
        t["10.0100"] = (A, "Research reactor fuel inventory is usually small.")
    if facility_type in ("FCF-UF", "FCF-ENR"):
        t["05.0200"] = (N, "No high-level waste at this facility type.")
        t["05.0700"] = (N, "No high-level waste at this facility type.")
        t["10.0100"] = (D, "Recovery and removal of uranium inventory and hold-up in process equipment.")
    if facility_type == "FCF-REP":
        t["10.0100"] = (D, "Removal of spent fuel, separated plutonium/uranium and other nuclear materials.")
        t["05.0200"] = (D, "Historical/legacy high-level waste (e.g. liquid HLW in tanks).")
    if facility_type == "SFS":
        t["10.0100"] = (D, "Spent fuel casks/canisters must be transferred before decommissioning.")
    if facility_type == "WDF":
        t["04.0500"] = (C, "Limited process systems; work is mainly closure and capping.")
    return t


def _strategy_defaults(strategy: str):
    """PA 03 (safe enclosure / entombment) depends on the decommissioning strategy."""
    s = (strategy or "").upper()
    if s.startswith("DECON"):
        return {"03": (N, "Immediate dismantling (DECON): no safe enclosure or entombment.")}
    if s.startswith("SAFSTOR"):
        return {"03": (D, "Deferred dismantling (SAFSTOR) with a safe enclosure period."),
                "03.0100": (D, "Deferred dismantling (SAFSTOR): preparation for safe enclosure."),
                "03.0200": (D, "Deferred dismantling (SAFSTOR): isolating and securing structures."),
                "03.0300": (N, "Not an entombment strategy.")}
    if s.startswith("ENTOMB"):
        return {"03": (D, "Entombment strategy."),
                "03.0100": (C, "Only parts of safe-enclosure preparation may be needed.")}
    return {}


def default_applicability(facility_type: str, code: str, strategy: str = None):
    """(rating, justification, rule_code) from the generic defaults.

    The most specific rule wins: Typical Activity, then Activity Group,
    then Principal Activity. rule_code is the code the rating was defined
    at, so callers can tell an explicit rating from an inherited one.
    """
    table = dict(_activity_defaults(facility_type), **_strategy_defaults(strategy))
    for c in ancestors(code):
        if c in table:
            rating, why = table[c]
            return rating, why, c
    pa = pa_of(code)
    rating = CODE_APPLICABILITY.get(facility_type, PA_DEFAULT).get(pa, A)
    why = "Not applicable to this facility type." if rating == N else ""
    return rating, why, pa


def effective_applicability(facility_type: str, code: str, overrides=None, strategy: str = None):
    """Applicability of a Principal Activity / Activity Group / Typical Activity.

    overrides: {code: {"rating": str, "justification": str}} set by the user.
    User overrides win over defaults; within each, the most specific code wins.
    Returns dict(rating, justification, source, rule_code).
    """
    overrides = overrides or {}
    for c in ancestors(code):
        o = overrides.get(c)
        if o and o.get("rating"):
            return {"rating": o["rating"], "justification": o.get("justification") or "",
                    "source": "User", "rule_code": c}
    rating, why, rule = default_applicability(facility_type, code, strategy)
    return {"rating": rating, "justification": why, "source": "Default", "rule_code": rule}


def get_code_applicability(facility_type: str, code: str, strategy: str = None) -> str:
    """Default rating for a Principal Activity, Activity Group or Typical Activity."""
    return default_applicability(facility_type, code, strategy)[0]


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
