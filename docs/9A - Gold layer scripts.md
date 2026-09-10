# Task 9A — Gold Layer Scripts

**Source Code:** [`src/gold/gold.py`](file:///home/duckthihn/ua_de_assessment/src/gold/gold.py)

## Gold Output Tables Summary

| Output Dataset | Rows | Description |
|---|---|---|
| **KPI Monthly Achievement Summary** | 348 | Monthly actuals vs targets with directional achievement % calculations. |
| **Pillar Monthly Rollup** | 48 | Average pillar achievement across 4 pillars (FS, CE, OF, PP) × 12 months. |
| **Order Cost Summary** | 8 | Monthly cost rollups by customer in VND (includes `UNKNOWN` for ORD-099). |
| **YTD KPI Actuals** | 348 | Cumulative YTD sum per KPI (skips missing months). |

---

## Polarity Mapping Strategy
Lower-is-better metrics (*OT Cost Ratio*, *Defect Rate*, *Turnover Rate*, etc.) utilize inverse achievement calculation:

$$\text{achievement\_pct} = (2 - \frac{\text{actual}}{\text{target}}) \times 100$$

Higher-is-better metrics use standard ratio calculation:

$$\text{achievement\_pct} = \frac{\text{actual}}{\text{target}} \times 100$$