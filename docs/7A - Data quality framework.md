# Task 7A — Data Quality Framework

**Source Code:** [`src/quality/data_quality.py`](file:///home/duckthihn/ua_de_assessment/src/quality/data_quality.py)

## Execution Summary
- **Total Checks Evaluated**: 16
- **Results**: **14 PASSED**, **2 WARNING**, **0 FAILED**
- **Audit Log Destination**: [`data/silver/data_quality_log.csv`](file:///home/duckthihn/ua_de_assessment/data/silver/data_quality_log.csv)

## Audit Matrix

| Rule Check | KPI Silver Result | Financial Silver Result | Status |
|---|---|---|:---:|
| **Row Count > 0** | PASSED (348 rows) | PASSED (31 rows) | PASSED |
| **Mandatory Columns Present** | PASSED (`UA_ID`, `PERIOD`, `Unit`) | PASSED (`order_no`, `category`, `period`, `converted_amount_vnd`) | PASSED |
| **Null Ratio Threshold** | WARNING (`actual_value` 19.8% null - expected) | PASSED (0% nulls) | WARNING |
| **Orphan Flagging** | PASSED (0 orphans) | WARNING (2 rows ORD-099 flagged `is_orphaned=True`) | WARNING |
| **Deduplication Validation** | PASSED (0 duplicate keys) | PASSED (0 duplicate keys) | PASSED |
| **Numeric Parsing Validation** | PASSED | PASSED | PASSED |