# Task 3B — SCD Decision Table

| Attribute | SCD Type | Justification |
|---|---|---|
| `kpi_name` | **Type 2** | Preserves historical KPI naming in past reports. |
| `unit` (% → Number) | **Type 2** | Unit changes alter metric interpretation; past ratios must not be labeled as counts. |
| `yearly_target` (M6 revision) | **Type 2** | Prevents recalculating past monthly achievements with revised targets. |
| `aggregation_method` | **Type 2** | Historical rollups must use the aggregation rule in effect during that period. |
| `department` (ownership move) | **Type 2** | Historical department performance reporting requires accurate ownership timelines. |
| `is_active` | **Type 1** | Current status flag; overwrite in place. |
| `pillar_id` (restructure) | **Type 2** | Protects historical pillar rollups from moving past months to new pillars. |

---

## Unit Change Scenario (% → Number at M7)

1. **Failure Mode**: Overwriting unit to `'Number'` (Type 1) causes Gold aggregations to silently add M1–M6 ratios (`0.94`) with M7–M12 counts (`12,400`), producing corrupted reports.
2. **Correct Handling**:
   - Expire old dimension row at M6 (`valid_to = 2024-06-30`).
   - Insert new SCD Type 2 dimension row with `unit = 'Number'` (`valid_from = 2024-07-01`).
   - Fact rows for M1–M6 point to old `kpi_sk`; M7–M12 point to new `kpi_sk`.
3. **Gold Safety**: Group by `(kpi_name, unit)` to keep ratio and count periods distinct in reports.