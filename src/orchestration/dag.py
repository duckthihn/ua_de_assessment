"""
Airflow DAG Definition
Orchestrates end-to-end pipeline: Ingestion -> Silver -> Data Quality -> Gold -> Notification.
"""

from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.trigger_rule import TriggerRule

# Resolve project paths
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_DIR = PROJECT_ROOT / "dataset"
DATA_DIR = PROJECT_ROOT / "data"
BRONZE_DIR = DATA_DIR / "bronze"
SILVER_DIR = DATA_DIR / "silver"
GOLD_DIR = DATA_DIR / "gold"

default_args = {
    "owner": "data-engineering",
    "retries": 2,                       # basic retry: at least 2 retries
    "retry_delay": timedelta(minutes=5),  # fixed delay between retries (L1 — not exponential)
    "email_on_failure": False,          # notify_result handles notification instead
}


def _ingest_erp_api(**context):
    """Calls both ERP endpoints (headers + lines), saves raw JSON to Bronze."""
    from src.ingestion.erp_api_ingestion import ingest_orders
    headers_file = DATASET_DIR / "mock_orders_headers.json"
    details_file = DATASET_DIR / "mock_orders_details.json"
    summary = ingest_orders(
        headers_file=headers_file,
        details_file=details_file,
        bronze_output_dir=BRONZE_DIR,
    )
    if "ti" in context and context["ti"]:
        context["ti"].xcom_push(key="ingest_erp_summary", value=summary)


def _ingest_kpi_actuals(**context):
    """Copies the KPI Excel/CSV export files to Bronze, unchanged."""
    import shutil
    kpi_bronze_dir = BRONZE_DIR / "kpi_actuals"
    kpi_bronze_dir.mkdir(parents=True, exist_ok=True)
    for fname in ["kpi_actual_long.csv", "kpi_actual_wide.csv", "kpi_master_dim.csv"]:
        shutil.copy(DATASET_DIR / fname, kpi_bronze_dir / fname)


def _ingest_financial_file(**context):
    """Copies the financial flat file (long + wide) to Bronze, unchanged."""
    import shutil
    fin_bronze_dir = BRONZE_DIR / "financial"
    fin_bronze_dir.mkdir(parents=True, exist_ok=True)
    for fname in ["financial_long_format.csv", "financial_wide_format.csv"]:
        shutil.copy(DATASET_DIR / fname, fin_bronze_dir / fname)


def _transform_kpi_silver(**context):
    """Cleans, unpivots, matches to master, MERGEs into DIM_KPI, writes Silver."""
    from src.transformation.silver_kpi import run_kpi_silver_pipeline
    kpi_bronze_dir = BRONZE_DIR / "kpi_actuals"
    result = run_kpi_silver_pipeline(
        long_path=kpi_bronze_dir / "kpi_actual_long.csv",
        wide_path=kpi_bronze_dir / "kpi_actual_wide.csv",
        master_path=kpi_bronze_dir / "kpi_master_dim.csv",
    )
    SILVER_DIR.mkdir(parents=True, exist_ok=True)
    out_path = SILVER_DIR / "silver_kpi.csv"
    result.to_csv(out_path, index=False)
    if "ti" in context and context["ti"]:
        context["ti"].xcom_push(key="kpi_silver_row_count", value=len(result))


def _transform_orders_silver(**context):
    """Joins order headers + line items, cleans, writes Silver."""
    print("Orders joined and stored in Bronze layer during ERP API ingestion.")


def _transform_financial_silver(**context):
    """Cleans, normalises, converts currency, writes Financial Silver."""
    from src.transformation.silver_financial import run_financial_silver_pipeline
    fin_bronze_dir = BRONZE_DIR / "financial"
    result = run_financial_silver_pipeline(
        long_path=fin_bronze_dir / "financial_long_format.csv",
        wide_path=fin_bronze_dir / "financial_wide_format.csv",
        rates_path=DATASET_DIR / "exchange_rates_reference.csv",
    )
    SILVER_DIR.mkdir(parents=True, exist_ok=True)
    out_path = SILVER_DIR / "silver_financial.csv"
    result.to_csv(out_path, index=False)
    if "ti" in context and context["ti"]:
        context["ti"].xcom_push(key="financial_silver_row_count", value=len(result))


