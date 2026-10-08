# YuAudit — maintainer and AI handoff

Version: **0.1.0**. Updated: 2026-10-08. Project: Local AI Document Reconciliation Studio. Intended GitHub owner/repository: `HongyuLeo/YuAudit`. Publication has been authorized; authentication and remote publication must be verified before claiming success. See the actual repository and release for publication status.

## Product and operating contract

YuAudit is a Windows x64 PySide6 desktop application for offline purchase-order, commercial-invoice and packing-list reconciliation. It imports CSV (UTF-8/BOM/GBK), read-only XLSX and ruled text-table PDF, supports manual document types, column mapping and value correction, and exports evidence-backed Excel, CSV and JSON reports. The UI has Chinese/English, light/dark themes, asynchronous cancellable tasks, searchable findings, source locations, review notes, local settings/session recovery and fictional demonstration data. Source files are never modified. Core functionality needs neither a model nor a network connection.

All money and quantity checks are deterministic Decimal computations. Missing fields remain missing. AI advice is never a verified business fact. A clean result means no exceptions in the checked scope, not certification of the entire transaction. Do not weaken these contracts to produce a more reassuring result.

## Architecture and important files

| File | Responsibility |
| --- | --- |
| `launch.py`, `yuaudit/__main__.py` | Desktop entry point, language arguments and packaged end-to-end smoke mode |
| `yuaudit/ui.py` | MainWindow, QThread workers, imports/mapping/corrections, dashboard, evidence, rules, optional AI and export workflows |
| `yuaudit/models.py` | Pydantic Kind, Source, RawRow, Line, Document, Rules, Finding and Result schemas; Decimal input validation |
| `yuaudit/parsers.py` | Format and document-kind guessing, read-only extraction, row/page/bounding-box provenance, cooperative cancellation |
| `yuaudit/normalize.py` | Identifier key normalization, multilingual column aliases, mapped document structuring |
| `yuaudit/engine.py` | Independent `reconcile(documents, rules, cancel)` deterministic engine |
| `yuaudit/ai.py` | AIProvider protocol, loopback-only Ollama, redirect restrictions, schema-validated mapping and summary drafts |
| `yuaudit/storage.py` | Atomic local JSON storage, session restoration and bounded logging |
| `yuaudit/reports.py` | Atomic exports, formula-injection protection, exact decimal strings and evidence sheets |
| `yuaudit/i18n.py` | Chinese/English UI resources |
| `yuaudit/demo.py`, `demo/EXPECTED.md` | Fictional fixtures and expected exceptions, including partial batches |
| `tests/` | Parsing, deterministic engine, AI fixture, UI, integration/export and license regression tests |
| `scripts/build.ps1` | Tests, resources, license collection, PyInstaller directory build, frozen smokes and ZIP audit |
| `scripts/licenses.py` | Fail-closed version/hash-checked third-party license collection |
| `scripts/fetch_official_licenses.py`, `licenses/upstream/manifest.json` | Official version-specific license provenance and retrieval |
| `scripts/verify_package_licenses.py` | Audit actual license files inside the final ZIP |
| `.github/workflows/windows.yml` | Windows x64 CI build, tests, frozen-app launch and uploaded artifacts |
| `docs/VERIFICATION.md`, `docs/test-results.xml`, `docs/verification/` | Actual local verification evidence and screenshots |

## Matching algorithm and correctness constraints

1. Parse original cells and retain their provenance; map known or manually chosen headers into typed lines. Validate numerical input without binary floating-point arithmetic.
2. Check PO numbers, invoice numbers and SKUs for aliases that collapse to the same normalized key within each document-kind namespace, across all imported files. Conflicting original identifiers produce `ambiguous_match`; involved comparisons and aggregates are blocked. Punctuation-only identifiers normalize to empty and enter review, even if normalization is disabled. Unaffected groups can still be checked.
3. Scope item matches by explicit PO references; packing comparisons also require explicit invoice references. Use exact identifiers and then unambiguous normalized identifiers. Constrained fuzzy candidates remain suggestions requiring manual correction and rerun; they are not automatic matches.
4. Detect repeated rows and ambiguous groups before aggregating. Accumulate trustworthy batches within their PO/item scope. Partial under-deliveries stay unverified balances; over-deliveries are exceptions. Missing references or comparison values must not be reported as a pass.
5. Check quantities, unit prices, quantity-times-price line calculations, declared totals, missing/extra items, duplicate invoice identifiers and reference relationships. Missing or different currencies block financial comparison. No implicit conversion or aggregation across currencies is permitted.
6. Return typed Findings with severity, identifier, comparison values, difference where computable, rule, review advice and source evidence. Decimal uses 64-digit working precision; accepted inputs have at most 20 significant digits and 8 decimal places. Tolerances come from Rules.

