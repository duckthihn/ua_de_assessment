"""
Silver Financial Transformation Pipeline
Standardises dates, fixes OCR typos, normalises customer names, applies FX conversion, and flags orphans.
"""

import hashlib
import logging
import re
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("financial_silver")


def fix_wide_header_labels(df: pd.DataFrame) -> pd.DataFrame:
    """Corrects mislabeled wide file header columns."""
    df = df.rename(columns={"value": "order_no"})
    sample = df["order_no"].dropna().astype(str).iloc[0]
    if not sample.upper().startswith("ORD"):
        logger.warning("WIDE HEADER CHECK | 'order_no' column does not look like an order number after rename")
    else:
        logger.info("WIDE HEADER FIX | Mislabeled 'value' column renamed to 'order_no'")
    return df


def fix_ocr_typos(df: pd.DataFrame, col: str) -> pd.DataFrame:
    df = df.copy()
    ocr_pattern = re.compile(r"^-?[\dO]+\.?[\dO]*$")
    for idx, val in df[col].items():
        if pd.isna(val):
            continue
        s = str(val)
        if "O" in s.upper() and ocr_pattern.match(s.upper()):
            corrected = s.upper().replace("O", "0")
            logger.info(f"OCR FIX | col={col} row={idx} '{s}' -> '{corrected}'")
            df.at[idx, col] = corrected
    df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def normalise_category(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    original = df["category"].astype(str)
    cleaned = original.str.strip().str.lower()
    changed = cleaned != original
    for idx in df.index[changed]:
        logger.info(f"NORMALISE | col=category row={idx} '{original.loc[idx]}' -> '{cleaned.loc[idx]}'")
    df["category"] = cleaned
    return df


MONTH_NAME_TO_NUM = {
    "january": "01", "february": "02", "march": "03", "april": "04",
    "may": "05", "june": "06", "july": "07", "august": "08",
    "september": "09", "october": "10", "november": "11", "december": "12",
    "jan": "01", "feb": "02", "mar": "03", "apr": "04", "jun": "06",
    "jul": "07", "aug": "08", "sep": "09", "oct": "10", "nov": "11", "dec": "12",
}

def standardise_period(raw: str) -> str:
    """
    Handles all known formats seen in the source data:
      2024-01, 2024/01, January 2024, 01-2024, Feb 2024, Jan-2024, etc.
    Returns YYYY-MM, or None if the format is unrecognised (logged, not guessed).
    """
    if pd.isna(raw):
        return None
    s = str(raw).strip()

    m = re.match(r"^(\d{4})[-/](\d{2})$", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}"

    m = re.match(r"^(\d{2})[-/](\d{4})$", s)
    if m:
        return f"{m.group(2)}-{m.group(1)}"

    m = re.match(r"^([A-Za-z]+)\s+(\d{4})$", s)
    if m and m.group(1).lower() in MONTH_NAME_TO_NUM:
        return f"{m.group(2)}-{MONTH_NAME_TO_NUM[m.group(1).lower()]}"

    m = re.match(r"^([A-Za-z]+)-(\d{4})$", s)
    if m and m.group(1).lower() in MONTH_NAME_TO_NUM:
        return f"{m.group(2)}-{MONTH_NAME_TO_NUM[m.group(1).lower()]}"

    return None


def standardise_period_column(df: pd.DataFrame, col: str = "period") -> pd.DataFrame:
    df = df.copy()
    original = df[col]
    standardised = original.apply(standardise_period)
    failed = standardised.isna() & original.notna()
    for idx in df.index[failed]:
        logger.warning(f"PERIOD PARSE FAILED | row={idx} raw value='{original.loc[idx]}' "
                        f"— could not standardise, left as null for manual review")
    changed = (standardised != original) & ~failed
    for idx in df.index[changed]:
        logger.info(f"PERIOD STANDARDISED | row={idx} '{original.loc[idx]}' -> '{standardised.loc[idx]}'")
    df[col] = standardised
    return df


def normalise_customer_name(df: pd.DataFrame, col: str = "customer_name") -> pd.DataFrame:
    """
    Canonicalisation logic: strip whitespace, then title-case. This maps
    'sunrise apparel', 'SUNRISE APPAREL', 'Sunrise Apparel ' all to
    'Sunrise Apparel'. Documented risk: this is a text-normalisation
    heuristic, not an ID match — two genuinely different customers with
    similar names would incorrectly merge under this logic.
    """
    df = df.copy()
    original = df[col].astype(str)
    cleaned = original.str.strip().str.replace(r"\s+", " ", regex=True).str.title()
    changed = cleaned != original
    for idx in df.index[changed]:
        logger.info(f"CUSTOMER NORMALISE | row={idx} '{original.loc[idx]}' -> '{cleaned.loc[idx]}'")
    df[col] = cleaned
    return df


def unpivot_wide(df: pd.DataFrame) -> pd.DataFrame:
    date_cols = [c for c in df.columns if re.match(r"^\d{2}/\d{2}/\d{4}$", c)]
    id_cols = [c for c in df.columns if c not in date_cols]
    melted = df.melt(id_vars=id_cols, value_vars=date_cols, var_name="period", value_name="amount")
    melted = melted.dropna(subset=["amount"]).reset_index(drop=True)
    melted["period"] = melted["period"].apply(lambda s: f"{s.split('/')[2]}-{s.split('/')[1]}")
    return melted


def convert_to_vnd(df: pd.DataFrame, rates_df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    rate_lookup = dict(zip(rates_df["currency"], rates_df["rate_to_vnd"]))
    df["fx_rate_to_vnd"] = df["currency"].map(rate_lookup)
    missing_rate = df["fx_rate_to_vnd"].isna() & df["currency"].notna()
    for idx in df.index[missing_rate]:
        logger.warning(f"FX RATE MISSING | row={idx} currency='{df.at[idx, 'currency']}' "
                        f"— no rate found, converted_amount_vnd will be null")
    df["converted_amount_vnd"] = df["amount"] * df["fx_rate_to_vnd"]
    return df


def flag_orphans(df: pd.DataFrame, known_orphan_orders: list) -> pd.DataFrame:
    df = df.copy()
    df["is_orphaned"] = df["order_no"].isin(known_orphan_orders)
    n = int(df["is_orphaned"].sum())
    if n:
        total_vnd = df.loc[df["is_orphaned"], "converted_amount_vnd"].sum()
        logger.warning(f"ORPHAN | {n} row(s) for order(s) {known_orphan_orders} have no matching "
                        f"ERP header — flagged is_orphaned=True, NOT dropped. "
                        f"Total value at risk: {total_vnd:,.0f} VND. "
                        f"Downstream consumers should exclude these from customer-level "
                        f"rollups unless explicitly reconciled, but must include them in "
                        f"total-spend/audit reports.")
    return df


def deduplicate(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    key_cols = ["order_no", "category", "period"]
    dup_mask = df.duplicated(subset=key_cols, keep="first")
    n = int(dup_mask.sum())
    if n:
        for idx in df.index[dup_mask]:
            row = df.loc[idx]
            logger.info(f"DEDUPE | row={idx} order_no={row['order_no']} category={row['category']} "
                        f"period={row['period']} dropped as duplicate of an earlier row")
    df["is_duplicate"] = dup_mask
    return df[~dup_mask].reset_index(drop=True)


def add_audit_columns(df: pd.DataFrame, source_file: str) -> pd.DataFrame:
    df = df.copy()
    hash_cols = ["order_no", "category", "period", "amount", "currency"]

    def row_hash(row):
        payload = "|".join(str(row[c]) for c in hash_cols)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    df["row_hash"] = df.apply(row_hash, axis=1)
    df["ingestion_ts"] = pd.Timestamp.now("UTC")
    df["source_file"] = source_file
    return df


def run_financial_silver_pipeline(long_path: Path, wide_path: Path, rates_path: Path) -> pd.DataFrame:
    logger.info("=== Starting Financial File Bronze -> Silver ===")

    long_df = pd.read_csv(long_path)
    wide_raw = pd.read_csv(wide_path)
    rates_df = pd.read_csv(rates_path)
    logger.info(f"Loaded long format: {len(long_df)} rows, wide format: {len(wide_raw)} rows")

    wide_fixed = fix_wide_header_labels(wide_raw)
    wide_long = unpivot_wide(wide_fixed)
    logger.warning("WIDE FORMAT LIMITATION | financial_wide_format.csv lacks currency, "
                    "customer_name, season, drop, and fabric_type columns present in the "
                    "long format. Used only as a cross-check on order/category/period/amount.")

    df = long_df.copy()
    df = fix_ocr_typos(df, "amount")
    df = normalise_category(df)
    df = standardise_period_column(df, "period")
    df = normalise_customer_name(df, "customer_name")
    df = convert_to_vnd(df, rates_df)
    df = flag_orphans(df, known_orphan_orders=["ORD-099"])
    df = deduplicate(df)
    df = add_audit_columns(df, source_file="financial_long_format.csv")

    wide_check = wide_long.rename(columns={"amount": "amount_wide"})
    wide_check = fix_ocr_typos(wide_check, "amount_wide")
    wide_check = normalise_category(wide_check)
    cross_check = df.merge(
        wide_check[["order_no", "category", "period", "amount_wide"]],
        on=["order_no", "category", "period"], how="left"
    )
    mismatches = cross_check[
        cross_check["amount_wide"].notna() & (cross_check["amount"] != cross_check["amount_wide"])
    ]
    if len(mismatches):
        for _, row in mismatches.iterrows():
            logger.warning(f"CROSS-CHECK MISMATCH | order={row['order_no']} category={row['category']} "
                            f"period={row['period']} long={row['amount']} vs wide={row['amount_wide']}")
    else:
        logger.info("CROSS-CHECK | Long and wide formats agree on all overlapping amounts.")

    logger.info(f"=== Financial Silver complete: {len(df)} final rows ===")
    return df


if __name__ == "__main__":
    result = run_financial_silver_pipeline(
        long_path=Path("financial_long_format.csv"),
        wide_path=Path("financial_wide_format.csv"),
        rates_path=Path("exchange_rates_reference.csv"),
    )
    result.to_csv("financial_silver.csv", index=False)