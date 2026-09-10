"""
Silver KPI Transformation Pipeline
Cleans OCR typos, normalises categoricals, unpivots long/wide formats, and matches against KPI master dimension.
"""

import hashlib
import logging
import re
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("kpi_silver")

CATEGORICAL_COLS = ["Pillar", "Sub_Pillar", "Department", "KPI_Name", "Sub_KPI_Type", "Unit"]
NATURAL_KEY_COLS = ["Pillar", "Sub_Pillar", "Department", "KPI_Name", "Sub_KPI_Type"]

def fix_ocr_typos(df: pd.DataFrame, value_cols: list, row_id_col: str = None) -> pd.DataFrame:
    """Replaces letter 'O' with '0' in numeric columns."""
    fix_log = []
    df = df.copy()
    ocr_pattern = re.compile(r"^-?[\dO]+\.?[\dO]*$")

    for col in value_cols:
        for idx, val in df[col].items():
            if pd.isna(val):
                continue
            s = str(val)
            if "O" in s.upper() and ocr_pattern.match(s.upper()):
                corrected = s.upper().replace("O", "0")
                fix_log.append({
                    "row_index": idx, "column": col,
                    "original_value": s, "corrected_value": corrected,
                })
                df.at[idx, col] = corrected

    if fix_log:
        for entry in fix_log:
            logger.info(f"OCR FIX | col={entry['column']} row={entry['row_index']} "
                        f"'{entry['original_value']}' -> '{entry['corrected_value']}'")
    else:
        logger.info("OCR FIX | No OCR typos (letter O in numeric fields) found in this batch.")
    return df


def normalise_categoricals(df: pd.DataFrame, columns: list) -> pd.DataFrame:
    """Strips leading/trailing whitespace from categorical columns."""
    df = df.copy()
    change_count = 0
    for col in columns:
        is_null = df[col].isna()
        original = df[col]
        cleaned = original.where(is_null, original.astype(str).str.strip().str.replace(r"\s+", " ", regex=True))
        changed_mask = (~is_null) & (cleaned.astype(str) != original.astype(str))
        n_changed = int(changed_mask.sum())
        if n_changed:
            change_count += n_changed
            for idx in df.index[changed_mask]:
                logger.info(f"NORMALISE | col={col} row={idx} "
                            f"'{original.loc[idx]}' -> '{cleaned.loc[idx]}'")
        df[col] = cleaned
    logger.info(f"NORMALISE | Total categorical values cleaned: {change_count}")
    return df


def deduplicate_raw_rows(df: pd.DataFrame, source_file: str) -> pd.DataFrame:
    """
    Drops exact duplicate rows that only became identical AFTER whitespace/
    casing normalisation (e.g. ' Revenue' vs 'Revenue' rows that otherwise
    have identical data). Logs which rows were dropped and why.
    """
    df = df.copy()
    dup_mask = df.duplicated(keep="first")
    n_dupes = int(dup_mask.sum())
    if n_dupes:
        for idx in df.index[dup_mask]:
            logger.info(f"DEDUPE (raw) | source={source_file} row={idx} dropped — "
                        f"became an exact duplicate of an earlier row after whitespace/casing cleanup")
    else:
        logger.info(f"DEDUPE (raw) | source={source_file} — no exact duplicate rows found")
    return df[~dup_mask].reset_index(drop=True)


MONTH_MAP = {f"M{i}": f"2024-{i:02d}" for i in range(1, 13)}

def unpivot_wide(df: pd.DataFrame, source_file: str) -> pd.DataFrame:
    month_cols = ["Jan-24", "Feb-24", "Mar-24", "Apr-24", "May-24", "Jun-24",
                  "Jul-24", "Aug-24", "Sep-24", "Oct-24", "Nov-24", "Dec-24"]
    id_cols = [c for c in df.columns if c not in month_cols]
    melted = df.melt(id_vars=id_cols, value_vars=month_cols,
                      var_name="_raw_period", value_name="actual_value")
    period_map = {
        "Jan-24": "2024-01", "Feb-24": "2024-02", "Mar-24": "2024-03", "Apr-24": "2024-04",
        "May-24": "2024-05", "Jun-24": "2024-06", "Jul-24": "2024-07", "Aug-24": "2024-08",
        "Sep-24": "2024-09", "Oct-24": "2024-10", "Nov-24": "2024-11", "Dec-24": "2024-12",
    }
    melted["PERIOD"] = melted["_raw_period"].map(period_map)
    melted = melted.drop(columns="_raw_period")
    melted["SOURCE_FILE"] = source_file
    return melted


def unpivot_long(df: pd.DataFrame, source_file: str) -> pd.DataFrame:
    month_cols = [f"M{i}" for i in range(1, 13)]
    id_cols = [c for c in df.columns if c not in month_cols]
    melted = df.melt(id_vars=id_cols, value_vars=month_cols,
                      var_name="_raw_period", value_name="actual_value")
    melted["PERIOD"] = melted["_raw_period"].map(MONTH_MAP)
    melted = melted.drop(columns="_raw_period")
    melted["SOURCE_FILE"] = source_file
    return melted


