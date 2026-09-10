# Task 8A — Required Airflow DAG

**Source Code:** [`src/orchestration/dag.py`](file:///home/duckthihn/ua_de_assessment/src/orchestration/dag.py)

## Task Matrix & Dependencies

| Task ID | Functionality | Upstream Dependencies |
|---|---|---|
| `ingest_erp_api` | Ingest ERP headers & lines to Bronze | None |
| `ingest_kpi_actuals` | Copy raw KPI files to Bronze | None |
| `ingest_financial_file` | Copy raw financial files to Bronze | None |
| `transform_kpi_silver` | Clean & unpivot KPI data | `ingest_kpi_actuals` |
| `transform_orders_silver` | Clean order data | `ingest_erp_api` |
| `transform_financial_silver` | Clean & convert financial data | `ingest_financial_file` |
| `run_data_quality` | Run DQ checks & write log | All 3 Silver tasks |
| `build_gold` | Build Gold aggregations (if DQ passes/warns) | `run_data_quality` |
| `notify_result` | Send run summary (always runs) | `build_gold` |

## Execution DAG Flow

```
ingest_kpi_actuals ───────► transform_kpi_silver ──────┐
ingest_erp_api ──────────► transform_orders_silver ────┼──► run_data_quality ──► build_gold ──► notify_result
ingest_financial_file ───► transform_financial_silver ─┘                                     (all_done)
```

## Key Configuration
- **Schedule**: `0 6 * * MON` (6:00 AM every Monday).
- **Retries**: `retries: 2`, `retry_delay: 5 minutes`.
- **Quality Gate**: `run_data_quality` raises an exception on `FAILED`, preventing `build_gold` from running via `TriggerRule.ALL_SUCCESS`.
- **Notification**: `notify_result` uses `TriggerRule.ALL_DONE` to guarantee execution regardless of upstream status.