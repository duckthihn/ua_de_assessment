"""
ERP Order Data Ingestion (Bronze Layer)
Ingests order headers and order details, applies field mapping, and saves raw JSON to Bronze.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# --------------------------------------------------------------------------
# Logging setup — every step is logged: what was called, how many records
# came back, and any errors encountered.
# --------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("erp_ingestion")


class ApiError(Exception):
    """Raised for any failure calling an endpoint — connection issue,
    empty response, bad status, or malformed JSON."""


# API Configuration
@dataclass
class ApiConfig:
    base_url: str = "https://erp.ua-manufacturing.example/api"
    auth_token: Optional[str] = None
    timeout_seconds: float = 10.0

    def auth_headers(self) -> dict:
        if self.auth_token:
            return {"Authorization": f"Bearer {self.auth_token}"}
        return {}


class ApiClient:
    def __init__(self, config: ApiConfig):
        self.config = config

    def fetch(self, endpoint_path: str, mock_file: Path) -> list:
        """Fetches data from mock JSON file (simulating GET endpoint)."""
        logger.info(f"Calling GET {self.config.base_url}{endpoint_path} "
                    f"headers={self.config.auth_headers()}")

        if not mock_file.exists():
            raise ApiError(f"Could not reach endpoint (file not found): {mock_file}")

        raw_text = mock_file.read_text(encoding="utf-8")

        if not raw_text.strip():
            raise ApiError(f"Empty response from {endpoint_path}")

        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as e:
            raise ApiError(f"Malformed JSON from {endpoint_path}: {e}")

        if not isinstance(data, list):
            raise ApiError(f"Unexpected response shape from {endpoint_path}")

        return data


# --------------------------------------------------------------------------
# Field mapping — source field names -> Bronze/target field names
# --------------------------------------------------------------------------
HEADER_FIELD_MAP = {
    "id": "order_id",
    "userId": "customer_id",
    "title": "order_code",
    "body": "order_notes",
}

DETAIL_FIELD_MAP = {
    "id": "line_id",
    "postId": "order_id",
    "name": "line_description",
    "email": "buyer_contact",
    "body": "line_notes",
}


def remap_fields(record: dict, field_map: dict) -> dict:
    return {field_map.get(k, k): v for k, v in record.items()}


def add_ingestion_metadata(record: dict, source_file: str) -> dict:
    record = dict(record)
    record["ingestion_timestamp"] = datetime.now(timezone.utc).isoformat()
    record["source_file"] = source_file
    return record


# --------------------------------------------------------------------------
# Main ingestion pipeline
# --------------------------------------------------------------------------
def ingest_orders(headers_file: Path, details_file: Path, bronze_output_dir: Path) -> dict:
    config = ApiConfig()  # auth_token=None today; set in production via env var
    client = ApiClient(config)

    logger.info("=== Starting ERP order ingestion ===")

    # --- Fetch headers ---
    try:
        raw_headers = client.fetch("/orders/headers", headers_file)
        logger.info(f"Received {len(raw_headers)} records from /orders/headers")
    except ApiError as e:
        logger.error(f"Failed to ingest order headers: {e}")
        raw_headers = []

    # --- Fetch details (line items) ---
    try:
        raw_details = client.fetch("/orders/lines", details_file)
        logger.info(f"Received {len(raw_details)} records from /orders/lines")
    except ApiError as e:
        logger.error(f"Failed to ingest order lines: {e}")
        raw_details = []

    # --- Remap fields + add ingestion metadata (Bronze layer requirement) ---
    headers_clean = [
        add_ingestion_metadata(remap_fields(r, HEADER_FIELD_MAP), headers_file.name)
        for r in raw_headers
    ]
    details_clean = [
        add_ingestion_metadata(remap_fields(r, DETAIL_FIELD_MAP), details_file.name)
        for r in raw_details
    ]

    # --- Save raw (remapped + timestamped) responses to Bronze ---
    bronze_output_dir.mkdir(parents=True, exist_ok=True)
    headers_out = bronze_output_dir / "order_headers_bronze.json"
    details_out = bronze_output_dir / "order_lines_bronze.json"
    headers_out.write_text(json.dumps(headers_clean, indent=2), encoding="utf-8")
    details_out.write_text(json.dumps(details_clean, indent=2), encoding="utf-8")
    logger.info(f"Wrote {len(headers_clean)} header records to {headers_out}")
    logger.info(f"Wrote {len(details_clean)} line-item records to {details_out}")

    # --- Join headers to their line items (one order -> list of line items) ---
    lines_by_order = {}
    for line in details_clean:
        lines_by_order.setdefault(line["order_id"], []).append(line)

    joined_orders = []
    orphan_line_count = 0
    for header in headers_clean:
        order_id = header["order_id"]
        order_lines = lines_by_order.pop(order_id, [])
        joined_orders.append({**header, "line_items": order_lines})

    # Any line items left in lines_by_order reference an order_id with no header
    for order_id, orphan_lines in lines_by_order.items():
        orphan_line_count += len(orphan_lines)
        logger.warning(f"{len(orphan_lines)} line item(s) reference unknown order_id "
                        f"'{order_id}' — no matching header found")

    logger.info(f"Joined {len(joined_orders)} orders to their line items "
                f"({orphan_line_count} orphaned line items found)")

    summary = {
        "headers_ingested": len(headers_clean),
        "lines_ingested": len(details_clean),
        "orders_joined": len(joined_orders),
        "orphan_line_items": orphan_line_count,
    }
    logger.info(f"=== Ingestion complete: {summary} ===")
    return summary


if __name__ == "__main__":
    ingest_orders(
        headers_file=Path("mock_orders_headers.json"),
        details_file=Path("mock_orders_details.json"),
        bronze_output_dir=Path("data/bronze"),
    )