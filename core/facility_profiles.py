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

FCF_ASSUMPTIONS = [
    "Process-specific contamination profile (e.g. enrichment, conversion, fabrication, "
    "reprocessing residues) has been characterised.",
    "Special nuclear material inventory reconciliation and safeguards termination "
    "approach is defined.",
    "Process equipment decontamination factors and waste classification assumptions "
    "are defined.",
]

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


def get_code_applicability(facility_type: str, pa_code: str) -> str:
    table = CODE_APPLICABILITY.get(facility_type, PA_DEFAULT)
    return table.get(pa_code, A)


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
    if facility_type in ("FCF-UF", "FCF-ENR", "FCF-REP"):
        return FCF_ASSUMPTIONS
    if facility_type in ("WSF", "WDF"):
        return WSF_ASSUMPTIONS
    return []
