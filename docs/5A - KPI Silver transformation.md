# Task 5A — KPI Silver Transformation

**Source Code:** [`src/transformation/silver_kpi.py`](file:///home/duckthihn/ua_de_assessment/src/transformation/silver_kpi.py)

## Pipeline Steps Summary

| Step | Transformation Applied | Result |
|---|---|---|
| Categorical Cleanup | Strip whitespace and collapse double spaces | 11 strings cleaned |
| Raw Deduplication | Drop exact duplicate rows post-cleanup | 3 duplicate rows dropped |
| Unpivot | Transform long (`M1-M12`) & wide (`Jan-24...Dec-24`) to `PERIOD` (`YYYY-MM`) | 348 unpivoted rows |
| Reconciliation | Reconcile long and wide outputs by natural key | Zero conflicts detected |
| Master Matching | Match composite key to `kpi_master_dim.csv` (`UA_ID`) | 348 matched rows (0 orphans) |
| Audit Enrichment | Append `ROW_HASH` (SHA256), `INGESTION_TS`, `IS_ORPHANED` | Audit flags added |

## Reconciliation Strategy
If long and wide format values conflict for the same KPI × month, wide format is treated as primary while logging a warning for review.