# Task 4A — ERP API Ingestion Script

**Source Code:** [`src/ingestion/erp_api_ingestion.py`](file:///home/duckthihn/ua_de_assessment/src/ingestion/erp_api_ingestion.py)

## Architecture & Transport Abstraction
- **ApiClient Abstraction**: All source reading lives inside `ApiClient.fetch()`. Transitioning from mock JSON files to live HTTP calls requires changing only the inner execution of `fetch()`.
- **Bearer Token Auth**: `ApiConfig.auth_headers()` acts as a single point for authentication headers (`Authorization: Bearer <token>`).

## Error Handling Matrix

| Edge Case | Action Taken |
|---|---|
| Missing file / Connection error | Logged as error; returns empty list without crashing. |
| Empty response | Logged as error; pipeline continues. |
| Malformed JSON | Logged with JSONDecodeError details; skips batch and continues. |
| Orphaned line items | Logged as warning; retained for audit. |

## Failure Test Verification
1. **Clean Run**: Ingested 10 headers and 50 line items successfully.
2. **Corrupted File Test**: Introduced syntax error into `mock_orders_details.json`. The script logged the malformed JSON error and safely processed headers.
3. **Recovery**: Restored file; ingestion succeeded completely on next run.