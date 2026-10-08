# Verification record

Run date: 2026-10-08, Windows 11 Pro x64 (10.0.26200), Python 3.12.14 x64, PySide6 Essentials 6.8.3, PyInstaller 6.16.0.

| Check | Result |
|---|---|
| `pytest -q` | **62 passed** (23 additional regression / license tests) |
| CSV UTF-8 / BOM / GBK | Passed, including Chinese path and spaces |
| Read-only XLSX with two sheets | Passed; sheet/row evidence retained |
| Ruled text PDF | Passed; page/table bbox evidence retained |
| Scanned PDF | Passed expected failure; explicit OCR message |
| Decimal precision, tolerances, totals, currencies | Passed |
| Duplicate/missing/extra/fuzzy/partial/cross-document rules | Passed |
| Demo end-to-end | Passed; 3 docs, 32 checks, 8 findings, expected codes |
| Report exports | Passed; XLSX 4 sheets, CSV UTF-8 BOM, JSON evidence |
| Formula injection protection | Passed |
| Ollama schema and local endpoint guard | Passed with local HTTP fixture; no live model required |
| UI Chinese/English, light/dark, editing, search and evidence | Passed offscreen Qt tests |
| Large-file benchmark | Rerun after fix: 3×5,000 rows, 30,000 checks, 3.905 s with tracemalloc, 254.61 MB peak Python allocations |
| Dependency check | `pip check`: no broken requirements |
| Real PyInstaller EXE | Passed; directory package starts and completes UI smoke |
| Packaged format fixtures | Passed in latest build path: CSV demo plus XLSX and text-PDF fixtures are parsed inside frozen app |
| ZIP artifact | Rebuilt using `scripts/build.ps1`; Chinese/English frozen smoke and extracted ZIP smoke passed |
| Extracted ZIP, Chinese path with spaces | Passed real EXE demo/export/CSV/XLSX/PDF smoke with PATH restricted to Windows directories and PYTHONHOME/PYTHONPATH cleared |
| Original PO-1 / PO1 reproduction | Review required; ambiguity evidence retained; no cross-document aggregates performed |
| PO/invoice/SKU collisions | Passed across all 3 document kinds, including separate files; unrelated groups still checked |
| Empty normalized identifiers | Passed for PO/invoice/SKU, normalization on and off; no matching |
| Normalized matching without ambiguity | Passed for PO, invoice and SKU; preserved normal matching |
| Official license texts | 7 actual texts from versioned official sources; source archives SHA-256 verified |
| License collection failure paths | Missing LGPL, altered text and version mismatch correctly stop collection |
| Final ZIP license audit | 31 inventoried packages; 180 file checks across both license directories; 7 official texts per directory plus Python license verified |

Final rerun after the pre-release corrections: **62 passed in 1.89 s**. Both Chinese and English frozen-app smoke runs completed successfully. Each smoke run also executes the original PO-1 / PO1 collision reproduction using the packaged engine and records `identifier_collision_guard: passed`. Machine-readable smoke records, actual screenshots and exported reports are retained in `docs/verification/`; `docs/test-results.xml` contains the pytest results. The final extracted ZIP run used `build/中文 空格解压验证-20261008-183617` and a fresh `本地 数据` directory, independently of the development Python environment. Build output is retained in `docs/verification/windows-build.txt`; packaged license verification is in `docs/verification/package-audit.json`.

This record supersedes the initial 39-test build. No GitHub Release has been published. Reproduce from a clean checkout with `scripts/build.ps1 -Python .venv/Scripts/python.exe`; the script runs all tests, collects verified licenses, builds the native EXE, runs both language smokes, verifies ZIP licenses and runs the extracted Chinese-path smoke. Move any previous `dist/YuAudit-Windows-x64` folder before rebuilding. Refresh official license resources only with `scripts/fetch_official_licenses.py`, then inspect the provenance diff.

The screenshot set in `docs/screenshots/` was captured from the actual running Qt application in Chinese/English and light/dark views. It is not a mockup.

## Not performed or not claimed
- Windows 10 compatibility was not run on this host; CI workflow targets `windows-latest` and should be used for a second OS validation.
- The GitHub Actions workflow has not been run against a remote repository yet.
- Ollama was not installed; the local provider was exercised with a deterministic loopback HTTP fixture and remains optional.
- EXE is unsigned. No installer/MSIX is supplied; the deliverable is a directory ZIP as requested.
- OCR and scanned-PDF extraction were intentionally not installed or claimed.

Publication preparation rerun: 62 passed in 1.69 s; pip check passed. Public text evidence replaces the local Windows user-profile prefix with PUBLIC_BUILD_USER; test outcomes, timings and application behavior are unchanged. GitHub CI status must be verified separately.
