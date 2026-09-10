# Task 2C — Dimensional Model: Order Cost Workstream

## Schema Overview

| Table | Column | Type | Key | Notes |
|---|---|---|---|---|
| **dim_date** | `date_sk` | INT | **PK** | Format `YYYYMM` |
| **dim_customer** | `customer_sk` | INT | **PK** | Surrogate key |
| | `customer_name_normalized` | VARCHAR(100) | Natural Key | Standardised name (e.g. `"Sunrise Apparel"`) |
| | `customer_id_erp` | VARCHAR(20) | | Links to ERP `userId` |
| **dim_season** | `season_sk` | INT | **PK** | `SS24`, `AW24`, `SS25` |
| **dim_drop** | `drop_sk` | INT | **PK** | `D1`, `D2`, `D3` |
| **dim_fabric_type** | `fabric_sk` | INT | **PK** | `Cotton`, `Polyester`, `Linen`, `Silk`, `Wool` |
| **dim_currency** | `currency_sk` | INT | **PK** | `USD`, `EUR`, `VND` |
| **fact_order_cost** | `order_no` | VARCHAR(10) | Composite PK | `(order_no, category, date_fk)` |
| | `category` | VARCHAR(20) | Composite PK | `fabric` / `trim` / `outsource` |
| | `date_fk` | INT | **FK → dim_date** | Composite PK |
| | `customer_fk` | INT | **FK → dim_customer** | Points to "Unknown" if orphaned |
| | `currency_fk` | INT | **FK → dim_currency** | Original transaction currency |
| | `original_amount` | DECIMAL(18,2) | | Original currency amount |
| | `converted_amount_vnd` | DECIMAL(18,2) | | FX Converted VND amount |
| | `is_orphaned` | BOOLEAN | | `True` for unlinked orders (ORD-099) |

---

## Design Decisions

1. **Handling ORD-099 Orphan Order**: Kept in the fact table with `is_orphaned = True` and linked to an `"Unknown"` customer entry to preserve total spend while excluding from customer-level rollups.
2. **`converted_amount_vnd` Location**: Calculated once at Silver using transaction-period FX rates to ensure immutable historical cost auditing.
3. **Customer Name Normalisation**: Stripped trailing spaces and uppercase-standardised strings (`"SUNRISE APPAREL"`, `"sunrise apparel "` -> `"Sunrise Apparel"`) mapped to a single `customer_sk`.