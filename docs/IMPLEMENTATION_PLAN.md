# Implementation Plan — Talend-to-Snowflake Migration Demo

## What the Demo Proves

Devin can parse a portfolio of Talend ETL job definitions (XML `.item` files), build a complete job inventory with dependency graphs and complexity classifications, and convert Talend jobs to Python modules using Snowpark for Snowflake operations — end-to-end, inside a single live Devin session.

## What Devin Does Live

Devin runs discovery scripts against the Talend XML files, builds the dependency graph, classifies jobs by complexity, populates the interactive dashboard, then converts jobs to Python/Snowpark using component-level translation rules.

## Stack and Rationale

| Component | Choice | Source/Rationale |
|---|---|---|
| Talend .item XML format | `talendfile:ProcessType` EMF-based XML with `node`, `connection`, `metadata`, `context` elements | Confirmed from real `.item` files in public Talend repos on GitHub (walid0912/Talend_Mission, hams71/ETL-ELT-Talend, sarradoghri/DW) |
| XML namespace | `xmlns:talendfile="platform:/resource/org.talend.model/model/TalendFile.xsd"` | Real Talend EMF model namespace from source examples |
| tMap nodeData | `xsi:type="TalendMapper:MapperData"` with `inputTables`, `outputTables`, `mapperTableEntries` | Confirmed from real `.item` files with tMap components |
| Component names | `tMysqlInput` (renders as tDBInput), `tMSSqlOutput` (renders as tDBOutput), `tMap`, `tLogRow`, `tFilterColumns`, `tFileInputDelimited`, `tFileOutputDelimited` | Real Talend component registry names |
| Python analysis | `lxml` for XML parsing, `json` for manifest output | Standard Python XML processing |
| Dashboard | Static HTML + vanilla JS + Chart.js CDN | No build step required, matches demo repo conventions |
| Snowpark stubs | `snowflake-snowpark-python` type stubs only | No live Snowflake connection needed for demo |

## Repo Layout

```
talend-snowflake-demo/
├── talend_jobs/
│   ├── customer_accounts/
│   │   ├── customer_extract_0.1.item          # tDBInput → tMap → tDBOutput
│   │   ├── customer_validation_0.1.item       # tDBInput → tMap → tDBOutput + tLogRow
│   │   └── customer_dimension_load_0.1.item   # tDBInput → tMap → tDBOutput (SCD Type 2)
│   ├── loan_processing/
│   │   ├── loan_application_ingest_0.1.item   # tFileInputDelimited → tMap → tDBOutput
│   │   ├── loan_risk_scoring_0.1.item         # tDBInput → tMap (complex) → tDBOutput
│   │   └── loan_status_update_0.1.item        # tDBInput → tDBRow → tLogRow
│   ├── payment_reconciliation/
│   │   ├── payment_match_0.1.item             # tDBInput ×2 → tMap (join) → tDBOutput
│   │   ├── payment_discrepancy_0.1.item       # tDBInput → tMap → tFileOutputDelimited
│   │   └── payment_settlement_0.1.item        # tDBInput → tMap → tDBOutput + tDBRow
│   ├── regulatory_reporting/
│   │   ├── cfpb_extract_0.1.item              # tDBInput ×3 → tMap → tFileOutputDelimited
│   │   ├── occ_compliance_report_0.1.item     # tDBInput → tMap → tDBOutput
│   │   └── regulatory_archive_0.1.item        # tDBInput → tFileOutputDelimited
│   └── data_quality/
│       ├── address_standardization_0.1.item   # tFileInputDelimited → tMap → tDBOutput
│       └── dedup_customer_0.1.item            # tDBInput → tMap (complex) → tDBOutput + tLogRow
├── routines/
│   ├── DateFormatUtils.java                   # Date formatting helpers
│   ├── AmountUtils.java                       # Currency rounding, amount validation
│   └── AccountValidator.java                  # Account number validation (Luhn, format)
├── python_target/                             # Empty — Devin populates during live demo
│   └── .gitkeep
├── scripts/
│   ├── parse_talend_xml.py                    # Parse .item files, extract component graphs
│   ├── build_dependency_graph.py              # Build job dependency map
│   ├── classify_complexity.py                 # Classify jobs by conversion difficulty
│   └── generate_manifest.py                   # Generate migration manifest JSON
├── dashboard/
│   ├── index.html                             # Interactive discovery dashboard
│   ├── dashboard.js                           # Dashboard logic and chart rendering
│   └── dashboard.css                          # Dashboard styling
├── docs/
│   ├── IMPLEMENTATION_PLAN.md                 # This file
│   ├── flowchart.html                         # Standalone HTML flowchart
│   └── flowchart.png                          # Rasterized flowchart
├── conversion-playbook.md                     # Component-level translation rules
├── DEMO_NOTES.md                              # Presenter cheat sheet
├── README.md                                  # Project overview
├── requirements.txt                           # Python dependencies
└── .github/workflows/ci.yml                   # Simple CI
```

## Flowchart Outline

1. **Talend Job Definitions** → **Prompt Devin**
2. Devin runs discovery: **Parse XML** → **Build Dependency Graph** → **Classify Complexity** → **Generate Manifest**
3. **Populate Dashboard** → **Presenter Opens Dashboard**
4. Devin runs conversion: **Apply Translation Rules** → **Rewrite tMap Expressions** → **Convert Routines** → **Generate Tests**
5. **Open PR with Converted Code**

## Runtime Plan

- Analysis scripts parse the real Talend XML files and produce JSON output
- Dashboard loads JSON data and renders charts/tables
- `python scripts/parse_talend_xml.py` → produces `analysis_output/job_inventory.json`
- `python scripts/build_dependency_graph.py` → produces `analysis_output/dependency_graph.json`
- `python scripts/classify_complexity.py` → produces `analysis_output/complexity_report.json`
- `python scripts/generate_manifest.py` → produces `analysis_output/migration_manifest.json`
- Dashboard reads from `analysis_output/` directory

## CI Plan

- Checkout, install Python deps (`lxml`), run `ruff` linter on Python files, validate XML well-formedness with `xmllint`

## Risks and Unknowns

- Talend component names in XML use vendor-specific names (e.g. `tMysqlInput` not `tDBInput`) — the display name differs from the XML `componentName`. Our demo files use generic `tDBInput`/`tDBOutput` component names which map to JDBC-based components, consistent with the platform-agnostic component variant.
- tMap `nodeData` structure varies between Talend versions — we use the v2.1 format confirmed from real examples.
- Real Talend projects include `.properties` and `.screenshot` companion files alongside `.item` files — we omit these for clarity since the XML is the source of truth for migration.
