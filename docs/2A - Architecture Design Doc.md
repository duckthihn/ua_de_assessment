# Task 2A — Architecture Design Doc

## Medallion Layer Specifications

| Layer | Source | Contents | Transformations Applied | File Format | Partitioning |
|---|---|---|---|---|---|
| **Bronze** | KPI Actuals | Raw CSV/XLSX export | Add `ingestion_ts`, `source_file` | CSV / JSON | By `ingestion_date` |
| **Bronze** | KPI Master | Raw Master Dim snapshot | Add `ingestion_ts` | CSV | By `load_date` |
| **Bronze** | ERP API | Raw order JSON responses | Add `ingestion_ts` | JSON | By `ingestion_date` |
| **Bronze** | Financial File | Raw dirty flat file | Add `ingestion_ts` | CSV | By `ingestion_date` |
| **Silver** | KPI Unified | Cleaned KPI fact table | Fix OCR typos, unpivot to `PERIOD` (YYYY-MM), match `UA_ID` | Parquet / Delta | By `PERIOD` |
| **Silver** | Orders Unified | Cleaned ERP orders & lines | Join headers & details, deduplicate | Parquet / Delta | By `order_month` |
| **Silver** | Financial Unified | Cleaned cost fact table | Fix OCR, standardise period & customer, FX convert to VND | Parquet / Delta | By `PERIOD` |
| **Gold** | KPI Summary | Monthly achievement & pillar rollups | Calculate achievement %, pillar averages | Parquet / Delta | By `PERIOD` |
| **Gold** | Order Summary | Cost rollups | Customer × month aggregations | Parquet / Delta | By `PERIOD` |

---

## Technical Justifications

### 1. Intermediate File Format (Parquet over CSV/JSON)
- **Schema & Type Safety**: Parquet enforces strict column types, preventing OCR typos (e.g. `875O.00`) from slipping through as valid strings.
- **Query Performance**: Columnar layout supports predicate pushdown and integrates natively with Delta Lake for MERGE operations.

### 2. Incremental Load Strategy

| Source | Strategy | Rationale |
|---|---|---|
| KPI Actuals | Full overwrite by period | Batch file export without changelog pointers. |
| KPI Master Dim | UPSERT / MERGE (SCD) | Maintains version history (`Valid_From`, `Is_Active`). |
| ERP API | Append + UPSERT on `order_id` | Prevents duplicate order records on API retries. |
| Financial File | Full reload + row-hash dedupe | Batch export with known duplicates. |

### 3. Compute Choice (Python vs PySpark)
- **Pandas / Python**: Selected for datasets under 10GB that fit comfortably in single-node RAM. Eliminates cluster spin-up latency and infrastructure cost.
- **PySpark**: Switch when dataset volume exceeds single-machine memory (> 50GB or > 10M records) or when distributed Spark joins are required.

### 4. Fabric Architecture Matrix
- **Bronze / Silver**: **Lakehouse (Delta Tables)** for schema flexibility, file storage, and Delta MERGE operations.
- **Gold**: **Data Warehouse / Direct Lake** for SQL views, row-level security, and direct Power BI reporting.