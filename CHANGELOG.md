# Changelog

## v0.1.0 - 2026-10-08
- Windows checkout fix: preserve official license bytes through Git attributes so upstream SHA-256 verification also succeeds with core.autocrlf enabled.
- Pre-release fix: block PO/invoice/SKU normalization collisions and empty normalized identifiers before matching or aggregation; preserve unambiguous normalized matches.
- Pre-release fix: redistribute official versioned openpyxl/et_xmlfile MIT/PSF and PySide6/shiboken6 LGPL/GPL license texts, with verified provenance and fail-closed collection.
- Initial offline Windows desktop release.
- CSV (UTF-8/BOM/GBK), read-only XLSX and ruled text-PDF table imports.
- Editable mapping and raw preview; field-level provenance.
- Deterministic Decimal reconciliation, evidence, partial batches and explicit uncertainty.
- Optional schema-validated loopback Ollama mapping and summary advice.
- Chinese/English UI, light/dark themes, cancellable workers, local recovery.
- Excel/CSV/JSON reports, fictional demo, automated tests and Windows packaging workflow.
- Known limitations and actual verification are documented separately.