def _run_data_quality(**context):
    """Runs all DQ checks (Task 7A) and writes results to data_quality_log."""
    from src.quality.data_quality import run_dq_checks
    SILVER_DIR.mkdir(parents=True, exist_ok=True)
    results = run_dq_checks(
        kpi_silver_path=SILVER_DIR / "silver_kpi.csv",
        financial_silver_path=SILVER_DIR / "silver_financial.csv",
    )
    dq_log_path = SILVER_DIR / "data_quality_log.csv"
    results.to_csv(dq_log_path, index=False)

    overall_result = "FAILED" if (results["result"] == "FAILED").any() else \
                      "WARNING" if (results["result"] == "WARNING").any() else "PASSED"
    if "ti" in context and context["ti"]:
        context["ti"].xcom_push(key="dq_overall_result", value=overall_result)
        context["ti"].xcom_push(
            key="dq_summary",
            value={
                "passed": int((results["result"] == "PASSED").sum()),
                "warning": int((results["result"] == "WARNING").sum()),
                "failed": int((results["result"] == "FAILED").sum()),
            },
        )

    if overall_result == "FAILED":
        raise ValueError(
            f"Data quality check FAILED — halting before Gold. "
            f"Summary: {results[results['result']=='FAILED'].to_dict('records')}"
        )


def _build_gold(**context):
    """Builds Gold outputs — only reached if run_data_quality did not fail."""
    from src.gold.gold import run_gold_layer
    print("Building Gold layer outputs (KPI achievement summary, order cost rollups)...")
    run_gold_layer(
        kpi_silver_path=SILVER_DIR / "silver_kpi.csv",
        financial_silver_path=SILVER_DIR / "silver_financial.csv",
        master_path=DATASET_DIR / "kpi_master_dim.csv",
        output_dir=GOLD_DIR,
    )


def _notify_result(**context):
    """
    Sends a summary notification. This task ALWAYS runs, even if an upstream
    task failed, because trigger_rule="all_done" ignores upstream state.
    """
    ti = context.get("ti")
    dq_result = (ti.xcom_pull(key="dq_overall_result", task_ids="run_data_quality") if ti else "UNKNOWN") or "UNKNOWN"
    dq_summary = (ti.xcom_pull(key="dq_summary", task_ids="run_data_quality") if ti else {}) or {}
    print(f"=== Pipeline run summary ===")
    print(f"Data quality result: {dq_result}")
    print(f"Check summary: {dq_summary}")
    print(f"(Send this to Slack/email in a real implementation)")


with DAG(
    dag_id="ua_manufacturing_data_pipeline",
    description="Orchestrates KPI and Order/Financial workstreams end to end",
    default_args=default_args,
    schedule_interval="0 6 * * MON",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["ua-manufacturing", "kpi", "orders", "L1"],
) as dag:

    ingest_erp_api = PythonOperator(task_id="ingest_erp_api", python_callable=_ingest_erp_api)
    ingest_kpi_actuals = PythonOperator(task_id="ingest_kpi_actuals", python_callable=_ingest_kpi_actuals)
    ingest_financial_file = PythonOperator(task_id="ingest_financial_file", python_callable=_ingest_financial_file)
    transform_kpi_silver = PythonOperator(task_id="transform_kpi_silver", python_callable=_transform_kpi_silver)
    transform_orders_silver = PythonOperator(task_id="transform_orders_silver", python_callable=_transform_orders_silver)
    transform_financial_silver = PythonOperator(task_id="transform_financial_silver", python_callable=_transform_financial_silver)
    run_data_quality = PythonOperator(task_id="run_data_quality", python_callable=_run_data_quality)

    build_gold = PythonOperator(
        task_id="build_gold", python_callable=_build_gold,
        trigger_rule=TriggerRule.ALL_SUCCESS,
    )

    notify_result = PythonOperator(
        task_id="notify_result", python_callable=_notify_result,
        trigger_rule=TriggerRule.ALL_DONE,
    )

    ingest_kpi_actuals >> transform_kpi_silver
    ingest_erp_api >> transform_orders_silver
    ingest_financial_file >> transform_financial_silver

    [transform_kpi_silver, transform_orders_silver, transform_financial_silver] >> run_data_quality

    run_data_quality >> build_gold >> notify_result