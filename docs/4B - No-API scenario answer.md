# Task 4B — "The ERP Has No API" Scenario

**Scenario:** Data exists only inside a web application with no export button, no database access, and vendor refuses to build an API. Data is needed weekly.

## Ingestion Options Comparison

| Option | Technical Risk | Business Risk | Maintenance Cost |
|---|---|---|---|
| **Web Scraping** (Browser automation) | Page layout changes break HTML selectors | Terms of service compliance | High (selector maintenance) |
| **Manual Export + Shared Folder** | Low technical risk, high human error | Dependent on single person | Medium (ongoing labor) |
| **RPA Tool** (UiPath / Automation Anywhere) | UI fragility | Licensing cost | Medium |
| **Vendor Scheduled Report / DB Export** | Dependent on vendor cooperation | Extra vendor fees | Low (once setup) |
| **OCR Screen Scraping** | High OCR misread rate | Risk of wrong numbers in reports | High |

## Recommendation
Implement **Web Scraping** as a temporary bridge with DOM change monitoring and alerts. In parallel, request commercial management to negotiate a scheduled SFTP/email export with the vendor.

## Business Alignment
Align with vendor relationship owner, business user, and IT/legal to confirm legal compliance and agree on SLA alert thresholds if layout breakage occurs.

## Migration Strategy (when API is delivered 6 months later)
Run the vendor API and web scraper **in parallel for 4 weeks** with automated output reconciliation. Deprecate the scraper once zero-delta is verified without altering Silver/Gold models.