def reconcile_sources(long_df: pd.DataFrame, wide_df: pd.DataFrame) -> pd.DataFrame:
    """
    Both files describe the same underlying KPI actuals — long and wide are
    two exports of the same data, not two different datasets. Reconciliation
    strategy:
      1. Clean + unpivot both independently (already done before this call).
      2. Group by the natural key + PERIOD.
      3. If both sources agree on actual_value -> keep one row.
      4. If they disagree -> flag as a CONFLICT and keep the wide-format
         value as primary (treated as the more reviewed export), but log
         the conflict so someone can verify manually.
      5. If a natural key + PERIOD appears in only one source -> keep it.
    """
    key_cols = NATURAL_KEY_COLS + ["PERIOD"]

    combined = pd.concat([long_df.assign(_priority=2), wide_df.assign(_priority=1)],
                          ignore_index=True)

    conflicts = []
    result_rows = []

    for key, group in combined.groupby(key_cols, dropna=False):
        distinct_values = group["actual_value"].dropna().unique()
        if len(distinct_values) > 1:
            conflicts.append({"key": key, "values": list(distinct_values)})
        chosen = group.sort_values("_priority").iloc[0]
        result_rows.append(chosen)

    result = pd.DataFrame(result_rows).drop(columns="_priority").reset_index(drop=True)

    if conflicts:
        for c in conflicts:
            logger.warning(f"RECONCILE CONFLICT | key={c['key']} "
                            f"conflicting values={c['values']} -> kept wide-format value")
    else:
        logger.info("RECONCILE | No conflicts found between long and wide sources — "
                    "both formats agree on every matching record.")

    logger.info(f"RECONCILE | {len(result)} unified rows after merging long+wide sources "
                f"({len(conflicts)} conflicts resolved in favour of wide format)")
    return result


def deduplicate(df: pd.DataFrame) -> pd.DataFrame:
    key_cols = NATURAL_KEY_COLS + ["PERIOD"]
    df = df.copy()
    dup_mask = df.duplicated(subset=key_cols, keep="first")
    n_dupes = int(dup_mask.sum())
    if n_dupes:
        dropped = df[dup_mask]
        for idx, row in dropped.iterrows():
            logger.info(f"DEDUPE | Dropped duplicate row index={idx} "
                        f"key={tuple(row[k] for k in key_cols)}")
    else:
        logger.info("DEDUPE | No duplicate rows found after reconciliation.")
    df["IS_DUPLICATE"] = dup_mask
    return df[~dup_mask].reset_index(drop=True)


def match_to_master(df: pd.DataFrame, master_df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["Sub_KPI_Type"] = df["Sub_KPI_Type"].fillna("").replace("", "ALL")
    master_df = master_df.copy()
    master_df["Sub_KPI_Type"] = master_df["Sub_KPI_Type"].fillna("").replace("", "ALL")
    active_master = master_df[master_df["Is_Active"] == "Y"]

    merged = df.merge(
        active_master[NATURAL_KEY_COLS + ["UA_ID"]],
        on=NATURAL_KEY_COLS, how="left",
    )
    merged["IS_ORPHANED"] = merged["UA_ID"].isna()
    n_orphaned = int(merged["IS_ORPHANED"].sum())
    if n_orphaned:
        orphan_keys = merged.loc[merged["IS_ORPHANED"], NATURAL_KEY_COLS].drop_duplicates()
        for _, row in orphan_keys.iterrows():
            logger.warning(f"ORPHAN | No active master match for "
                            f"{dict(zip(NATURAL_KEY_COLS, row.tolist()))}")
    logger.info(f"MATCH | {len(merged) - n_orphaned} records matched to master, "
                f"{n_orphaned} flagged as orphaned")
    return merged


def add_audit_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    hash_cols = NATURAL_KEY_COLS + ["PERIOD", "actual_value", "Target", "Unit"]

    def row_hash(row):
        payload = "|".join(str(row[c]) for c in hash_cols)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    df["ROW_HASH"] = df.apply(row_hash, axis=1)
    df["INGESTION_TS"] = pd.Timestamp.now("UTC")
    return df


def run_kpi_silver_pipeline(long_path: Path, wide_path: Path, master_path: Path) -> pd.DataFrame:
    logger.info("=== Starting KPI Actuals Bronze -> Silver ===")

    long_df = pd.read_csv(long_path)
    wide_df = pd.read_csv(wide_path)
    master_df = pd.read_csv(master_path)
    logger.info(f"Loaded long format: {len(long_df)} rows, wide format: {len(wide_df)} rows")

    long_df = normalise_categoricals(long_df, CATEGORICAL_COLS)
    wide_df = normalise_categoricals(wide_df, CATEGORICAL_COLS)

    long_df = deduplicate_raw_rows(long_df, "kpi_actual_long.csv")
    wide_df = deduplicate_raw_rows(wide_df, "kpi_actual_wide.csv")

    long_unpivoted = unpivot_long(long_df, source_file="kpi_actual_long.csv")
    wide_unpivoted = unpivot_wide(wide_df, source_file="kpi_actual_wide.csv")

    long_unpivoted = fix_ocr_typos(long_unpivoted, ["actual_value", "Target"])
    wide_unpivoted = fix_ocr_typos(wide_unpivoted, ["actual_value", "Target"])

    long_unpivoted["actual_value"] = pd.to_numeric(long_unpivoted["actual_value"], errors="coerce")
    wide_unpivoted["actual_value"] = pd.to_numeric(wide_unpivoted["actual_value"], errors="coerce")

    unified = reconcile_sources(long_unpivoted, wide_unpivoted)
    unified = deduplicate(unified)
    unified = match_to_master(unified, master_df)
    unified = add_audit_columns(unified)

    logger.info(f"=== KPI Silver complete: {len(unified)} final rows ===")
    return unified


if __name__ == "__main__":
    result = run_kpi_silver_pipeline(
        long_path=Path("kpi_actual_long.csv"),
        wide_path=Path("kpi_actual_wide.csv"),
        master_path=Path("kpi_master_dim.csv"),
    )
    result.to_csv("kpi_actual_silver.csv", index=False)