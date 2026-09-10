# DATA ENGINEER ASSESSMENT CONFIDENTIAL UA Manufacturing L1/L2 Band Placement

## DATA ENGINEER TECHNICAL ASSESSMENT
### L1/L2 Band Placement

| Field | Value |
| :--- | :--- |
| **Company** | UA Manufacturing Digital Solutions Team |
| **Version** | V2 |
| **Time Allowed** | 48 hours |
| **Submission** | GitHub repository (link provided separately) |
| **Interview** | Full walk-through and defence required for every decision |

---

### Confidentiality & Integrity Notice
This assignment is confidential to UA Manufacturing. Do not share, distribute, or publish any part of it including on public repositories, forums, or social media.

You may use documentation, references, and AI tools you would normally use at work. The thinking, decisions, and justifications must be entirely your own. During the technical interview you will be asked to walk through and defend every part of your submission in detail.

Submissions are used solely for evaluation and will be deleted once the recruitment process concludes.

---

### How to Read This Document
Each task is labelled by band. L1 tasks are required of all candidates. L2 tasks are required of L2 candidates and optional stretch for L1 candidates. BOTH tasks are required of all but graded differently.

| Band | Who | Grading |
| :--- | :--- | :--- |
| **L1** | All candidates | Required baseline: missing this is a fail at any level |
| **L2** | L2 candidates only | Expected for senior placement; L1 candidates attempting these earn credit |
| **BOTH** | All candidates | Required of all, but depth and breadth expected differs by level |

Read the entire assignment before starting—later sections connect to earlier ones. Document every significant decision: why matters as much as what. If you run out of time, submit what you have with clear notes on what you would do next.

---

## Context: UA Manufacturing
You are joining the Data Team at UA Manufacturing, a garment and apparel company with operations across Finance, Production, Logistics, HR, and HSE. Your task in this assessment covers two independent but connected workstreams:

- **Workstream A: KPI Tracking Pipeline:** Ingest and model monthly KPI actuals from Excel files provided by the business.
- **Workstream B: ERP Order Data Pipeline:** Ingest order data from a REST API and a dirty flat financial file, and build a dimensional model for cost reporting.

Both workstreams share the same medallion architecture and data quality framework. You will design them to work together in a single Airflow DAG.

### UA KPI Framework
The business tracks performance against four strategic pillars:

| Code | Pillar | Description |
| :--- | :--- | :--- |
| **FS** | Financial Sustainability | Cost ratios, revenue, waste: owned by Finance and Production |
| **CE** | Customer Experience | Delivery, quality, NPS: owned by Logistics, QC, and Commercial |
| **OF** | Operational Fitness | Line efficiency, headcount, training: owned by Production and HR |
| **PP** | People Powered | Engagement, safety, wellness: owned by HR and HSE |

### Data Sources: Workstream A (KPI)
The business provides monthly KPI actuals in Excel. Three files are provided:
- `kpi_actual_long.csv`: Actuals in long format, one row per KPI × Sub KPI Type, with M1–M12 as separate columns.
- `kpi_actual_wide.csv`: The same underlying data in wide/pivoted format, with month headers using a different naming convention (`Jan-24`, `Feb-24`...), you must reconcile both.
- `kpi_master_dim.csv`: The KPI Master dimension defining what KPIs exist, their three-layer surrogate IDs, targets, aggregation methods, and SCD metadata.

### Data Sources: Workstream B (ERP Orders)
The ERP system exposes a REST API with two endpoints. For this assessment, use the provided mock JSON files (treat them as API responses), `mock_orders_headers.json` and `mock_orders_details.json`. In production, these would be live endpoints with authentication.

| Endpoint | URL | Treat As | Field Mapping |
| :--- | :--- | :--- | :--- |
| **Headers** | `mock_orders_headers.json` (stand-in for `https://jsonplaceholder.typicode.com/posts`) | Order Headers | `id` → `order_id`<br>`userId` → `customer_id`<br>`title` → `order_code`<br>`body` → `order_notes` |
| **Details** | `mock_orders_details.json` (stand-in for `https://jsonplaceholder.typicode.com/comments`) | Order Line Items | `id` → `line_id`<br>`postId` → `order_id` (FK)<br>`name` → `line_description`<br>`email` → `buyer_contact`<br>`body` → `line_notes` |

