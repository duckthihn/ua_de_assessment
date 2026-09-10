"""Main Execution Script - End-to-End ELT Pipeline
Orchestrates pipeline stages: Bronze Ingestion -> Silver Transformation -> Data Quality -> Gold Aggregations.
"""

import shutil
import sys
from pathlib import Path
import pandas as pd

# Add project root to python path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ingestion.erp_api_ingestion import ingest_orders
from src.transformation.silver_kpi import run_kpi_silver_pipeline
from src.transformation.silver_financial import run_financial_silver_pipeline
from src.quality.data_quality import run_dq_checks
from src.gold.gold import run_gold_layer


def print_banner(title: str) -> None:
    print("\n" + "=" * 70)
    print(f" {title.upper()}")
    print("=" * 70)


def run_pipeline() -> int:
    print_banner("UA Manufacturing Data Pipeline (L1 Batch ELT)")
    print(f"Project Root: {PROJECT_ROOT}")
    
    dataset_dir = PROJECT_ROOT / "dataset"
    bronze_dir = PROJECT_ROOT / "data" / "bronze"
    silver_dir = PROJECT_ROOT / "data" / "silver"
    gold_dir = PROJECT_ROOT / "data" / "gold"
    
    # Ensure all directories exist
    bronze_dir.mkdir(parents=True, exist_ok=True)
    silver_dir.mkdir(parents=True, exist_ok=True)
    gold_dir.mkdir(parents=True, exist_ok=True)
    
    # -------------------------------------------------------------
    # STAGE 1: BRONZE INGESTION
    # -------------------------------------------------------------
    print_banner("Stage 1: Bronze Ingestion")
    
    # 1A: ERP API Ingestion
    erp_headers_file = dataset_dir / "mock_orders_headers.json"
    erp_details_file = dataset_dir / "mock_orders_details.json"
    
    erp_stats = ingest_orders(
        headers_file=erp_headers_file,
        details_file=erp_details_file,
        bronze_output_dir=bronze_dir
    )
    print("✓ ERP API Ingestion Stats:")
    for k, v in erp_stats.items():
        print(f"  - {k}: {v}")

    # 1B: Copy KPI Raw Files to Bronze
    kpi_bronze_dir = bronze_dir / "kpi_actuals"
    kpi_bronze_dir.mkdir(parents=True, exist_ok=True)
    kpi_files = ["kpi_actual_long.csv", "kpi_actual_wide.csv", "kpi_master_dim.csv"]
    for fname in kpi_files:
        shutil.copy(dataset_dir / fname, kpi_bronze_dir / fname)
        shutil.copy(dataset_dir / fname, bronze_dir / fname)
    print(f"✓ Copied {len(kpi_files)} KPI raw files to Bronze ({kpi_bronze_dir})")

    # 1C: Copy Financial Raw Files to Bronze
    fin_bronze_dir = bronze_dir / "financial"
    fin_bronze_dir.mkdir(parents=True, exist_ok=True)
    fin_files = ["financial_long_format.csv", "financial_wide_format.csv", "exchange_rates_reference.csv"]
    for fname in fin_files:
        shutil.copy(dataset_dir / fname, fin_bronze_dir / fname)
        shutil.copy(dataset_dir / fname, bronze_dir / fname)
    print(f"✓ Copied {len(fin_files)} Financial raw files to Bronze ({fin_bronze_dir})")

    # -------------------------------------------------------------
    # STAGE 2: SILVER TRANSFORMATIONS
    # -------------------------------------------------------------
    print_banner("Stage 2: Silver Transformations")
    
    # 2A: Silver KPI Pipeline
    print("Executing Silver KPI Pipeline...")
    kpi_long_file = kpi_bronze_dir / "kpi_actual_long.csv"
    kpi_wide_file = kpi_bronze_dir / "kpi_actual_wide.csv"
    kpi_master_file = kpi_bronze_dir / "kpi_master_dim.csv"
    
    kpi_silver_df = run_kpi_silver_pipeline(
        long_path=kpi_long_file,
        wide_path=kpi_wide_file,
        master_path=kpi_master_file
    )
    silver_kpi_path = silver_dir / "silver_kpi.csv"
    kpi_silver_df.to_csv(silver_kpi_path, index=False)
    print(f"✓ Saved Silver KPI dataset to {silver_kpi_path} ({len(kpi_silver_df)} rows)")
    
    # 2B: Silver Financial Pipeline
    print("\nExecuting Silver Financial Pipeline...")
    fin_long_file = fin_bronze_dir / "financial_long_format.csv"
    fin_wide_file = fin_bronze_dir / "financial_wide_format.csv"
    fx_rates_file = fin_bronze_dir / "exchange_rates_reference.csv"
    
    fin_silver_df = run_financial_silver_pipeline(
        long_path=fin_long_file,
        wide_path=fin_wide_file,
        rates_path=fx_rates_file
    )
    silver_fin_path = silver_dir / "silver_financial.csv"
    fin_silver_df.to_csv(silver_fin_path, index=False)
    print(f"✓ Saved Silver Financial dataset to {silver_fin_path} ({len(fin_silver_df)} rows)")

    # -------------------------------------------------------------
    # STAGE 3: DATA QUALITY FRAMEWORK
    # -------------------------------------------------------------
    print_banner("Stage 3: Data Quality Evaluation")
    dq_log_df = run_dq_checks(
        kpi_silver_path=silver_kpi_path,
        financial_silver_path=silver_fin_path
    )
    
    dq_log_path = silver_dir / "data_quality_log.csv"
    dq_log_df.to_csv(dq_log_path, index=False)
    print(f"✓ Saved Data Quality Audit Log to {dq_log_path}")
    
    print("\nData Quality Check Summary:")
    for _, row in dq_log_df.iterrows():
        status_symbol = "✓" if row["result"] == "PASSED" else ("⚠" if row["result"] == "WARNING" else "✗")
        print(f"  [{status_symbol} {row['result']}] {row['table_name']} -> {row['check_name']}: {row['details']}")
        
    critical_failure = (dq_log_df["result"] == "FAILED").any()
    if critical_failure:
        print("\n⛔ CRITICAL QUALITY FAILURE DETECTED! Gating triggered: Halting before Gold Layer.")
        return 1
    else:
        print("\n✓ Quality Gating Passed (All checks PASSED or WARNING). Proceeding to Gold Layer.")

    # -------------------------------------------------------------
    # STAGE 4: GOLD AGGREGATIONS
    # -------------------------------------------------------------
    print_banner("Stage 4: Gold Layer Aggregations")
    achievement_summary, pillar_rollup, order_cost_summary, ytd_actuals = run_gold_layer(
        kpi_silver_path=silver_kpi_path,
        financial_silver_path=silver_fin_path,
        master_path=kpi_master_file,
        output_dir=gold_dir
    )
    
    print(f"✓ Built kpi_monthly_achievement_summary.csv ({len(achievement_summary)} rows)")
    print(f"✓ Built pillar_monthly_rollup.csv ({len(pillar_rollup)} rows)")
    print(f"✓ Built order_cost_summary.csv ({len(order_cost_summary)} rows)")
    print(f"✓ Built ytd_kpi_actuals.csv ({len(ytd_actuals)} rows)")

    print_banner("Pipeline Completed Successfully")
    return 0


if __name__ == "__main__":
    exit_code = run_pipeline()
    sys.exit(exit_code)


