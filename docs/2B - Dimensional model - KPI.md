# Task 2B — Dimensional Model: KPI Workstream

## Schema Overview

| Table | Column | Type | Key | Notes |
|---|---|---|---|---|
| **DIM_KPI** | `kpi_sk` | BIGINT | **PK** | Surrogate key (SCD Type 2) |
| | `ua_id` | VARCHAR(15) | Natural Key | e.g. `UA-001` |
| | `pillar` | VARCHAR(5) | | FS / CE / OF / PP |
| | `sub_pillar` | VARCHAR(50) | | |
| | `department` | VARCHAR(50) | | |
| | `kpi_name` | VARCHAR(100) | | |
| | `sub_kpi_type` | VARCHAR(50) | | Sentinel `'ALL'` if blank |
| | `unit` | VARCHAR(10) | | `%` or `Number` |
| | `yearly_target` | DECIMAL(18,4) | | Target value |
| | `aggregation_method` | VARCHAR(10) | | `SUM` / `AVERAGE` / `LAST` |
| | `is_active`, `valid_from`, `valid_to` | CHAR / DATE | | SCD metadata |
| **DIM_DATE** | `date_sk` | INT | **PK** | Format `YYYYMM` |
| **FACT_KPI_ACTUAL** | `kpi_fk` | INT | **FK → DIM_KPI** | Composite PK `(kpi_fk, date_fk)` |
| | `date_fk` | INT | **FK → DIM_DATE** | Composite PK `(kpi_fk, date_fk)` |
| | `actual_value` | DECIMAL(18,4) | | Measured actual |
| | `target_value` | DECIMAL(18,4) | | Snapshot of target at period load time |
| | `achievement_pct` | DECIMAL(9,4) | | Calculated achievement |
| | `is_missing_actual`, `is_orphaned` | BOOLEAN | | Data quality flags |

---

## Design Decisions

1. **Star Schema vs Snowflake**: Star schema with `DIM_DEPARTMENT` linking to `DIM_PILLAR` to simplify analytical BI reporting.
2. **Missing Sub KPI Type Handling**: Standardised to sentinel value `'ALL'` instead of `NULL` to prevent join mismatches.
3. **Target Value Location**: Stored in both `DIM_KPI` and snapshot into `FACT_KPI_ACTUAL` to preserve historical achievement calculations if targets change mid-year.
4. **Achievement Calculation**:
   - **Higher is better** (e.g. Line Efficiency): `(actual / target) * 100`
   - **Lower is better** (e.g. Defect Rate): `(2 - (actual / target)) * 100`