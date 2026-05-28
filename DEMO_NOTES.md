# Demo Cheat Sheet — Talend ETL Migration

## Setup (before the call)
- [ ] Open the repo in a browser tab: https://github.com/tedfoley-cog/talend-snowflake-demo
- [ ] Have a Devin session ready on this repo

## Demo Flow
1. Show the repo — point out the 14 Talend `.item` XML files across 5 business domains (customer accounts, loan processing, payment reconciliation, regulatory reporting, data quality), the 3 custom Java routines, and the empty `python_target/` directory. "This is a real portfolio — not toy examples. These jobs do SSN validation, risk scoring, payment matching, CFPB reporting."
2. Show one `.item` file briefly — highlight the XML complexity: `tMap` expressions with nested ternaries, custom routine calls like `AmountUtils.calculateMonthlyPayment()`, multi-source joins. "A previous vendor achieved 40-50% automated conversion. Let's see what Devin does."
3. Prompt Devin: "Parse all the Talend job definitions, build a dependency graph, classify each job by migration complexity, populate the discovery dashboard, then convert the jobs to Python/Snowpark and generate unit test scaffolding."
4. While Devin works, narrate: it's parsing XML component graphs, extracting tMap expressions, identifying cross-job dependencies via shared tables, scoring complexity based on expression depth and routine usage, and writing the results as JSON that feeds the dashboard.
5. Open the dashboard — show the component distribution chart, complexity heatmap, job inventory table with effort estimates, dependency graph, and tMap expression analysis. "In 5 minutes, Devin mapped the full portfolio — what would take a team days of manual discovery."
6. Show the converted Python files in `python_target/` — point out how tMap expressions became Snowpark `F.when()` / `F.concat()`, how custom Java routines became Python functions, how `tDBRow` dynamic SQL became parameterized `session.sql()`. "Every job has a test scaffold too."
