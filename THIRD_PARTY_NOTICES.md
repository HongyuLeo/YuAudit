# Third-party notices

YuAudit application code: MIT. Dependencies are distributed under their own terms, not relicensed as MIT. `scripts/licenses.py` collects installed versions, license metadata and bundled license/notice files into `THIRD_PARTY_LICENSES/inventory.json` and per-package folders. That directory is included beside the EXE and inside its data directory.

The wheel metadata omits some license texts. `licenses/upstream/` therefore contains the actual openpyxl 3.1.5 and et_xmlfile 2.0.0 texts extracted from their official PyPI source distributions, including et_xmlfile's Python license. PySide6 Essentials / shiboken6 6.8.3 receive the LGPL v3 and accompanying GPL v3 texts from the official Qt for Python `v6.8.3` source tag. `manifest.json` records URLs, source archive members and SHA-256 values. `scripts/fetch_official_licenses.py` refreshes these developer resources; normal builds use them offline, verify versions/hashes and fail if required texts are missing. Package metadata names alone are not accepted as proof of these licenses. The same source manifest is redistributed with the EXE.

## Compatibility review
- **PySide6 / shiboken6 / Qt 6**: LGPL-3.0 / GPL alternatives or commercial licenses; this distribution uses the LGPL option for the required Qt Core/Gui/Widgets components. Dynamic Qt DLLs remain separate and replaceable. No static Qt linking or GPL-only Qt modules are intentionally used. Application source and build instructions are supplied. Qt LGPL notices, copyright and component licenses must remain. Qt sources: https://code.qt.io/cgit/qt/ ; PySide sources: https://code.qt.io/cgit/pyside/pyside-setup.git/ (tag v6.8.3). Users may modify/replace LGPL libraries and reverse-engineer for debugging such modifications; the application adds no restriction on those rights.
- **Python 3.12 runtime**: PSF license, including its bundled third-party notices.
- **openpyxl**: MIT; **et_xmlfile**: MIT.
- **pdfplumber / pdfminer.six**: MIT.
- **pypdfium2**: Apache-2.0 or BSD-3-Clause; PDFium carries BSD and additional third-party notices distributed by its wheel. Preserve all supplied notices.
- **Pydantic / pydantic-core / annotated-types / typing-inspection**: MIT; **typing_extensions**: PSF-2.0.
- **cryptography**: Apache-2.0 or BSD-3-Clause; wheel may include OpenSSL and Rust notices. **cffi**: MIT; **pycparser**: BSD-3-Clause.
- Build/test tools **PyInstaller**: GPL-2.0-or-later with bootloader exception allowing commercial/non-GPL bundled applications; **pyinstaller-hooks-contrib**: Apache-2.0 / GPL-2.0 with exception; **altgraph**: MIT; **pefile**: MIT; **pywin32-ctypes**: BSD-3-Clause; **setuptools**: MIT; **pytest**: MIT; **Pillow**: HPND; **ReportLab**: BSD; supporting test packages retain their generated inventory licenses.

These licenses permit the planned open-source distribution with their notices and LGPL dynamic-library obligations retained. License metadata alone is not a replacement for actual texts; use the collected texts. No model weights, OCR engine or proprietary assets are bundled. The icon is original code-generated artwork.
