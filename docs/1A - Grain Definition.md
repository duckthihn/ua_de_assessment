# Task 1A — Grain Definition

## Workstream A: FACT_KPI_ACTUAL

| Grain Option | Verdict | Justification |
|---|---|---|
| One row per KPI per Year | **Incorrect** | Destroys monthly tracking and MoM trends. |
| One row per KPI Name per Month | **Incorrect** | Blends distinct `Sub_KPI_Type` entries (e.g. Direct vs Indirect targets). |
| One row per Pillar per Month | **Incorrect** | Coarse Gold-layer rollup grain. |
| **One row per KPI + Sub KPI Type per Month** | **Correct** | Matches `DIM_KPI` grain × `DIM_DATE` without loss of granularity. |
| One row per KPI + Sub KPI Type + Department per Month | **Incorrect** | Redundant; Department is functionally dependent on KPI + Sub KPI Type. |

---

## Workstream B: FACT_ORDER_COST

| Grain Option | Verdict | Justification |
|---|---|---|
| One row per order | **Incorrect** | Loses cost category breakdown (fabric/trim/outsource). |
| One row per order × cost category | **Incorrect** | Loses monthly granularity for recurring order costs. |
| **One row per order × cost category × month** | **Correct** | Matches `financial_long_format.csv` structure and enables monthly cost rollups. |
| One row per customer × month | **Incorrect** | Gold-layer summary grain. |

---

## Region Dimension Addition
- **KPI Workstream**: Region joins via `DIM_DEPARTMENT` or customer dimension without altering the fact table grain.
- **Orders Workstream**: Region attaches to `dim_customer` or `dim_factory` as an attribute unless orders are split across multiple regions.