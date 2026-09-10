# UA Manufacturing Data Engineering Pipeline & Technical Assessment (L1 / L2)

## 1. Executive Summary & Pipeline Architecture

This repository implements the end-to-end ELT data pipeline and technical documentation for **UA Manufacturing Digital Solutions Team**, covering both required workstreams:
- **Workstream A: KPI Tracking Pipeline** (Excel/CSV ingestion, unpivoting, master matching, achievement modeling).
- **Workstream B: ERP Orders & Financial Cost Pipeline** (REST API order headers/details, dirty flat financial cleanup, FX conversion to VND, orphan order tracking).

The project adheres to a **Medallion Architecture** (Bronze → Silver → Data Quality Gating → Gold) orchestrated end-to-end via Python and Apache Airflow.

```
                               ┌─────────────────────────┐
                               │     Raw Data Sources    │
                               │ KPI / ERP API / Finance │
                               └────────────┬────────────┘
                                            │
                                            ▼
                              ┌──────────────────────────┐
                              │       BRONZE LAYER       │
                              │ Raw Json / CSV Ingestion │
                              └─────────────┬────────────┘
                                            │
                                            ▼
                              ┌──────────────────────────┐
                              │       SILVER LAYER       │
                              │ Clean, Unpivot, Dedupe   │
                              │ Currency FX, Master Match│
                              └─────────────┬────────────┘
                                            │
                                            ▼
                              ┌──────────────────────────┐
                              │  DATA QUALITY EVALUATION │
                              │   Gating: Halt on FAIL   │
                              └─────────────┬────────────┘
                                            │
                                            ▼
                              ┌──────────────────────────┐
                              │        GOLD LAYER        │
                              │ KPI Achievement & Rollup │
                              │   Order Cost Aggregates  │
                              └──────────────────────────┘
```

---

## 2. Quickstart & Pipeline Execution

### Prerequisites
- Python 3.10+
- Pandas, NumPy

### Execution via Single Entrypoint
To run the complete pipeline end-to-end (ingest Bronze data, clean & transform to Silver, run automated Data Quality checks with gating, and build Gold analytical summaries):

```bash
python3 main.py
```

### Expected Output
- **Bronze Layer (`data/bronze/`)**: Native JSON and raw CSV exports with ingestion metadata (`ingestion_timestamp`, `source_file`).
- **Silver Layer (`data/silver/`)**: Cleaned, unpivoted datasets (`silver_kpi.csv`, `silver_financial.csv`) and the audit log (`data_quality_log.csv`).
- **Gold Layer (`data/gold/`)**: Business-ready analytical aggregates (`kpi_monthly_achievement_summary.csv`, `pillar_monthly_rollup.csv`, `order_cost_summary.csv`, `ytd_kpi_actuals.csv`).

---

## 3. Project Directory Structure

```
ua-de-assessment/
├── main.py                             # Single entrypoint script running end-to-end pipeline
├── DATA_ENGINEER_ASSESSMENT.md         # Full assessment prompt & requirements
├── dataset/                            # Raw mock API responses and initial CSV/Excel files
│   ├── exchange_rates_reference.csv
│   ├── financial_long_format.csv
│   ├── financial_wide_format.csv
│   ├── kpi_actual_long.csv
│   ├── kpi_actual_wide.csv
│   ├── kpi_master_dim.csv
│   ├── mock_orders_details.json
│   └── mock_orders_headers.json
├── src/                                # Core pipeline source code
│   ├── ingestion/
│   │   └── erp_api_ingestion.py        # ERP REST API client with Bearer auth ready & error handling
│   ├── transformation/
│   │   ├── silver_kpi.py               # OCR cleaning, unpivot M1-M12 / Jan-24, master dim match
│   │   └── silver_financial.py         # Multi-format date standardisation, FX conversion, orphan handling
│   ├── quality/
│   │   └── data_quality.py             # Task 7A DQ checks (PASSED/WARNING/FAILED log & gating)
│   ├── gold/
│   │   └── gold.py                     # Gold layer aggregations (Achievement, Pillar Rollup, Order Costs)
│   └── orchestration/
│       └── dag.py                      # Apache Airflow DAG definition (Task 8A / 8B)
├── docs/                               # Detailed design documents for all assessment tasks
│   ├── 1A - Grain Definition.md
│   ├── 2A - Architecture Design Doc.md
│   ├── 2B - Dimensional model - KPI.md
│   ├── 2C - Dimensional model - Orders.md
│   ├── 3B - SCD decision table.md
│   ├── 4A - ERP API Ingestion Script.md
│   ├── 4B - No-API scenario answer.md
│   ├── 5A - KPI Silver transformation.md
│   ├── 5B - Financial Silver transformation .md
│   ├── 5C - Mixed units design.md
│   ├── 6A - Schema evolution answers.md
│   ├── 7A - Data quality framework.md
│   ├── 8A - Airflow DAG.md
│   ├── 9A - Gold layer scripts.md
│   └── 10A-10D All platform and scenarios answers.md
└── data/                               # Pipeline outputs generated at runtime
    ├── bronze/
    ├── silver/
    └── gold/
```

