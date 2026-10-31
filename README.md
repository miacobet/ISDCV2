# ISDC Decommissioning Cost Estimation Tool

A desktop application for preparing decommissioning cost estimates for nuclear
installations using the **International Structure for Decommissioning Costing
(ISDC) of Nuclear Installations** (NEA/OECD, IAEA, EC — 2012, NEA No. 7088).

It covers the whole estimate: the ISDC cost matrix, a graded approach by
facility type and strategy, phases, waste streams, an assumptions register,
a decommissioning fund plan, the EUR/MWh levy for power reactors, and PDF /
Excel reports.

> This tool is an engineering aid. The applicability defaults, assumption
> items and reference values are generic. Users are responsible for checking
> all inputs, assumptions and results against the ISDC publication and their
> own national requirements.

## Features

- **ISDC 2012 cost structure** — the full hierarchy of Appendix A:
  11 Principal Activities, 65 Activity Groups and 260 Typical Activities, with
  the four ISDC cost categories (labour, investment, expenses, contingency).
  Costs can be entered per Typical Activity or as a lump sum per Activity Group.
  11.04 *Asset recovery* accepts negative amounts (income).
- **Graded approach** — every item is rated Mandatory / Dominant / Applicable /
  Conditional / Not applicable for the facility type (power reactors, research
  reactors, fuel fabrication, enrichment, reprocessing, waste and spent fuel
  storage, disposal) and the strategy (DECON, SAFSTOR, entombment). Any rating
  can be changed per project with a mandatory justification. Items that need
  attention (e.g. a dominant cost driver with no cost, or costs on a
  not-applicable item) are flagged in the matrix and in the reports.
- **Contingency check** — contingency is a cost category; the tool reports it
  as a share of the base cost and warns when none is entered.
- **Funding plan** — how much must be paid into the decommissioning fund
  (monthly, quarterly or yearly, level or increasing payments) so the fund can
  pay every cost when it falls due. Uses the phase cost profile, cost
  escalation and fund return, with a year-by-year schedule, chart and
  sensitivity cases.
- **EUR/MWh levy** (power reactors) — the levy per MWh that pays the funding
  plan, year by year and as a constant rate, and a check of the national
  tariff (sufficient / shortfall).
- **Assumptions register** — checklist condensed from ISDC Appendix B topics,
  plus facility-specific items (CANDU, fuel fabrication, enrichment,
  reprocessing, spent fuel and waste storage).
- **Reports** — full report and funding plan note (PDF), full workbook (Excel)
  with matrix, applicability, phases, waste, assumptions and funding plan.

## Installation

Requires Python 3.9 or later.

### macOS / Linux

```bash
cd isdc_app
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Start the tool by double-clicking `Launch_Tool.command` (macOS) or with
`.venv/bin/python main.py`. The launcher uses the `.venv` (or `venv`) folder
automatically and shows a message if the packages are missing.

### Windows

Run `Install_Windows.cmd`. It installs the required packages and creates
`Launch_Tool.bat`.

## Data

- Projects are stored in `isdc_tool.db` (SQLite) in the folder the tool is
  started from. It is not uploaded to git.
- Databases created with earlier versions of this tool (which used a
  non-standard code list) are converted to the ISDC 2012 structure
  automatically on first start. A backup is saved as
  `isdc_tool.backup-before-ISDC2012.db`, every converted entry notes its old
  code, and the tool shows a summary.

## Methods (summary)

- **Accuracy ranges** — Order-of-magnitude −30 % / +50 %, Budgetary −15 % / +30 %,
  Definitive −5 % / +15 % (ISDC Section 2.2).
- **NPV** — phase costs discounted from the phase midpoint to the base year at
  the project discount rate.
- **Funding plan** — costs (base-year prices) are spread over the phase years,
  escalated to the year they are spent and paid monthly from the fund; the
  fund earns the stated return (compounded monthly); contributions are paid
  at the end of each period until the shutdown year. The required payment is
  the smallest one that keeps the fund balance ≥ 0 at every month-end
  (solved exactly — the balance is linear in the payment).
- **Levy** — funding-plan contributions divided by the annual energy
  production, assuming that energy is generated in every contribution year.

All rates (discount, inflation/escalation, fund return, tariffs) are user
inputs. National legislation decides which values are acceptable.

## Tests

```bash
.venv/bin/python -m unittest discover -s tests -v
```

The suite covers the database and migration, calculations, funding plan and
levy, graded approach, exports, and a headless GUI check.

## Project layout

```
main.py                 application entry point and stylesheet
core/isdc_data.py       ISDC 2012 hierarchy (Appendix A) and code helpers
core/facility_profiles.py  facility types, applicability defaults, assumptions
core/applicability.py   graded-approach review and contingency check
core/calculator.py      totals, accuracy bounds, phase NPV
core/funding_plan.py    funding plan and EUR/MWh levy
core/database.py        SQLite storage
core/migration.py       conversion of older databases to ISDC 2012 codes
gui/                    PyQt5 user interface
export/                 PDF (reportlab) and Excel (openpyxl) reports
tests/                  automated tests
```

## Reference

NEA/OECD, IAEA, EC (2012), *International Structure for Decommissioning
Costing (ISDC) of Nuclear Installations*, NEA No. 7088, OECD Publishing,
Paris. Appendix A (cost item hierarchy), Appendix B (assumptions and boundary
conditions), Appendix C (quality assurance and contingency) and Appendix D
(definitions of cost items) are the primary references for using this tool.
