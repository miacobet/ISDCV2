"""
core/isdc_data.py
==================
ISDC cost item hierarchy, as published in the NEA/OECD "International
Structure for Decommissioning Costing (ISDC) of Nuclear Installations"
(NEA No. 7088, 2012), Appendix A: 11 Principal Activities (Level 1),
Activity Groups (Level 2) and Typical Activities (Level 3).

Codes follow the ISDC numbering: "01" = Principal Activity, "01.0100" =
Activity Group, "01.0101" = Typical Activity. Titles are taken from
Appendix A of the publication.

Cost categories (labour, investment, expenses, contingency) are applied
to every activity; contingency is a cost category, not a Principal
Activity.

Structure: PA_CODE -> {"title": str, "groups": {GROUP_CODE: (title, [(CODE, title), ...])}}
"""

ISDC_VERSION = "ISDC 2012 (NEA No. 7088)"

# Codes whose amounts are income (Asset recovery) and may be entered as negative values.
INCOME_PREFIXES = ("11.04",)

ISDC_HIERARCHY = {
    "01": {
        "title": "Pre-decommissioning actions",
        "groups": {
            "01.0100": ("Decommissioning planning", [
                ("01.0101", "Strategic planning"),
                ("01.0102", "Preliminary planning"),
                ("01.0103", "Final planning"),
            ]),
            "01.0200": ("Facility characterisation", [
                ("01.0201", "Detailed facility characterisation"),
                ("01.0202", "Hazardous-material surveys and analyses"),
                ("01.0203", "Establishing a facility inventory database"),
            ]),
            "01.0300": ("Safety, security and environmental studies", [
                ("01.0301", "Decommissioning safety analysis"),
                ("01.0302", "Environmental impact assessment"),
                ("01.0303", "Safety, security and emergency planning for site operations"),
            ]),
            "01.0400": ("Waste management planning", [
                ("01.0401", "Establish waste management criteria"),
                ("01.0402", "Develop a waste management plan"),
            ]),
            "01.0500": ("Authorisation", [
                ("01.0501", "License applications and license approvals"),
                ("01.0502", "Stakeholder involvement"),
            ]),
            "01.0600": ("Preparing management group and contracting", [
                ("01.0601", "Management team activities"),
                ("01.0602", "Contracting activities"),
            ]),
        },
    },
    "02": {
        "title": "Facility shutdown activities",
        "groups": {
            "02.0100": ("Plant shutdown and inspection", [
                ("02.0101", "Termination of operation, plant stabilisation, isolation and inspection"),
                ("02.0102", "Defueling and transfer of fuel to spent-fuel storage"),
                ("02.0103", "Cooling down of spent fuel"),
                ("02.0104", "Management of fuel, fissile and other nuclear materials"),
                ("02.0105", "Isolation of power equipment"),
                ("02.0106", "Facility reuse"),
            ]),
            "02.0200": ("Drainage and drying of systems", [
                ("02.0201", "Drainage and drying of closed systems not in operation"),
                ("02.0202", "Drainage of spent-fuel pool and other open systems not in operation"),
                ("02.0203", "Removal of sludge and products from open systems"),
                ("02.0204", "Drainage of special process fluids"),
            ]),
            "02.0300": ("Decontamination of closed systems for dose reduction", [
                ("02.0301", "Decontamination of process installations using operational procedures"),
                ("02.0302", "Decontamination of process installations using additional procedures"),
            ]),
            "02.0400": ("Radiological inventory characterisation to support detailed planning", [
                ("02.0401", "Radiological inventory characterisation"),
                ("02.0402", "Underground water monitoring"),
            ]),
            "02.0500": ("Removal of system fluids, operational waste and redundant material", [
                ("02.0501", "Removal of combustible material"),
                ("02.0502", "Removal of system fluids (water, oils, etc.)"),
                ("02.0503", "Removal of special system fluids"),
                ("02.0504", "Removal of waste from decontamination"),
                ("02.0505", "Removal of spent resins"),
                ("02.0506", "Removal of specific operational waste from fuel cycle facilities"),
                ("02.0507", "Removal of other waste from facility operations"),
                ("02.0508", "Removal of redundant equipment and materials"),
            ]),
        },
    },
    "03": {
        "title": "Additional activities for safe enclosure or entombment",
        "groups": {
            "03.0100": ("Preparation for safe enclosure", [
                ("03.0101", "Decontamination of selected components and areas to facilitate safe enclosure"),
                ("03.0102", "Zoning for long-term storage"),
                ("03.0103", "Removal of inventory not suitable for safe enclosure"),
                ("03.0104", "Dismantling and transfer of contaminated equipment and material to containment structure for long-term storage"),
                ("03.0105", "Radiological inventory characterisation for safe enclosure"),
            ]),
            "03.0200": ("Site boundary reconfiguration, isolating and securing structures", [
                ("03.0201", "Modification of auxiliary systems"),
                ("03.0202", "Site boundary reconfiguration"),
                ("03.0203", "Construction of temporary enclosures, stores, structural enhancements, etc"),
                ("03.0204", "Stabilisation of radioactive and hazardous waste pending remediation"),
                ("03.0205", "Facility controlled area hardening, isolation for safe enclosure"),
            ]),
            "03.0300": ("Facility entombment", [
                ("03.0301", "Facility entombment as end state of decommissioning strategy"),
                ("03.0302", "Institutional control and monitoring of the entombment end state"),
            ]),
        },
    },
    "04": {
        "title": "Dismantling activities within the controlled area",
        "groups": {
            "04.0100": ("Procurement of equipment for decontamination and dismantling", [
                ("04.0101", "Procurement of general site-dismantling equipment"),
                ("04.0102", "Procurement of equipment for decontamination of personnel and tools"),
                ("04.0103", "Procurement of special tools for dismantling the reactor systems"),
                ("04.0104", "Procurement of special tools for dismantling in fuel cycle facilities"),
                ("04.0105", "Procurement of special tools for dismantling other components or structures"),
            ]),
            "04.0200": ("Preparations and support for dismantling", [
                ("04.0201", "Reconfiguration of existing services, facilities and site to support dismantling"),
                ("04.0202", "Preparation of infrastructure and logistics for dismantling"),
                ("04.0203", "Ongoing radiological characterisation during dismantling"),
            ]),
            "04.0300": ("Pre-dismantling decontamination", [
                ("04.0301", "Drainage of remaining systems"),
                ("04.0302", "Removal of sludge and products from remaining systems"),
                ("04.0303", "Decontamination of remaining systems"),
                ("04.0304", "Decontamination of areas in buildings"),
            ]),
            "04.0400": ("Removal of materials requiring specific procedures", [
                ("04.0401", "Removal of thermal insulation"),
                ("04.0402", "Removal of asbestos"),
                ("04.0403", "Removal of other hazardous materials"),
            ]),
            "04.0500": ("Dismantling of main process systems, structures and components", [
                ("04.0501", "Dismantling of reactor internals"),
                ("04.0502", "Dismantling of reactor vessel and core components"),
                ("04.0503", "Dismantling of other primary loop components"),
                ("04.0504", "Dismantling of main process systems in fuel cycle facilities"),
                ("04.0505", "Dismantling of main process systems in other nuclear facilities"),
                ("04.0506", "Dismantling of external thermal/biological shields"),
            ]),
            "04.0600": ("Dismantling of other systems and components", [
                ("04.0601", "Dismantling of auxiliary systems"),
                ("04.0602", "Dismantling of remaining components"),
            ]),
            "04.0700": ("Removal of contamination from building structures", [
                ("04.0701", "Removal of embedded elements in buildings"),
                ("04.0702", "Removal of contaminated structures"),
                ("04.0703", "Decontamination of buildings"),
            ]),
            "04.0800": ("Removal of contamination from areas outside buildings", [
                ("04.0801", "Removal of underground contaminated pipes and structures"),
                ("04.0802", "Removal of contaminated soil and other contaminated items"),
            ]),
            "04.0900": ("Final radioactivity survey for release of buildings", [
                ("04.0901", "Final radioactivity survey of buildings"),
                ("04.0902", "Declassification of buildings"),
            ]),
        },
    },
    "05": {
        "title": "Waste processing, storage and disposal",
        "groups": {
            "05.0100": ("Waste management system", [
                ("05.0101", "Establishing the waste management system"),
                ("05.0102", "Reconstruction of existing facilities for decommissioning waste management system"),
                ("05.0103", "Procurement of additional equipment for management of historical/legacy waste"),
                ("05.0104", "Maintenance, surveillance and operational support for waste management system"),
                ("05.0105", "Demobilisation/decommissioning of waste management system"),
            ]),
            "05.0200": ("Management of historical/legacy high-level waste", [
                ("05.0201", "Characterisation"),
                ("05.0202", "Retrieval and processing"),
                ("05.0203", "Final conditioning"),
                ("05.0204", "Storage"),
                ("05.0205", "Transport"),
                ("05.0206", "Disposal"),
                ("05.0207", "Containers"),
            ]),
            "05.0300": ("Management of historical/legacy intermediate-level waste", [
                ("05.0301", "Characterisation"),
                ("05.0302", "Retrieval and processing"),
                ("05.0303", "Final conditioning"),
                ("05.0304", "Storage"),
                ("05.0305", "Transport"),
                ("05.0306", "Disposal"),
                ("05.0307", "Containers"),
            ]),
            "05.0400": ("Management of historical/legacy low-level waste", [
                ("05.0401", "Characterisation"),
                ("05.0402", "Retrieval and treatment"),
                ("05.0403", "Final conditioning"),
                ("05.0404", "Storage"),
                ("05.0405", "Transport"),
                ("05.0406", "Disposal"),
                ("05.0407", "Containers"),
            ]),
            "05.0500": ("Management of historical/legacy very low-level waste", [
                ("05.0501", "Characterisation"),
                ("05.0502", "Retrieval, treatment and packaging"),
                ("05.0503", "Transport"),
                ("05.0504", "Disposal"),
            ]),
            "05.0600": ("Management of historical/legacy exempt waste and materials", [
                ("05.0601", "Retrieval, treatment and packaging"),
                ("05.0602", "Clearance measurement of exempt waste and materials"),
                ("05.0603", "Transport of hazardous waste"),
                ("05.0604", "Disposal of hazardous waste at dedicated waste dumps"),
                ("05.0605", "Transport of conventional waste and materials"),
                ("05.0606", "Disposal of conventional waste at conventional waste dumps"),
            ]),
            "05.0700": ("Management of decommissioning high-level waste", [
                ("05.0701", "Characterisation"),
                ("05.0702", "Processing"),
                ("05.0703", "Final conditioning"),
                ("05.0704", "Storage"),
                ("05.0705", "Transport"),
                ("05.0706", "Disposal"),
                ("05.0707", "Containers"),
            ]),
            "05.0800": ("Management of decommissioning intermediate-level waste", [
                ("05.0801", "Characterisation"),
                ("05.0802", "Processing"),
                ("05.0803", "Final conditioning"),
                ("05.0804", "Storage"),
                ("05.0805", "Transport"),
                ("05.0806", "Disposal"),
                ("05.0807", "Containers"),
            ]),
            "05.0900": ("Management of decommissioning low-level waste", [
                ("05.0901", "Characterisation"),
                ("05.0902", "Processing"),
                ("05.0903", "Final conditioning"),
                ("05.0904", "Storage"),
                ("05.0905", "Transport"),
                ("05.0906", "Disposal"),
                ("05.0907", "Containers"),
            ]),
            "05.1000": ("Management of decommissioning very low-level waste", [
                ("05.1001", "Characterisation"),
                ("05.1002", "Treatment and packaging"),
                ("05.1003", "Transport"),
                ("05.1004", "Disposal"),
            ]),
            "05.1100": ("Management of decommissioning very short-lived waste", [
                ("05.1101", "Characterisation"),
                ("05.1102", "Treatment, storage, handling and packaging"),
                ("05.1103", "Final management of decommissioning very short-lived waste"),
            ]),
            "05.1200": ("Management of decommissioning exempt waste and materials", [
                ("05.1201", "Treatment and packaging"),
                ("05.1202", "Clearance measurement of exempt waste and materials"),
                ("05.1203", "Transport of hazardous waste"),
                ("05.1204", "Disposal of hazardous waste at dedicated waste dumps"),
                ("05.1205", "Transport of conventional waste and materials"),
                ("05.1206", "Disposal of conventional waste at conventional waste dumps"),
            ]),
            "05.1300": ("Management of decommissioning waste and materials generated outside controlled areas", [
                ("05.1301", "Recycling of concrete"),
                ("05.1302", "Treatment and packaging of hazardous waste"),
                ("05.1303", "Treatment and recycling of other materials"),
                ("05.1304", "Transport of hazardous waste"),
                ("05.1305", "Disposal of hazardous waste at dedicated waste dumps"),
                ("05.1306", "Transport of conventional waste and materials"),
                ("05.1307", "Disposal of conventional waste at conventional waste dumps"),
            ]),
        },
    },
    "06": {
        "title": "Site infrastructure and operation",
        "groups": {
            "06.0100": ("Site security and surveillance", [
                ("06.0101", "Procurement of general security equipment"),
                ("06.0102", "Operation and maintenance of automated access control systems, monitoring systems and alarms"),
                ("06.0103", "Security fencing and protection of remaining entrances against trespassing"),
                ("06.0104", "Deployment of guards/security forces"),
            ]),
            "06.0200": ("Site operation and maintenance", [
                ("06.0201", "Inspection and maintenance of buildings and systems"),
                ("06.0202", "Site upkeep activities"),
            ]),
            "06.0300": ("Operation of support systems", [
                ("06.0301", "Electricity supply systems"),
                ("06.0302", "Ventilation systems"),
                ("06.0303", "Heating, steam and lighting systems"),
                ("06.0304", "Water supply systems"),
                ("06.0305", "Sewage/waste water systems"),
                ("06.0306", "Compressed air/nitrogen systems"),
                ("06.0307", "Other systems"),
            ]),
            "06.0400": ("Radiation and environmental safety monitoring", [
                ("06.0401", "Procurement and maintenance of equipment for radiation protection and environmental monitoring"),
                ("06.0402", "Radiation protection and monitoring"),
                ("06.0403", "Environmental protection and radiation environmental monitoring"),
            ]),
        },
    },
    "07": {
        "title": "Conventional dismantling, demolition and site restoration",
        "groups": {
            "07.0100": ("Procurement of equipment for conventional dismantling and demolition", [
                ("07.0101", "Procurement of equipment for conventional dismantling and demolition"),
            ]),
            "07.0200": ("Dismantling of systems and building components outside the controlled area", [
                ("07.0201", "Electricity generating system"),
                ("07.0202", "Cooling system components"),
                ("07.0203", "Other auxiliary systems"),
            ]),
            "07.0300": ("Demolition of buildings and structures", [
                ("07.0301", "Demolition of buildings and structures from the formerly controlled area"),
                ("07.0302", "Demolition of buildings and structures outside the controlled area"),
                ("07.0303", "Dismantling of the stack"),
            ]),
            "07.0400": ("Final cleanup, landscaping and refurbishment", [
                ("07.0401", "Earthworks, landworks"),
                ("07.0402", "Landscaping and other site finishing activities"),
                ("07.0403", "Refurbishment of buildings"),
            ]),
            "07.0500": ("Final radioactivity survey of site", [
                ("07.0501", "Final survey"),
                ("07.0502", "Independent verification of the final survey"),
            ]),
            "07.0600": ("Perpetuity funding/surveillance for limited or restricted release of property", [
                ("07.0601", "Routine maintenance"),
                ("07.0602", "Surveillance and monitoring"),
            ]),
        },
    },
    "08": {
        "title": "Project management, engineering and support",
        "groups": {
            "08.0100": ("Mobilisation and preparatory work", [
                ("08.0101", "Mobilisation of personnel"),
                ("08.0102", "Establishment of general supporting infrastructure for decommissioning project"),
            ]),
            "08.0200": ("Project management", [
                ("08.0201", "Core management group"),
                ("08.0202", "Project implementation planning, detailed ongoing planning"),
                ("08.0203", "Scheduling and cost control"),
                ("08.0204", "Safety and environmental analysis, ongoing studies"),
                ("08.0205", "Quality assurance and quality surveillance"),
                ("08.0206", "General administration and accounting"),
                ("08.0207", "Public relations and stakeholders involvement"),
            ]),
            "08.0300": ("Support services", [
                ("08.0301", "Engineering support"),
                ("08.0302", "Information system and computer support"),
                ("08.0303", "Waste management support"),
                ("08.0304", "Decommissioning support including chemistry, decontamination"),
                ("08.0305", "Personnel management and training"),
                ("08.0306", "Documentation and records control"),
                ("08.0307", "Procurement, warehousing, and materials handling"),
                ("08.0308", "Housing, office equipment, support services"),
            ]),
            "08.0400": ("Health and safety", [
                ("08.0401", "Health physics"),
                ("08.0402", "Industrial safety"),
            ]),
            "08.0500": ("Demobilisation", [
                ("08.0501", "Demobilisation of project infrastructure for decommissioning"),
                ("08.0502", "Demobilisation of personnel"),
            ]),
            "08.0600": ("Mobilisation and preparatory work by contractors (if needed)", [
                ("08.0601", "Mobilisation of personnel"),
                ("08.0602", "Establishment of general supporting infrastructure for decommissioning project"),
            ]),
            "08.0700": ("Project management by contractors (if needed)", [
                ("08.0701", "Core management group"),
                ("08.0702", "Project implementation planning, detailed ongoing planning"),
                ("08.0703", "Scheduling and cost control"),
                ("08.0704", "Safety and environmental analysis, ongoing studies"),
                ("08.0705", "Quality assurance and quality surveillance"),
                ("08.0706", "General administration and accounting"),
                ("08.0707", "Public relations and stakeholder involvement"),
            ]),
            "08.0800": ("Support services by contractors (if needed)", [
                ("08.0801", "Engineering support"),
                ("08.0802", "Information system and computer support"),
                ("08.0803", "Waste management support"),
                ("08.0804", "Decommissioning support including chemistry, decontamination"),
                ("08.0805", "Personal management and training"),
                ("08.0806", "Documentation and records control"),
                ("08.0807", "Procurement, warehousing, and materials handling"),
                ("08.0808", "Housing, office equipment, support services"),
            ]),
            "08.0900": ("Health and safety by contractors (if needed)", [
                ("08.0901", "Health physics"),
                ("08.0902", "Industrial safety"),
            ]),
            "08.1000": ("Demobilisation by contractors (if needed)", [
                ("08.1001", "Demobilisation of project infrastructure for decommissioning"),
                ("08.1002", "Demobilisation of personnel"),
            ]),
        },
    },
    "09": {
        "title": "Research and development",
        "groups": {
            "09.0100": ("Research and development of equipment, techniques and procedures", [
                ("09.0101", "Equipment, techniques and procedures for characterisation"),
                ("09.0102", "Equipment, techniques and procedures for decontamination"),
                ("09.0103", "Equipment, techniques and procedures for dismantling"),
                ("09.0104", "Equipment, techniques and procedures for waste management"),
                ("09.0105", "Other research and development activities"),
            ]),
            "09.0200": ("Simulation of complicated works", [
                ("09.0201", "Physical mock-ups and training"),
                ("09.0202", "Test or demonstration programmes"),
                ("09.0203", "Computer simulations, visualisations and 3D modelling"),
                ("09.0204", "Other activities"),
            ]),
        },
    },
    "10": {
        "title": "Fuel and nuclear material",
        "groups": {
            "10.0100": ("Removal of fuel or nuclear material from facility to be decommissioned", [
                ("10.0101", "Transfer of fuel or nuclear material to external storage or to treatment facilities"),
                ("10.0102", "Transfer of fuel or nuclear material to dedicated buffer storage"),
            ]),
            "10.0200": ("Dedicated buffer storage for fuel and/or nuclear material", [
                ("10.0201", "Construction of buffer storage"),
                ("10.0202", "Operation of buffer storage"),
                ("10.0203", "Transfer of fuel and/or nuclear material away from the buffer storage"),
            ]),
            "10.0300": ("Decommissioning of buffer storage", [
                ("10.0301", "Decommissioning of buffer storage"),
                ("10.0302", "Management of waste"),
            ]),
        },
    },
    "11": {
        "title": "Miscellaneous expenditures",
        "groups": {
            "11.0100": ("Owner costs", [
                ("11.0101", "Implementation of transition plans"),
                ("11.0102", "External projects to be performed as a consequence of decommissioning"),
                ("11.0103", "Payments (fees) to authorities"),
                ("11.0104", "Specific external services and payments"),
            ]),
            "11.0200": ("Taxes", [
                ("11.0201", "Value added taxes"),
                ("11.0202", "Local, community, federal taxes"),
                ("11.0203", "Environmental taxes"),
                ("11.0204", "Taxes on industrial activities"),
                ("11.0205", "Other taxes"),
            ]),
            "11.0300": ("Insurances", [
                ("11.0301", "Nuclear related insurances"),
                ("11.0302", "Other insurances"),
            ]),
            "11.0400": ("Asset recovery", [
                ("11.0401", "Asset recovery related to redundant equipment"),
                ("11.0402", "Asset recovery related to released materials"),
                ("11.0403", "Asset recovery related to material and equipment from conventional dismantling and demolition"),
                ("11.0404", "Asset recovery related to buildings and site"),
                ("11.0405", "Other asset recovery"),
            ]),
        },
    },
}


# ---------------------------------------------------------------------
# Code helpers
# ---------------------------------------------------------------------

def code_level(code: str) -> int:
    """1 = Principal Activity ("04"), 2 = Activity Group ("04.0500"), 3 = Typical Activity ("04.0501")."""
    if len(code) == 2:
        return 1
    return 2 if code.endswith("00") else 3


def pa_of(code: str) -> str:
    return code[:2]


def group_of(code: str) -> str:
    """Activity Group of a Level-2 or Level-3 code."""
    return code[:5] + "00"


def ancestors(code: str):
    """The code itself followed by its parents, most specific first."""
    level = code_level(code)
    if level == 1:
        return [code]
    if level == 2:
        return [code, pa_of(code)]
    return [code, group_of(code), pa_of(code)]


def is_within(code: str, parent: str) -> bool:
    """True if `code` is `parent` or lies below it in the hierarchy."""
    return parent in ancestors(code)


def is_income_code(code: str) -> bool:
    return code.startswith(INCOME_PREFIXES)