---

## 4. Platform & Scenario Responses

### Task 4B — "The ERP Has No API" Scenario
**Scenario:** Data exists only inside a web application with no export button, no database access, and vendor refuses to build an API. Data is needed weekly.

#### 1. Options Comparison:
| Option | Technical Risk | Business Risk | Maintenance Cost |
|---|---|---|---|
| **Web Scraping** (Browser automation via Playwright/Selenium) | Layout changes break HTML selectors | Terms of service compliance | High (selector maintenance) |
| **Manual Export + Upload** (Shared folder upload) | Low technical risk, high human error | Dependency on single person's availability | Medium (ongoing labor) |
| **RPA Tool** (UiPath / Automation Anywhere) | Similar UI fragility to web scraping | Licensing overhead | Medium |
| **Vendor Scheduled Report / DB Export** | Dependent on vendor willingness | Extra vendor fees | Low (once setup) |
| **Screen Scraping via OCR** | High OCR misread rate (e.g. `O` vs `0`) | Risk of silent financial errors | High |

#### 2. Recommendation & Strategy:
Start with **Web Scraping** as a managed bridge with strict alerts (diff monitoring on DOM structure). Pair it with strong data validation at Bronze/Silver. If layout changes occur, fail gracefully and notify on-call DEs. Concurrently, push commercial leadership to negotiate a scheduled SFTP/email CSV dump with the vendor.

#### 3. Migration Plan when Vendor API becomes available (6 months later):
Run the new API and interim Web Scraper **in parallel for 4 weeks**, running automated reconciliation checks between both sources. Once zero-delta is proven, deprecate the scraper without altering downstream Silver/Gold models.

---

### Task 8B / 10C — Credential Management & Service Principals
**Scenario:** Pipelines fail every 90 days due to personal developer account password expiration. A colleague suggests resetting passwords every 89 days.

#### Why "Reset Every 89 Days" Is Flawed:
1. Tying pipeline execution to human identities creates single-point-of-failure vulnerabilities when developers leave.
2. Manually updating credentials violates security auditing and least-privilege principles.

#### The Production Solution:
1. **Service Principal / Managed Identity**: Provision an Azure AD Service Principal or System-Assigned Managed Identity dedicated strictly to Data Factory / Airflow execution.
2. **Least Privilege Scope**: Assign RBAC roles restricted only to target storage containers (e.g., `Storage Blob Data Contributor` on `raw/` and `silver/`).
3. **Azure Key Vault Integration**: Store client secrets inside Azure Key Vault with automated 30-day expiry notifications via Event Grid / Slack. Managed Identity completely eliminates password rotation requirements.

---

### Task 10A — Git, CI/CD, and Naming Conventions
- **Git Branching Strategy**: `main` (protected production), `develop` (integration), and `feature/<ticket-id>-<description>` feature branches. Hotfixes branch from `main`.
- **CI/CD Quality Gates**:
  1. Automated formatting & linting (`ruff` / `black`).
  2. Unit test suite execution on transformations.
  3. Airflow DAG import sandbox check (`python -m py_compile dag.py`).
  4. Schema evolution validation against test fixtures.
  5. Mandatory peer code review approval prior to merging.

---

### Task 10B — Storage Format & Compute Justification
- **Storage Format**:
  - **Bronze**: Raw native format (JSON / CSV) to preserve original source structure for replayability.
  - **Silver / Gold**: **Parquet / Delta Lake** for schema enforcement, high compression, columnar speed, and predicate pushdown.
