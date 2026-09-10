# Task 5B — Financial Silver Transformation

**Source Code:** [`src/transformation/silver_financial.py`](file:///home/duckthihn/ua_de_assessment/src/transformation/silver_financial.py)

## Data Cleansing & Transformation Summary

| Issue / Step | Action Taken | Result |
|---|---|---|
| **OCR Typos** | Replaced letter 'O' with '0' in amounts | 6 OCR typos corrected |
| **Category Normalisation** | Lowercased & trimmed spaces | 11 categories cleaned (`fabric`/`trim`/`outsource`) |
| **Period Standardisation** | Parsed mixed date formats into `YYYY-MM` | Standardised all date formats (`2024-01`...`2024-12`) |
| **Customer Normalisation** | Mapped variants to canonical names | 16 names cleaned (e.g. *Sunrise Apparel*) |
| **Orphan Handling** | Flagged `ORD-099` (`is_orphaned=True`) | Retained 2 orphan rows (~161.2M VND) |
| **Deduplication** | Dropped duplicate order-category-period rows | 2 duplicates dropped (`ORD-005`, `ORD-008`) |
| **FX Conversion** | Converted USD/EUR/VND to VND | 100% amounts converted |
| **Header Fix** | Mislabeled `"value"` column renamed to `"order_no"` | Fixed wide format header |

## Cross-Verification Strategy
Wide format data is unpivoted and used to cross-verify amounts against long format records before final Silver dataset persistence (31 final rows).