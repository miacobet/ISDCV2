"""
core/isdc_data.py
==================
Seed data for the ISDC (International Structure for Decommissioning
Costing, NEA/OECD 2012, NEA No. 7088) three-level cost-code hierarchy.

This is a working engineering breakdown following the general ISDC
structure (11 Principal Activities, each with Level-2 activity groups
and Level-3 typical activities). It is provided as a practical starting
structure for cost estimation in this tool; users should verify code
titles and scope against their own copy of the ISDC publication and
adjust as needed for their project.

Structure: PA_CODE -> {"title": str, "groups": {L2_CODE: (title, [(L3_CODE, title), ...])}}
"""

ISDC_HIERARCHY = {
    "01": {
        "title": "Pre-decommissioning actions",
        "groups": {
            "01.01": ("Decommissioning planning", [
                ("01.01.01", "Preparation of the decommissioning plan"),
                ("01.01.02", "Preparation of the cost estimate"),
                ("01.01.03", "Decommissioning strategy studies and option studies"),
            ]),
            "01.02": ("Facility and site characterisation", [
                ("01.02.01", "Radiological characterisation surveys"),
                ("01.02.02", "Physical/structural condition surveys"),
                ("01.02.03", "Hazardous (non-radiological) material surveys"),
            ]),
            "01.03": ("Authorisations, licensing and administrative actions", [
                ("01.03.01", "Preparation of licensing/authorisation documentation"),
                ("01.03.02", "Regulatory review support and responses to requests"),
                ("01.03.03", "Administrative and legal actions related to licence termination"),
            ]),
        },
    },
    "02": {
        "title": "Facility shutdown activities",
        "groups": {
            "02.01": ("Final operational shutdown", [
                ("02.01.01", "Final core/fuel discharge and removal from reactor/process"),
                ("02.01.02", "System draining, deinventory and lay-up"),
                ("02.01.03", "Final operational radiological survey"),
            ]),
            "02.02": ("Deactivation", [
                ("02.02.01", "Process/system deactivation and isolation"),
                ("02.02.02", "Removal of operational fluids and process chemicals"),
                ("02.02.03", "Deactivation of non-essential support systems"),
            ]),
            "02.03": ("Transition to decommissioning configuration", [
                ("02.03.01", "Reconfiguration of safety and support systems for decommissioning"),
                ("02.03.02", "Establishment of decommissioning radiological control areas"),
                ("02.03.03", "Decommissioning-phase staffing and organisation transition"),
            ]),
        },
    },
    "03": {
        "title": "Dismantling activities within the controlled area",
        "groups": {
            "03.01": ("Decontamination", [
                ("03.01.01", "Chemical decontamination of systems and components"),
                ("03.01.02", "Mechanical/physical decontamination of surfaces"),
                ("03.01.03", "Decontamination of building structures"),
            ]),
            "03.02": ("Dismantling of process systems and components", [
                ("03.02.01", "Dismantling of primary system components"),
                ("03.02.02", "Dismantling of auxiliary and support system components"),
                ("03.02.03", "Segmentation and size-reduction of large components"),
            ]),
            "03.03": ("Removal of activated/contaminated structures", [
                ("03.03.01", "Removal of biological shielding and activated concrete"),
                ("03.03.02", "Removal of activated structural components"),
                ("03.03.03", "Demolition of contaminated building structures"),
            ]),
            "03.04": ("Final radiological survey and site release", [
                ("03.04.01", "Final status survey of buildings and structures"),
                ("03.04.02", "Final status survey of land areas"),
                ("03.04.03", "Preparation of site release/clearance documentation"),
            ]),
        },
    },
    "04": {
        "title": "Waste processing, storage and disposal",
        "groups": {
            "04.01": ("Waste processing and conditioning", [
                ("04.01.01", "Waste sorting, segregation and characterisation"),
                ("04.01.02", "Waste treatment (volume reduction, decontamination)"),
                ("04.01.03", "Waste conditioning and packaging"),
            ]),
            "04.02": ("Waste interim storage", [
                ("04.02.01", "Operation of on-site interim waste storage"),
                ("04.02.02", "Waste package inspection and maintenance during storage"),
            ]),
            "04.03": ("Waste transport and disposal", [
                ("04.03.01", "Transport of waste to storage/disposal facilities"),
                ("04.03.02", "Disposal fees and disposal facility charges"),
                ("04.03.03", "Clearance/exemption of material from regulatory control"),
            ]),
        },
    },
    "05": {
        "title": "Site infrastructure and operation",
        "groups": {
            "05.01": ("Site services during decommissioning", [
                ("05.01.01", "Electrical power supply and distribution"),
                ("05.01.02", "HVAC and ventilation systems operation"),
                ("05.01.03", "Water, sanitary and other utilities"),
            ]),
            "05.02": ("Maintenance of facility and site infrastructure", [
                ("05.02.01", "Maintenance of buildings and structures retained in service"),
                ("05.02.02", "Maintenance of safety-related support systems"),
            ]),
            "05.03": ("Conservation/safe-storage period operation", [
                ("05.03.01", "Surveillance and monitoring during conservation period"),
                ("05.03.02", "Minimum-service system operation during conservation period"),
                ("05.03.03", "Periodic inspections and condition assessments"),
            ]),
        },
    },
    "06": {
        "title": "Project management, engineering and site support",
        "groups": {
            "06.01": ("Project management", [
                ("06.01.01", "Project management team and administration"),
                ("06.01.02", "Project controls (cost, schedule, risk)"),
                ("06.01.03", "Quality assurance and quality control"),
            ]),
            "06.02": ("Engineering support", [
                ("06.02.01", "Engineering design and work-package preparation"),
                ("06.02.02", "Configuration management and documentation control"),
            ]),
            "06.03": ("Site support services", [
                ("06.03.01", "Security and access control"),
                ("06.03.02", "Fire protection services"),
                ("06.03.03", "Radiation protection and health physics support"),
                ("06.03.04", "Training of decommissioning personnel"),
            ]),
        },
    },
    "07": {
        "title": "Research and development",
        "groups": {
            "07.01": ("Technology development", [
                ("07.01.01", "Development of dismantling/decontamination technologies"),
                ("07.01.02", "Qualification and testing of novel techniques or tooling"),
            ]),
            "07.02": ("Demonstration programmes", [
                ("07.02.01", "Mock-up trials and demonstration activities"),
            ]),
        },
    },
    "08": {
        "title": "Fuel and nuclear material",
        "groups": {
            "08.01": ("Nuclear fuel management", [
                ("08.01.01", "Spent fuel handling and inventory management"),
                ("08.01.02", "Spent fuel transport"),
                ("08.01.03", "Spent fuel storage/disposition"),
            ]),
            "08.02": ("Special nuclear material", [
                ("08.02.01", "Special nuclear material inventory reconciliation"),
                ("08.02.02", "Special nuclear material disposition/transfer"),
            ]),
            "08.03": ("Safeguards and material accountancy", [
                ("08.03.01", "Safeguards termination activities"),
            ]),
        },
    },
    "09": {
        "title": "Miscellaneous expenditures",
        "groups": {
            "09.01": ("Taxes, fees and insurance", [
                ("09.01.01", "Taxes and statutory fees related to decommissioning"),
                ("09.01.02", "Insurance during decommissioning"),
            ]),
            "09.02": ("Other costs", [
                ("09.02.01", "Legacy liabilities not elsewhere classified"),
                ("09.02.02", "Other miscellaneous decommissioning expenditures"),
            ]),
        },
    },
    "10": {
        "title": "Income",
        "groups": {
            "10.01": ("Sale of recovered materials", [
                ("10.01.01", "Sale of recovered metals and materials"),
                ("10.01.02", "Sale of recovered equipment"),
            ]),
            "10.02": ("Other income", [
                ("10.02.01", "Income from site/asset disposal or re-use"),
            ]),
        },
    },
    "11": {
        "title": "Unplanned costs (contingency)",
        "groups": {
            "11.01": ("Project contingency", [
                ("11.01.01", "Contingency for identified project risks"),
            ]),
            "11.02": ("Unforeseen events", [
                ("11.02.01", "Allowance for unforeseen/unplanned events"),
            ]),
        },
    },
}
