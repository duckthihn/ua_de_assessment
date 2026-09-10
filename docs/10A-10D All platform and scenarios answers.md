# Task 10A — Git, CI/CD, and Naming Conventions

## Repository Structure
Standard Medallion layout: `dataset/` (raw inputs), `src/` (pipeline code by stage), `data/` (runtime outputs), `docs/` (design docs), and `main.py` entrypoint.

## Branches
- `main`: Protected production branch.
- `develop`: Integration branch.
- `feature/<ticket-id>-<description>`: Short-lived feature branches.

## CI/CD Pipeline Checks (PR against `main`)
1. **Linting**: Run `ruff` / `black` for code formatting.
2. **Unit Tests**: Test transformation functions on sample fixtures.
3. **DAG Import Check**: Verify DAG imports cleanly without syntax errors.
4. **Data Quality Dry-Run**: Validate output schema and data quality rules against sample inputs.
5. **Code Review**: At least 1 peer approval required before merging.

## Naming Conventions
- **Tables**: `snake_case` with layer prefix (`dim_kpi`, `fact_kpi_actual`, `gold_kpi_monthly_achievement`).
- **Columns**: `snake_case`, descriptive (`actual_value`, `converted_amount_vnd`).
- **DAG / Task IDs**: `snake_case`, `<verb>_<object>` (`ingest_erp_api`, `transform_kpi_silver`).

---

# Task 10B — Storage Format and Compute Justification

## Storage Format Matrix
- **Bronze**: Raw source format (JSON/CSV) to preserve original structure for auditing and replayability.
- **Silver / Gold**: **Parquet / Delta Lake** for schema safety, columnar performance, compression, and fast analytical queries.

## Python vs PySpark
- **Python (pandas)**: Fits current data scale (< 10GB, fits comfortably in single-machine RAM). Near-instant startup, zero cluster overhead.
- **PySpark**: Transition when single dataset size exceeds single-machine memory (> 50GB or > 10M rows) or when distributed Delta MERGE across large fact tables is needed.

## Microsoft Fabric Components
- **Lakehouse**: Ideal for Bronze & Silver (flexible schema, Delta tables, MERGE support).
- **Data Warehouse / Direct Lake**: Ideal for Gold reporting layer (SQL read/write semantics and fast Power BI connectivity).

---

# Task 10C — Service Principal and Credentials

## Problem with "Reset every 89 days"
Relying on manual password resets under personal developer accounts creates a single point of failure when employees leave and violates security auditing standards.

## Production Solution
1. **Use Service Principal / Managed Identity**: Provision a dedicated Azure AD Service Principal or System-Assigned Managed Identity for pipeline execution.
2. **Least Privilege**: Scope access permissions strictly to target storage containers.
3. **Azure Key Vault**: Store client secrets securely in Key Vault (or use Managed Identity to eliminate secrets entirely).
4. **Automated Expiry Alerts**: Set Key Vault alerts 30 days prior to secret expiration.

---

# Task 10D — Schema Evolution in Production

## Handling New KPI Master Columns
Bronze ingests raw data as-is. In Silver, update table schema using Delta Lake `mergeSchema=true` after validating new columns.

## Scaling to 100x Volume
Vectorize string parsing and OCR routines in PySpark (`F.regexp_replace`), partition tables by `Pillar` and `PERIOD`, and parallelize Airflow DAG tasks by domain.

## Code Versioning vs Schema Evolution
Tag releases in Git (e.g. `v1.4.0`) and record schema versions. Delta Lake time-travel (`VERSION AS OF`) allows rolling back table data independently of code releases if needed.