# YuAudit v0.1.0

Initial Windows x64 release of the Local AI Document Reconciliation Studio.

## Included
- Offline desktop reconciliation of PO, Invoice and Packing List.
- Evidence-backed Decimal rules, manual mapping/corrections and partial-batch handling.
- Chinese/English, light/dark, filters, review notes, last-session recovery.
- Excel/CSV/JSON report exports and a completely fictional demo.
- Optional local Ollama suggestions; core works without any model.
- Source, tests, original icon, third-party notices and native Windows CI workflow.

## Installation
Extract the complete ZIP and run `YuAudit-Windows-x64/YuAudit.exe`. Keep `_internal` and licenses beside the executable. No developer runtime installation is needed. This release is unsigned.

## Scope
Text PDFs need ruled tables. OCR, exchange rates, credit notes, unit conversions and unrestricted free-form AI extraction are not part of this release. Preview editing covers the first 500 rows. Read README for all limits. See VERIFICATION.md for real test evidence; Windows 10 and a live Ollama model have not been tested in this environment.
