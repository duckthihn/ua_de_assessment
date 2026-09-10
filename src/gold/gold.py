"""
Gold Layer Aggregations Pipeline
Builds analytical tables for KPI achievements, pillar rollups, order cost summaries, and YTD actuals.
"""

import logging
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("gold_layer")

LOWER_IS_BETTER_KPIS = {
    "OT Cost Ratio", "CMP Cost Ratio", "Fabric Waste Rate", "Defect Rate",
    "Customer Returns", "Staff Turnover Rate", "Lost Time Injury Rate",
    "Near Miss Reports", "Sick Days per Employee",
}


def compute_achievement_pct(row) -> float:
    """
    Implements the 4 formula cases from Task 5C:
      (a) lower-is-better %  -> (2 - actual/target) * 100
      (b) higher-is-better % -> actual/target * 100
      (c) SUM-aggregated Number KPI -> same ratio, applied to actual
      (d) zero-target KPI (e.g. Lost Time Injury Rate) -> pass/fail
    """
    actual = row["actual_value"]
    target = row["target_value"]
    kpi_name = row["KPI_Name"]

    if pd.isna(actual):
        return None

    if target == 0:
        return 100.0 if actual == 0 else 0.0

    is_lower_better = kpi_name in LOWER_IS_BETTER_KPIS

    if is_lower_better:
        pct = (2 - actual / target) * 100
    else:
        pct = (actual / target) * 100

    return round(max(-100.0, min(pct, 300.0)), 2)


def build_kpi_monthly_achievement_summary(kpi_silver: pd.DataFrame, master_df: pd.DataFrame) -> pd.DataFrame:
    df = kpi_silver.copy()
    df = df.rename(columns={"Target": "target_value", "PERIOD": "Period", "Unit": "unit"})
    df["is_missing_actual"] = df["actual_value"].isna()
    df["achievement_pct"] = df.apply(compute_achievement_pct, axis=1)

    result = df[["UA_ID", "KPI_Name", "Sub_KPI_Type", "Period", "actual_value",
                 "target_value", "achievement_pct", "unit", "is_missing_actual"]]
    logger.info(f"GOLD | KPI Monthly Achievement Summary: {len(result)} rows")
    return result


def build_pillar_monthly_rollup(kpi_achievement: pd.DataFrame, kpi_silver: pd.DataFrame) -> pd.DataFrame:
    pillar_lookup = kpi_silver[["UA_ID", "Pillar"]].drop_duplicates()
    merged = kpi_achievement.merge(pillar_lookup, on="UA_ID", how="left")

    valid = merged[merged["achievement_pct"].notna()]

    result = (
        valid.groupby(["Pillar", "Period"], as_index=False)["achievement_pct"]
        .mean()
        .rename(columns={"achievement_pct": "avg_achievement_pct"})
    )
    result["avg_achievement_pct"] = result["avg_achievement_pct"].round(2)
    logger.info(f"GOLD | Pillar Monthly Rollup: {len(result)} rows")
    return result


def build_order_cost_summary(financial_silver: pd.DataFrame) -> pd.DataFrame:
    df = financial_silver.copy()

    named_customers = df[~df["is_orphaned"]]
    orphaned = df[df["is_orphaned"]]

    result = (
        named_customers.groupby(["customer_name", "period"], as_index=False)["converted_amount_vnd"]
        .sum()
        .rename(columns={"period": "Period", "converted_amount_vnd": "total_cost_vnd"})
    )

    if not orphaned.empty:
        orphan_summary = (
            orphaned.groupby("period", as_index=False)["converted_amount_vnd"]
            .sum()
            .rename(columns={"period": "Period", "converted_amount_vnd": "total_cost_vnd"})
        )
        orphan_summary["customer_name"] = "UNKNOWN (unmatched orders)"
        result = pd.concat([result, orphan_summary], ignore_index=True)
        logger.warning(f"GOLD | Order Cost Summary includes an explicit 'UNKNOWN' row for "
                        f"{len(orphaned)} orphaned order line(s) — kept visible, not merged "
                        f"into any named customer's total")

    result = result.sort_values(["Period", "customer_name"]).reset_index(drop=True)
    logger.info(f"GOLD | Order Cost Summary: {len(result)} rows")
    return result


def build_ytd_kpi_actuals(kpi_silver: pd.DataFrame) -> pd.DataFrame:
    df = kpi_silver.sort_values(["UA_ID", "PERIOD"]).copy()
    # cumsum naturally skips NaN — a missing month shows NaN for itself but
    # doesn't reset or corrupt the running total for later months. fillna(0)
    # first would be wrong: it would treat a missing month as "contributed
    # zero", understating a SUM-type KPI's true cumulative total.
    df["ytd_actual"] = df.groupby("UA_ID")["actual_value"].cumsum()
    result = df[["UA_ID", "KPI_Name", "Sub_KPI_Type", "PERIOD", "actual_value", "ytd_actual"]]
    result = result.rename(columns={"PERIOD": "Period"})
    logger.info(f"GOLD | YTD KPI Actuals: {len(result)} rows")
    return result


def run_gold_layer(kpi_silver_path: Path, financial_silver_path: Path, master_path: Path,
                    output_dir: Path):
    logger.info("=== Building Gold Layer (Task 9A) ===")

    kpi_silver = pd.read_csv(kpi_silver_path)
    financial_silver = pd.read_csv(financial_silver_path)
    master_df = pd.read_csv(master_path)

    achievement_summary = build_kpi_monthly_achievement_summary(kpi_silver, master_df)
    pillar_rollup = build_pillar_monthly_rollup(achievement_summary, kpi_silver)
    order_cost_summary = build_order_cost_summary(financial_silver)
    ytd_actuals = build_ytd_kpi_actuals(kpi_silver)

    output_dir.mkdir(parents=True, exist_ok=True)
    achievement_summary.to_csv(output_dir / "kpi_monthly_achievement_summary.csv", index=False)
    pillar_rollup.to_csv(output_dir / "pillar_monthly_rollup.csv", index=False)
    order_cost_summary.to_csv(output_dir / "order_cost_summary.csv", index=False)
    ytd_actuals.to_csv(output_dir / "ytd_kpi_actuals.csv", index=False)

    logger.info("=== Gold Layer build complete ===")
    return achievement_summary, pillar_rollup, order_cost_summary, ytd_actuals


if __name__ == "__main__":
    run_gold_layer(
        kpi_silver_path=Path("kpi_actual_silver.csv"),
        financial_silver_path=Path("financial_silver.csv"),
        master_path=Path("kpi_master_dim.csv"),
        output_dir=Path("gold"),
    )