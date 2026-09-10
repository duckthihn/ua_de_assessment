# Task 6A — Schema Evolution: Model Survival Test

| # | Business Change | Impact | Required Pipeline Action |
|---|---|---|---|
| 1 | New KPI "Sustainability Score" under sub-pillar "ESG" | **Compatible** | Add new row to `DIM_KPI` master; Silver pipeline ingests new dimension & fact rows automatically. |
| 2 | On Time Delivery Rate unit change (% → Number) | **Requires SCD2** | Create new SCD Type 2 dimension row (`unit = 'Number'`). M1–M6 fact rows retain old `unit = '%'`. |
| 3 | Line Efficiency for Line D added starting M7 (M1–M6 blank) | **Compatible** | `actual_value` is nullable; set `is_missing_actual = True` for unlaunched periods. |
| 4 | Sub-pillar "Cost Efficiency" renamed to "Cost Control" | **Compatible** | Stable surrogate `SP_ID` protects FKs; update descriptive text via SCD Type 2. |
| 5 | Target change 0.12 → 0.10 starting M6 | **Compatible** | Target is snapshotted into `FACT_KPI_ACTUAL`; past M1–M5 achievement percentages remain unaffected. |
| 6 | FOB Revenue tracked at department level (grain change) | **Breaking Change** | Requires grain evolution or separate department-level fact table + historical backfill strategy. |
| 7 | Three new cost categories added to financial file | **Compatible** | Dynamic category grain handles new row values without table DDL changes. |
| 8 | Two KPIs retired starting M9 | **Compatible** | Soft-delete via `DIM_KPI.is_active = 'N'`; historical M1–M8 facts retained untouched. |