The release-blocking regression was PO-1 quantity 10 plus PO1 quantity 20 at 1 USD, with invoice/packing PO-1 quantity 30. It now returns review_required and prevents the false aggregate pass. Tests cover all identifier fields, document kinds, cross-file collisions, empty keys, unaffected groups and valid unambiguous normalized matching. The frozen smoke directly reruns this reproduction.

## Run and reproduce a build

```powershell
py -3.12 -m venv .venv
.venv/Scripts/python -m pip install -r requirements-dev.txt
.venv/Scripts/python -m pytest -q
.venv/Scripts/python -m yuaudit
./scripts/build.ps1 -Python .venv/Scripts/python.exe
```

Use Windows x64 for native packaging. Build from a clean checkout; move an existing `dist/YuAudit-Windows-x64` directory aside before rebuilding. Outputs are `dist/YuAudit-Windows-x64/YuAudit.exe` and `dist/YuAudit-Windows-x64.zip`. Distribute the entire folder, including `_internal` and both third-party license directories. No user Python installation is required.

```powershell
$env:YUAUDIT_DATA_DIR = "$PWD/build/test-profile"
dist/YuAudit-Windows-x64/YuAudit.exe --smoke-test build/manual-smoke --language en
```

Normal local state is under `%LOCALAPPDATA%/YuAudit`; `YUAUDIT_DATA_DIR` isolates test profiles. Do not commit user state, imported documents, logs, secrets, environments or model weights. All committed demonstration and test data are fictional.

## Real validation results

The pre-publication fix was tested on Windows 11 Pro x64 10.0.26200, Python 3.12.14, PySide6 Essentials/shiboken6 6.8.3 and PyInstaller 6.16.0: **62 tests passed in 1.89 seconds**, and `pip check` found no broken requirements. These are recorded prior runs, not a claim that remote CI has completed.

The rebuilt real EXE passed Chinese and English UI/demo/export smokes (3 documents, 32 checks, 8 expected findings), CSV/XLSX/text-PDF parsing and the collision guard. The final ZIP was extracted to a Chinese path containing spaces and launched with PATH restricted to Windows and PYTHONHOME/PYTHONPATH cleared; that smoke passed. License auditing checked 31 packages and 180 files across two license directories. Benchmark: three 5,000-row documents, 30,000 checks, no findings, 3.905 seconds with tracemalloc and 254.61 MB peak Python allocations (not total process memory).

Required official license bodies are vendored with provenance: openpyxl 3.1.5 MIT LICENCE.rst; et_xmlfile 2.0.0 LICENCE.rst and LICENCE.python; Qt for Python v6.8.3 LGPL-3.0-only and GPL-3.0-only texts for PySide6_Essentials and shiboken6. Collection fails if required text/version/hash checks fail. Metadata license names are insufficient. Code is MIT; bundled dependencies retain their own licenses. Models are not distributed.

## Known limitations and next work

Windows 10 and a live Ollama model have not been tested; AI was exercised with a loopback HTTP fixture. GitHub Actions results must be checked after pushing. EXE is unsigned, portable only. OCR, free-form PDF, automatic tax/discount recognition, credit notes, unit conversion, FX, arbitrary spreadsheet header-row selection and full-row GUI pagination are absent. Preview editing is limited to 500 rows; up to 100,000 rows per file are checked. Supplier/date fields are extracted without independent validation. Commas mean thousands separators; Excel formulas need cached values. Cancellation is cooperative; native parsing or an AI request may take time (AI timeout 60 seconds).

Preserve regression coverage when extending matching. Priorities are usable correct comparisons, stability, UI and then extensions. To add OCR or additional providers, keep the typed extraction/evidence contract and manual confirmation boundary. If changing runtime logic or dependency versions, rerun tests, rebuild EXE, repeat both language and clean-path smokes, audit licenses and regenerate checksums.

## Publishing and release files

Only publish under `HongyuLeo/YuAudit`, after verifying the authenticated GitHub account. Inspect any existing remote history; never force-push. Release tag is `v0.1.0`. Attach `YuAudit-Windows-x64.zip`, `YuAudit-Source-v0.1.0.zip` and `SHA256SUMS.txt` to Releases; keep binary packages out of normal Git commits. Check the remote owner, commit, README files, this handoff and asset sizes/hashes after publishing. Publication is authorized by the latest user request; older local handoff statements withholding permission are superseded.

Local delivery layout: `outputs/YuAudit` contains source and the native `dist` directory; the two release ZIP files, checksums and CHATGPT_HANDOFF.md are in `outputs/`. Source ZIP excludes .git, dist, build, caches and user profiles. Exact hashes are in SHA256SUMS.txt. Do not claim upload or CI success until independently verified.
