# Task 5C — Handle Mixed Units

## Data Type & Storage Standards

| Question | Answer & Rationale |
|---|---|
| **Data Type for `actual_value`** | **DECIMAL(18,4)**. Prevents floating-point rounding errors while providing exact precision for both ratios (`0.8500`) and counts (`12400.0000`). |
| **Prevent Accidental BI Sums** | Always expose `unit` alongside metrics and enforce BI measures to group by `unit` before aggregating. |
| **Percentage Representation** | Store as **decimal ratio (0.85)** to align with master target definitions (`Yearly_Target = 0.85`). |

---

## Achievement Percentage Formulas

1. **Lower is Better (%)** (e.g. OT Cost Ratio, target 0.12):
   $$\text{achievement\_pct} = (2 - \frac{\text{actual}}{\text{target}}) \times 100$$
2. **Higher is Better (%)** (e.g. Line Efficiency, target 0.85):
   $$\text{achievement\_pct} = \frac{\text{actual}}{\text{target}} \times 100$$
3. **Number KPI with SUM Aggregation** (e.g. FOB Revenue):
   $$\text{achievement\_pct} = \frac{\sum \text{actual\_ytd}}{\text{yearly\_target}} \times 100$$
4. **Zero-Target KPI** (e.g. Lost Time Injuries, target 0):
   $$\text{achievement\_pct} = \begin{cases} 100, & \text{if actual} = 0 \\ 0, & \text{if actual} > 0 \end{cases}$$