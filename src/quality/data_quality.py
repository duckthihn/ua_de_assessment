"""
Data Quality Checks Framework
Executes automated quality checks on Silver datasets and logs results.
"""

import logging
from pathlib import Path

import pandas as pd

from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("data_quality")

RESULTS = []


def record(check_name: str, table_name: str, result: str, row_count: int, details: str):
    RESULTS.append({
        "check_name": check_name,
        "table_name": table_name,
        "result": result,
        "row_count": row_count,
        "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "details": details,
    })
    log_fn = {"PASSED": logger.info, "WARNING": logger.warning, "FAILED": logger.error}[result]
    log_fn(f"[{result}] {table_name} | {check_name} | {details}")


def check_not_empty(df: pd.DataFrame, table_name: str):
    if len(df) > 0:
        record("row_count_not_empty", table_name, "PASSED", len(df), f"{len(df)} rows present")
    else:
        record("row_count_not_empty", table_name, "FAILED", 0, "Table is empty — 0 rows found")


def check_mandatory_columns(df: pd.DataFrame, table_name: str, mandatory_cols: list):
    for col in mandatory_cols:
        if col not in df.columns:
            record("mandatory_column_present", table_name, "FAILED", len(df),
                   f"Column '{col}' is missing entirely")
            continue
        null_count = df[col].isna().sum()
        if null_count == len(df) and len(df) > 0:
            record("mandatory_column_present", table_name, "FAILED", len(df),
                   f"Column '{col}' is present but fully null")
        elif null_count > 0:
            record("mandatory_column_present", table_name, "WARNING", len(df),
                   f"Column '{col}' has {null_count} null value(s) out of {len(df)} "
                   f"({null_count/len(df):.1%}) — not fully null, but worth reviewing")
        else:
            record("mandatory_column_present", table_name, "PASSED", len(df),
                   f"Column '{col}' present with no nulls")


def check_orphans_flagged(df: pd.DataFrame, table_name: str, orphan_col: str):
    if orphan_col not in df.columns:
        record("orphans_flagged", table_name, "FAILED", len(df),
               f"Expected orphan flag column '{orphan_col}' not found")
        return
    n_orphaned = int(df[orphan_col].sum())
    if n_orphaned == 0:
        record("orphans_flagged", table_name, "PASSED", len(df),
               "No orphaned records in this batch — nothing to flag")
    else:
        record("orphans_flagged", table_name, "WARNING", len(df),
               f"{n_orphaned} orphaned record(s) found and correctly flagged "
               f"({orphan_col}=True) — review recommended, not an error by itself")


def check_no_duplicates_remain(df: pd.DataFrame, table_name: str, key_cols: list):
    dup_count = df.duplicated(subset=key_cols, keep=False).sum()
    if dup_count == 0:
        record("no_duplicates_remain", table_name, "PASSED", len(df),
               f"No duplicate rows on key {key_cols}")
    else:
        record("no_duplicates_remain", table_name, "FAILED", len(df),
               f"{dup_count} row(s) still share a duplicate key {key_cols} "
               f"after the dedup step — dedup logic likely missed a case")


def check_numeric_parses_cleanly(df: pd.DataFrame, table_name: str, numeric_col: str):
    if numeric_col not in df.columns:
        record("numeric_column_valid", table_name, "FAILED", len(df),
               f"Expected numeric column '{numeric_col}' not found")
        return
    coerced = pd.to_numeric(df[numeric_col], errors="coerce")
    newly_failed = coerced.isna() & df[numeric_col].notna()
    n_failed = int(newly_failed.sum())
    if n_failed == 0:
        record("numeric_column_valid", table_name, "PASSED", len(df),
               f"'{numeric_col}' parses cleanly as numeric for all non-null rows "
               f"— no leftover OCR-style typos detected")
    else:
        bad_values = df.loc[newly_failed, numeric_col].tolist()
        record("numeric_column_valid", table_name, "FAILED", len(df),
               f"{n_failed} value(s) in '{numeric_col}' do not parse as numeric: "
               f"{bad_values} — likely a leftover OCR typo or bad data")


def run_dq_checks(kpi_silver_path: Path, financial_silver_path: Path) -> pd.DataFrame:
    global RESULTS
    RESULTS.clear()
    logger.info("=== Starting Data Quality Checks (Task 7A, L1) ===")

    kpi_df = pd.read_csv(kpi_silver_path)
    fin_df = pd.read_csv(financial_silver_path)

    check_not_empty(kpi_df, "kpi_actual_silver")
    check_mandatory_columns(kpi_df, "kpi_actual_silver",
                             mandatory_cols=["UA_ID", "PERIOD", "actual_value", "Unit"])
    check_orphans_flagged(kpi_df, "kpi_actual_silver", orphan_col="IS_ORPHANED")
    check_no_duplicates_remain(kpi_df, "kpi_actual_silver", key_cols=["UA_ID", "PERIOD"])
    check_numeric_parses_cleanly(kpi_df, "kpi_actual_silver", numeric_col="actual_value")

    check_not_empty(fin_df, "financial_silver")
    check_mandatory_columns(fin_df, "financial_silver",
                             mandatory_cols=["order_no", "category", "period", "converted_amount_vnd"])
    check_orphans_flagged(fin_df, "financial_silver", orphan_col="is_orphaned")
    check_no_duplicates_remain(fin_df, "financial_silver", key_cols=["order_no", "category", "period"])
    check_numeric_parses_cleanly(fin_df, "financial_silver", numeric_col="amount")

    results_df = pd.DataFrame(RESULTS)
    logger.info(f"=== DQ checks complete: "
                f"{(results_df['result']=='PASSED').sum()} PASSED, "
                f"{(results_df['result']=='WARNING').sum()} WARNING, "
                f"{(results_df['result']=='FAILED').sum()} FAILED ===")
    return results_df


if __name__ == "__main__":
    results = run_dq_checks(
        kpi_silver_path=Path("kpi_actual_silver.csv"),
        financial_silver_path=Path("financial_silver.csv"),
    )
    print(results.to_string(index=False))