- **Compute Selection (Python vs PySpark)**:
  - **Python / Pandas**: Chosen for this pipeline due to dataset scale (< 10GB, fits comfortably in single-node memory). Provides fast execution without cluster spin-up latency.
  - **PySpark**: Transition threshold is reached when single file/table volume exceeds single-machine RAM (> 50GB or > 10M records) or when distributed Delta MERGE operations across large fact tables are required.

---

### Task 10D — Schema Evolution in Production
1. **New Master Columns**: Handled via schema-on-read in Bronze. Silver ingestion utilizes Delta Lake `mergeSchema=true` after explicit schema validation to prevent silent field dropping.
2. **100x Scale-Up (3,000 KPIs, 50 Pillars)**: Vectorize string parsing and OCR routines in PySpark (`F.regexp_replace`), partition Delta tables by `Pillar` and `PERIOD`, and parallelize Airflow task groups per pillar.

---

## 5. Deliverables Submission Verification

| Deliverable | Location / Artifact | Status |
|---|---|:---:|
| **Grain Definition** | [`docs/1A - Grain Definition.md`](file:///home/duckthihn/ua_de_assessment/docs/1A%20-%20Grain%20Definition.md) | Verified ✓ |
| **Architecture Design** | [`docs/2A - Architecture Design Doc.md`](file:///home/duckthihn/ua_de_assessment/docs/2A%20-%20Architecture%20Design%20Doc.md) | Verified ✓ |
| **KPI Dimensional Model** | [`docs/2B - Dimensional model - KPI.md`](file:///home/duckthihn/ua_de_assessment/docs/2B%20-%20Dimensional%20model%20-%20KPI.md) | Verified ✓ |
| **Orders Dimensional Model** | [`docs/2C - Dimensional model - Orders.md`](file:///home/duckthihn/ua_de_assessment/docs/2C%20-%20Dimensional%20model%20-%20Orders.md) | Verified ✓ |
| **Surrogate Key & SCD Table** | [`docs/3B - SCD decision table.md`](file:///home/duckthihn/ua_de_assessment/docs/3B%20-%20SCD%20decision%20table.md) | Verified ✓ |
| **ERP API Ingestion Script** | [`src/ingestion/erp_api_ingestion.py`](file:///home/duckthihn/ua_de_assessment/src/ingestion/erp_api_ingestion.py) | Verified ✓ |
| **No-API Scenario Answer** | Section 4 of `README.md` & [`docs/4B - No-API scenario answer.md`](file:///home/duckthihn/ua_de_assessment/docs/4B%20-%20No-API%20scenario%20answer.md) | Verified ✓ |
| **KPI Silver Transformation** | [`src/transformation/silver_kpi.py`](file:///home/duckthihn/ua_de_assessment/src/transformation/silver_kpi.py) | Verified ✓ |
| **Financial Silver Transformation** | [`src/transformation/silver_financial.py`](file:///home/duckthihn/ua_de_assessment/src/transformation/silver_financial.py) | Verified ✓ |
| **Mixed Units Design** | [`docs/5C - Mixed units design.md`](file:///home/duckthihn/ua_de_assessment/docs/5C%20-%20Mixed%20units%20design.md) | Verified ✓ |
| **Schema Evolution Answers** | [`docs/6A - Schema evolution answers.md`](file:///home/duckthihn/ua_de_assessment/docs/6A%20-%20Schema%20evolution%20answers.md) | Verified ✓ |
| **Data Quality Framework** | [`src/quality/data_quality.py`](file:///home/duckthihn/ua_de_assessment/src/quality/data_quality.py) | Verified ✓ |
| **Airflow DAG** | [`src/orchestration/dag.py`](file:///home/duckthihn/ua_de_assessment/src/orchestration/dag.py) | Verified ✓ |
| **Gold Layer Scripts** | [`src/gold/gold.py`](file:///home/duckthihn/ua_de_assessment/src/gold/gold.py) | Verified ✓ |
| **Full README & Documentation** | `README.md` & [`docs/10A-10D All platform and scenarios answers.md`](file:///home/duckthihn/ua_de_assessment/docs/10A-10D%20All%20platform%20and%20scenarios%20answers.md) | Verified ✓ |