#### API assumptions you must design for:
- No authentication today but assume Bearer token auth will be required in production. Design for it from the start.
- Approximately 5–10% of requests return malformed JSON. Handle this gracefully: log and skip, do not crash.
- The API has no pagination today, but your code must not assume this will remain true.
- Headers endpoint returns a flat list; Details endpoint returns all line items ungrouped: you must group and join them yourself.

> **Note for candidates:** Your ingestion code should read the mock JSON files as if they came from a live API. Design your code so that switching to a real HTTP endpoint (like JSONPlaceholder or your company's ERP) requires changing only the transport layer — e.g., one config variable, dependency injection, or an abstract base class.

### Data Sources: Workstream B (Financial Flat File)
A dirty financial file is exported manually from the accounting system. It is provided in two formats: both must be handled:
- `financial_long_format.csv`: One row per order × cost category × month.
- `financial_wide_format.csv`: Same data, with dates as column headers that must be unpivoted.
- `exchange_rates_reference.csv`: Default FX rates for currency conversion to VND.

#### Known dirty data issues (there may be more: finding them is part of the assessment):
| # | Issue | Examples |
| :-: | :--- | :--- |
| **1** | OCR typos: letter O used as digit 0 | `875O.00`, `41O0.00`, `310O0.00`, `95O0.00` |
| **2** | Inconsistent casing and whitespace | `"fabric "`, `" outsource"`, `"FABRIC"`, `"TRIM"` |
| **3** | Mixed date formats in period column | `2024-01`, `2024/01`, `January 2024`, `01-2024`, `Feb 2024` |
| **4** | Customer name variants for same entity | `"sunrise apparel"`, `"Sunrise Apparel"`, `"SUNRISE APPAREL"` |
| **5** | Duplicate rows with minor differences | `ORD-005 OUTSOURCE` appears twice: different casing and amount typo |
| **6** | Orphaned order | `ORD-099` exists in financial file but has no matching order in ERP API |
| **7** | Wide format date headers must be unpivoted | `31/01/2024`, `28/02/2024` ... as column names |
| **8** | Mixed currencies | USD, EUR, VND: all amounts must be converted to VND using `exchange_rates_reference.csv` |

---

## Part 1: Grain Definition (Do This First)
This is the most important question in dimensional modelling. Answer it before writing any code. Getting the grain wrong invalidates everything built on top of it.

### TASK 1A: Define the Grain of Each Fact Table `[BOTH]`
For each workstream, identify the correct grain of the fact table. For each option below, state **Correct** or **Incorrect** and explain why in one or two sentences:

#### Workstream A: `FACT_KPI_ACTUAL`
| Grain Option | Correct/Incorrect? | Why? |
| :--- | :--- | :--- |
| One row per KPI per Year (annual rollup) | | |
| One row per KPI Name per Month | | |
| One row per Pillar per Month | | |
| One row per KPI + Sub KPI Type per Month | | |
| One row per KPI + Sub KPI Type + Department per Month | | |

#### Workstream B: `FACT_ORDER_COST`
| Grain Option | Correct/Incorrect? | Why? |
| :--- | :--- | :--- |
| One row per order | | |
| One row per order × cost category | | |
| One row per order × cost category × month | | |
| One row per customer × month | | |

> **Interview follow-up:** A new dimension 'Region' is added to both workstreams next quarter. Explain how your grain choices accommodate or break under this change.

### TASK 1B: Aggregation Logic by KPI Type `[L2]`
The `kpi_master_dim.csv` contains an `Aggregation_Method` column with values: `SUM`, `AVERAGE`, `LAST`. Answer all of the following:
1. Why must Headcount KPIs use `LAST` instead of `SUM` or `AVERAGE`? What does summing Headcount across months actually produce, and why is it wrong?
2. Why must Revenue KPIs use `SUM`? Why would `AVERAGE` be incorrect?
3. Why must Rate KPIs (OT Cost Ratio, Line Efficiency, Defect Rate) use `AVERAGE` and not `SUM`?
4. What happens to a leadership dashboard if the wrong aggregation method is applied silently?
5. Design a Python or PySpark function that reads the `Aggregation_Method` from the master dimension and applies the correct logic dynamically: no hardcoding per KPI.

---

## Part 2: Architecture Design (Before Writing Any Code)
Document your full architecture before starting implementation. This section is not optional and will be reviewed first in the interview.

### TASK 2A: Bronze / Silver / Gold Layer Design `[BOTH]`
Design the medallion architecture for both workstreams. Complete the table below for each source:

| Layer | Source | Contents | Transformations Applied | File Format | Partitioning Strategy |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Bronze** | KPI Actuals (long + wide) | | | | |
| **Bronze** | KPI Master Dim | | | | |
| **Bronze** | ERP API (orders + lines) | | | | |
| **Bronze** | Financial Flat File | | | | |
| **Silver** | KPI Actuals unified | | | | |
| **Silver** | Orders + Lines | | | | |
| **Silver** | Financial costs | | | | |
| **Gold** | KPI achievement summary | | | | |
| **Gold** | Order cost reporting | | | | |

#### Also address all of the following in your architecture document:
- Justify: why Parquet over CSV, XLSX, TXT, or JSON for intermediate layers?
- How do you handle incremental loads for each source: weekly snapshot, append, or UPSERT? Justify per source.
- When would you choose Python over PySpark for this pipeline? At what data volume or complexity threshold do you switch?
- When would you choose SQL Endpoint vs Direct Lake vs Lakehouse vs Data Warehouse in Microsoft Fabric for each layer?

### TASK 2B: Dimensional Model: KPI Workstream `[BOTH]`
Design the full dimensional model for the KPI tracking system:

| Table | Grain | Key Columns |
| :--- | :--- | :--- |
| `DIM_KPI` | One row per KPI + Sub KPI Type version | Surrogate key, natural key, pillar, sub_pillar, department, kpi_name, sub_kpi_type, unit, target, aggregation_method, SCD metadata |
| `DIM_DATE` | One row per calendar month | `date_sk`, `year`, `month`, `quarter`, `period_label` (YYYY-MM) |
| `DIM_PILLAR` | One row per pillar | `pillar_sk`, `pillar_code`, `pillar_name` |
| `DIM_DEPARTMENT` | One row per department | `dept_sk`, `dept_name`, `pillar_fk` |
| `FACT_KPI_ACTUAL` | One row per `DIM_KPI` × `DIM_DATE` | All FKs, `actual_value`, `target_value`, `unit`, `achievement_pct`, `is_missing_actual`, `ingestion_ts` |

#### Justify every design decision. Specifically address:
- Why star schema over snowflake (or justify if you chose otherwise).
- How you handle KPIs with no Sub KPI Type: empty string, `NULL`, or sentinel value?
- Whether the Yearly Target belongs in the fact or the dimension: and why.
- How `achievement_pct` is calculated correctly for % KPIs where lower is better (Defect Rate) vs higher is better (Line Efficiency) as these are not the same formula.

### TASK 2C: Dimensional Model: Order Cost Workstream `[BOTH]`
Design the dimensional model for the financial order cost data. Your schema must include:
- `dim_date`: calendar month grain
- `dim_customer`: one row per customer (natural key: normalised `customer_name`)
- `dim_season`: SS24, AW24, SS25...
- `dim_drop`: D1, D2, D3...
- `dim_fabric_type`: Cotton, Polyester, Linen, Silk, Wool
- `dim_currency`: USD, EUR, VND with conversion rates
- `fact_order_cost`: grain: order × cost category × month

For each table define: table name, grain, all columns with data types, primary key, and all foreign keys.

#### Also address:
- How do you handle `ORD-099`, which exists in the financial file but not in the ERP API? Document your explicit handling: do not silently drop or include it.
- Where does `converted_amount_vnd` live: in the fact table or calculated at Gold? Why?
- How does your `dim_customer` handle the four variants of 'Sunrise Apparel' as the same entity?

---

## Part 3: Surrogate Keys and SCD Design

### TASK 3A: Surrogate Key Design: Three-Layer ID Structure `[L2]`
The `kpi_master_dim.csv` uses a three-layer surrogate key structure: `PILLAR_ID` (`PIL-FS`), `SP_ID` (`SP-FSC`), `UA_ID` (`UA-001`). Answer all of the following:
1. Why is a three-layer surrogate key used instead of a single auto-increment integer? What does each layer provide?
2. What makes a surrogate key stable? What would make it unstable?
3. The master contains both `UA-001` and `UA-001-OLD` for the same KPI. Why does this exist and how must your pipeline handle it?
4. If the business renames a sub-pillar from 'Cost Efficiency' to 'Cost Control', how does the surrogate key structure protect downstream reports from breaking?
5. Design a SHA256 `ROW_HASH` strategy for `DIM_KPI` change detection. Which columns should be included in the hash, which excluded, and why?

### TASK 3B: SCD Type 1 vs Type 2: Decision Table `[BOTH]`
For each attribute below in `DIM_KPI`, state whether you would apply SCD Type 1 (overwrite in place) or SCD Type 2 (add new version row and expire old) and explain why:

| Attribute | SCD Type | Justification |
| :--- | :--- | :--- |
| `kpi_name` | | |
| `unit`: % changes to Number mid-year | | |
| `yearly_target`: revised in M6 | | |
| `aggregation_method` | | |
| `department`: KPI ownership moves teams | | |
| `is_active` | | |
| `pillar_id`: pillar restructure | | |

#### Critical Interview Scenario:
The unit for On Time Delivery Rate changes from % to Number (absolute shipment count) starting M7. Historical actuals M1–M6 are stored as decimal ratios (e.g., 0.94). New actuals M7–M12 are absolute counts (e.g., 12400 shipments). Describe exactly how your SCD and fact table handle this mid-year transition: what breaks, what must be recalculated, and how you prevent silent data corruption in Gold layer reports.

### TASK 3C: Implement SCD Type 1 MERGE with ROW_HASH `[L2]`
Implement a PySpark function that performs a MERGE into `DIM_KPI` Silver using `ROW_HASH`-based change detection. Requirements:
- Accept a DataFrame of incoming master records and an existing Silver Delta table as inputs.
- Compute SHA256 `ROW_HASH` over the correct columns (justify your column selection).
- Identify NEW records (insert), CHANGED records (update in place: SCD Type 1), and UNCHANGED records (skip).
- Log a summary: N inserted, N updated, N skipped.
- Handle records that exist in Silver but are absent from the incoming batch: then set `Is_Active = 'N'`, do not delete.
- Add `MERGE_TIMESTAMP` to every upserted row.
- Document any edge cases your implementation does not handle and explain the trade-offs behind those decisions.

---

## Part 4: REST API Ingestion

### TASK 4A: ERP API Ingestion Script `[BOTH]`
Write a Python script to ingest order data from the ERP API endpoints. For this assessment, use the provided mock JSON files below (treat them as API responses). In production, these would be live endpoints with authentication.

#### Mock API Responses
Create two JSON files in your `data/raw/` folder. Your ingestion script should read these files as if they came from a REST API (use `requests.get()` against local file paths or `json.load()` — either is acceptable, but design your code so switching to a real HTTP endpoint requires minimal changes).
- `mock_orders_headers.json` (treat as `GET /orders/headers`)
- `mock_orders_details.json` (treat as `GET /orders/lines`)

#### Field Mapping
Treat the mock data with the following mapping:

| Source | Treat As | Field Mapping |
| :--- | :--- | :--- |
| `mock_orders_headers.json` | Order Headers | `id` → `order_id`<br>`userId` → `customer_id`<br>`title` → `order_code`<br>`body` → `order_notes` |
| `mock_orders_details.json` | Order Line Items | `id` → `line_id`<br>`postId` → `order_id` (FK)<br>`name` → `line_description`<br>`email` → `buyer_contact`<br>`body` → `line_notes` |

#### Requirements
Your script must:
- Call both endpoints (read both JSON files) and retrieve all records.
- Join headers and details: one order record linked to its associated line items.
- Handle errors: connection timeout, empty response, HTTP 4xx, HTTP 5xx (simulate by corrupting one file temporarily).
- Save raw response to Bronze layer as JSON with `ingestion_timestamp` added to each record.
- Log each step clearly: what was called, how many records returned, any errors.
- Design for authentication: the API has no auth today but will require Bearer token in production. Structure your code so adding auth requires changing only one place (e.g., a config variable or function decorator).

#### L2 requirement: In addition to the above:
- Handle malformed JSON gracefully: log the failure with the raw response, skip the record, continue processing.
- Implement exponential backoff retry logic: for transient failures (connection errors, 5xx).
- Handle HTTP 4xx and 5xx differently: 4xx should not retry, 5xx should retry.
- Design the authentication layer: as stated above (Bearer token ready).
- Handle pagination: assume the API may return a `next_page` cursor in future. Write code that handles both paginated and non-paginated responses without breaking.

#### Testing Your Error Handling
To verify your code handles failures correctly:
- Temporarily corrupt `mock_orders_details.json` (add an extra comma or missing quote).
- Run your pipeline, it should log the error and skip the corrupted record(s).
- Fix the file, pipeline should recover on next run.
- Do not commit the corrupted file to GitHub. Document in your README that you tested this.

### TASK 4B: The ERP Has No API: Scenario Question `[BOTH]`
Answer the following in your `README.md`. This is not a coding task: it tests how you think through a real-world constraint:

#### Scenario:
> The ERP system at UA has no API at all for a specific dataset you need. The data only exists inside a web application: there is no export button, no database access, and the vendor has confirmed they will not build an API. You need this data in your pipeline every week.

#### Answer all of the following:
1. What are your options for getting this data into the pipeline? List every realistic approach.
2. For each option: what are the technical risks, the business risks, and the maintenance cost?
3. Which option would you recommend and why? What conditions would change your recommendation?
4. What conversation would you have with the business before starting implementation? Who needs to be in the room?
5. If the vendor eventually builds an API six months later: how do you migrate from your interim solution cleanly?

> **L2 additions:** One option is web scraping. Walk through the full technical implementation approach: how would you build a scraper that is resilient to minor HTML changes in the web app? What signals would you monitor to detect breakage before the pipeline silently produces wrong data?

---

## Part 5: Silver Transformation

### TASK 5A: KPI Actuals: Bronze to Silver `[BOTH]`
Implement the Bronze → Silver transformation for KPI actuals. Your script must:
- Ingest both `kpi_actual_long.csv` and `kpi_actual_wide.csv`.
- Fix OCR typos (letter O as digit 0): log every fix with the original value, corrected value, and row identifier.
- Normalise whitespace and casing on all categorical fields: log every change.
- Detect and remove duplicate rows: log count and which rows were dropped and why.
- Unpivot wide format (`Jan-24` ... `Dec-24`) into a unified `PERIOD` column in `YYYY-MM` format.
- Unpivot long format `M1`–`M12` into the same `PERIOD` structure.
- Reconcile both formats into a single unified schema: document how you handle discrepancies between them.
- Match each record to `UA_ID` in `kpi_master_dim.csv` via composite natural key: `Pillar + Sub_Pillar + Department + KPI_Name + Sub_KPI_Type`.
- Flag records that do not match any active master record as `ORPHANED`: do not drop them.
- Add: `ROW_HASH` (SHA256), `INGESTION_TS`, `SOURCE_FILE`, `IS_DUPLICATE`, `IS_ORPHANED`.

> **L2 requirements:** Implement in PySpark with correct Delta table output and partitioning. L1 candidates may use pandas but must annotate where PySpark would be needed at scale.

### TASK 5B: Financial File: Bronze to Silver `[BOTH]`
Implement the Bronze → Silver transformation for the financial flat file. Your script must:
- Ingest both `financial_long_format.csv` and `financial_wide_format.csv`.
- Fix all known dirty data issues: and find any additional ones not listed in the Known Issues table.
- Standardise the period column: handle all five date formats and output `YYYY-MM`.
- Normalise `customer_name` to a canonical form (e.g., 'Sunrise Apparel') and document your normalisation logic.
- Unpivot wide format date columns to long format.
- Convert all amounts to VND using `exchange_rates_reference.csv`: log any records where conversion fails or rate is missing.
- Explicitly handle `ORD-099`: then flag it, do not drop it, document what a downstream consumer should do with it.
- Deduplicate: pay attention to `ORD-005 OUTSOURCE` which appears twice with slightly different values.

> **Going further (optional):** Implement a live FX rate lookup instead of the static reference file. Document the risks of hardcoded rates in a production financial pipeline.

### TASK 5C: Handle Mixed Units `[BOTH]`
The KPI fact table contains both % and Number KPIs in the same `actual_value` column. Answer all of the following:
1. What data type should `actual_value` use? Justify your choice: consider `DECIMAL(18,4)` vs `FLOAT` vs `STRING` and the implications of each.
2. How do you prevent accidental SUM aggregation across mixed-unit KPIs in a connected BI tool?
3. Should you store % KPIs as 0.85 or 85? What is the risk of each representation and which is your standard?
4. Design the `achievement_pct` calculation for:
   - (a) a % KPI where lower is better (OT Cost Ratio, target 0.12)
   - (b) a % KPI where higher is better (Line Efficiency, target 0.85)
   - (c) a Number KPI with SUM aggregation (FOB Revenue)
   - (d) a Number KPI where the target is zero (Lost Time Injuries)  
   *Show your formula for each.*

---

## Part 6: Schema Evolution and Flexibility

### TASK 6A: Business Changes: Model Survival Test `[BOTH]`
The business makes the following changes. For each, explain how your pipeline and data model accommodates or breaks, and what you would need to change:

| # | Business Change | How does your model handle it? |
| :-: | :--- | :--- |
| **1** | A brand new KPI 'Sustainability Score' is added under a new Sub Pillar 'ESG' | |
| **2** | On Time Delivery Rate changes unit from % to Number (absolute shipment count) | |
| **3** | Line Efficiency for Line D is added starting M7 only: M1–M6 are blank by design | |
| **4** | The 'Cost Efficiency' Sub Pillar is renamed 'Cost Control' | |
| **5** | OT Cost Ratio Yearly Target changes from 0.12 to 0.10 starting M6: mid-year revision | |
| **6** | FOB Revenue must now be tracked at department level: a new grain dimension | |
| **7** | Finance adds three new cost categories to the financial file next export | |
| **8** | Two KPIs are retired: actuals stop appearing from M9 onwards | |

---

## Part 7: Data Quality Framework

### TASK 7A: Required Quality Checks `[L1]`
Implement the following data quality checks on Silver outputs for both workstreams:
- Silver output is not empty (`row count > 0`).
- All mandatory columns are present and not fully null:
  - For KPI Silver: `UA_ID`, `PERIOD`, `actual_value`, `unit`
  - For Financial Silver: `order_no`, `category`, `period`, `converted_amount_vnd`
- Orphaned records are present and flagged: `IS_ORPHANED = True`, not silently dropped or included in aggregations.
- No duplicate rows remain after deduplication.
- No OCR typos remain in numeric columns, then validate that `actual_value` and amount columns parse as numeric.
- Log all results: `PASSED` / `WARNING` / `FAILED` per check.

### TASK 7B: Advanced Quality Framework `[L2]`
Extend the data quality framework with all of the following:
- **Configurable null checks per table:** Driven by a YAML or JSON config file, not hardcoded.
- **Referential integrity:** Every `UA_ID` in `FACT_KPI_ACTUAL` must exist as an active record in `DIM_KPI`.
- **Freshness check:** Flag `WARNING` if `INGESTION_TS` is older than 7 days.
- **Row count variance:** Flag `WARNING` if Silver row count drops more than 15% vs previous run.
- **Consecutive missing actuals:** Flag any KPI × Month combination where actual is NULL for 3 or more consecutive months.
- **Achievement pct sanity:** Flag any row where `achievement_pct > 300%` or `< 0` (likely a data error, not genuine performance).
- **Currency conversion completeness:** Flag any financial record where `converted_amount_vnd` is null or zero.
- Write results to a `data_quality_log` table with columns: `check_name`, `table_name`, `result` (PASSED/WARNING/FAILED), `row_count`, `checked_at`, `details`. Pipeline continues on WARNING; halts on FAILED.

---

## Part 8: Airflow DAG

### TASK 8A: Required DAG `[L1]`
Build an Airflow DAG that orchestrates both workstreams end to end. Required tasks:

| Task ID | What It Does | Dependencies |
| :--- | :--- | :--- |
| `ingest_erp_api` | Call both ERP endpoints, save raw JSON to Bronze | None |
| `ingest_kpi_actuals` | Copy KPI Excel/CSV files to Bronze | None |
| `ingest_financial_file` | Copy financial flat file to Bronze | None |
| `transform_kpi_silver` | Clean, unpivot, match to master, MERGE DIM_KPI | `ingest_kpi_actuals` |
| `transform_orders_silver` | Join headers + lines, clean, save Silver | `ingest_erp_api` |
| `transform_financial_silver` | Clean, normalise, convert currency, save Silver | `ingest_financial_file` |
| `run_data_quality` | Run all DQ checks, write to data_quality_log | All three Silver tasks |
| `build_gold` | Build Gold outputs: only if DQ result is PASSED or WARNING | `run_data_quality` |
| `notify_result` | Send summary notification: always runs regardless of upstream result | `build_gold` |

#### Also include:
- Weekly schedule (Monday morning).
- Retry logic on ingestion tasks (basic: at least 2 retries with a delay).
- The DAG must not proceed to Gold if `data_quality` result is FAILED.
- `notify_result` must always run: even if upstream tasks fail.

### TASK 8B: Advanced DAG `[L2]`
Extend the DAG with the following:
- Exponential backoff retry on all ingestion tasks.
- Conditional branching from `run_data_quality`: PASSED and WARNING proceed to `build_gold`; FAILED sends alert and stops.
- SLA alert: raise an alarm if the DAG has not completed within 3 hours of its scheduled start.
- The `notify_result` task always runs with a full summary: how many checks passed, warned, failed; row counts per layer; any orphaned or duplicate records found.

#### Scenario Question: Answer in README
> Your team currently runs pipelines using individual user accounts with passwords that expire every 90 days. Every 90 days, all pipelines fail when credentials expire. A colleague suggests everyone resets their password every 89 days. What is the correct solution to this problem, and how would you implement it? Walk through your approach step by step.

---

## Part 9: Gold Layer

### TASK 9A: Required Gold Outputs `[L1]`
Build the following Gold outputs:
- **KPI Monthly Achievement Summary:** `UA_ID`, `KPI_Name`, `Sub_KPI_Type`, `Period`, `actual_value`, `target_value`, `achievement_pct`, `unit`, `is_missing_actual`
- **Pillar Monthly Rollup:** `Pillar`, `Period`, average achievement across all active KPIs in the pillar (exclude NULL actuals from average)
- **Order Cost Summary:** Total cost per customer per month in VND
- **YTD KPI Actuals:** Cumulative actual per KPI for months where actual is not NULL

### TASK 9B: Advanced Gold Outputs `[L2]`
Extend Gold with:
- **3-month rolling average of actual_value per KPI:** Applied using the correct aggregation method per KPI type.
- **Month-over-month variance:** % change from the previous non-null actual.
- **KPI Trend Flag:** `IMPROVING`, `STABLE`, `DECLINING`: define your threshold logic and justify it.
- **Bonus scoring simulation:** For each KPI compute a raw score 0–120 (120 = overachievement ceiling). Apply correct directional logic: lower-is-better KPIs use an inverse formula.
- **Order cost breakdown:** Original currency amount alongside converted VND amount; cost category as % of total per order per month.

---

## Part 10: Platform Thinking (Answer in README)
All questions in this section must be answered in your `README.md`. These are not optional.

### TASK 10A: Git, CI/CD, and Naming Conventions `[BOTH]`
- How would you structure your Git repository for this project: branches, folders, naming conventions?
- What would your CI/CD pipeline do when a PR is raised against main? What checks are enforced before any merge?
- Define your naming convention for: tables, columns, DAG IDs, task IDs, pipeline names, file paths in the data lake.
- Why does consistent naming matter in a team environment? Give a concrete example of what breaks without it.

### TASK 10B: Storage Format and Compute Justification `[BOTH]`
- Build a comparison table: CSV vs XLSX vs JSON vs Parquet for Bronze, Silver, and Gold layers. Justify your choice for each.
- Python vs PySpark: when do you use each? What is your data volume or complexity threshold for switching? What are the trade-offs in a cloud environment?
- Microsoft Fabric: compare SQL Endpoint, Direct Lake, Lakehouse, and Data Warehouse. For this specific pipeline: which would you use for Silver, which for Gold, and why? When does each become the wrong choice?

### TASK 10C: Service Principal and Credentials `[BOTH]`
#### Scenario:
> Your data pipelines in Azure Data Factory are running using individual developer accounts. Each account password expires every 90 days and every time it does, all pipelines fail. A colleague suggests everyone just resets their password every 89 days. What is the correct solution? Walk through exactly how you would implement it and why it is better than the current approach.

### TASK 10D: Schema Evolution in Production `[L2]`
- How would your architecture handle schema evolution if the KPI master file adds three new columns next month?
- How would it scale to 100x current KPI volume: 3,000 KPIs tracked across 50 pillars?
- How do you version your pipeline code alongside the data schema so that a rollback of the pipeline does not corrupt the Delta table?

---

## Submission Checklist

| Deliverable | Content | Band |
| :--- | :--- | :--- |
| [ ] **Architecture design doc** | Part 2A: Bronze/Silver/Gold for both workstreams with justifications | Both |
| [ ] **Dimensional model: KPI** | Part 2B: Full schema with types, PKs, FKs, and justifications | Both |
| [ ] **Dimensional model: Orders** | Part 2C: Full schema including ORD-099 handling | Both |
| [ ] **Grain definition** | Part 1A: Written answers for both workstreams | Both |
| [ ] **Aggregation logic function** | Part 1B: Dynamic aggregation method applied from master | L2 |
| [ ] **Surrogate key design** | Part 3A: Three-layer ID design and ROW_HASH strategy | L2 |
| [ ] **SCD decision table** | Part 3B: Written answers for all 7 attributes | Both |
| [ ] **SCD MERGE implementation** | Part 3C: PySpark MERGE with ROW_HASH | L2 |
| [ ] **ERP API ingestion script** | Part 4A: Python with error handling and auth design | Both |
| [ ] **No-API scenario answer** | Part 4B: Written analysis in README | Both |
| [ ] **KPI Silver transformation** | Part 5A: Cleaning, unpivot, dedup, master match | Both |
| [ ] **Financial Silver transformation** | Part 5B: All cleaning steps including FX conversion | Both |
| [ ] **Mixed units design** | Part 5C: Data type, aggregation safety, achievement formulas | Both |
| [ ] **Schema evolution answers** | Part 6A: All 8 scenarios | Both |
| [ ] **Data quality framework** | Parts 7A (L1) and 7B (L2) | Both |
| [ ] **Airflow DAG** | Parts 8A (L1) and 8B (L2) | Both |
| [ ] **Gold layer scripts** | Parts 9A (L1) and 9B (L2) | Both |
| [ ] **README.md** | Parts 4B, 8B scenario, 10A–10D: all platform and scenario questions | Both |

---

### Evaluation Philosophy
There is no single correct answer. We evaluate thinking quality, decision transparency, trade-off awareness, and intellectual honesty.

An L1 candidate who clearly documents what they do not know will score higher than one who silently makes a wrong assumption. An L2 candidate is expected to justify every architectural decision with production-readiness in mind.

Some parts of this assessment are intentionally ambiguous. How you handle ambiguity is part of what we are assessing.

*UA Manufacturing Digital Solutions Team*