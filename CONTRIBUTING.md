# Contributing

Use Python 3.12 x64 and the development requirements. Run `python -m pytest -q` before changes are submitted. Add regression tests for matching, Decimal arithmetic, missing evidence, currencies and partial shipments. Keep UI, parsers and deterministic rules separate. Never let an AI output bypass schema validation or human approval.

Use fictional fixtures only. Do not submit business files, accounts, credentials, local profiles, model weights or logs. Avoid committing `build/` and `dist/`; attach binary artifacts to releases instead. Preserve third-party license texts when updating dependencies. Test Windows source and packaged EXE workflows in paths containing Chinese characters and spaces.
