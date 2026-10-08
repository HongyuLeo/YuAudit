"""Collect installed distribution metadata and actual license texts for redistribution."""
import importlib.metadata as md
import json
from pathlib import Path
import shutil
import sys
import argparse
import hashlib

project = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser()
parser.add_argument("--output", type=Path, default=project / "THIRD_PARTY_LICENSES")
root = parser.parse_args().output.resolve()
root.mkdir(parents=True, exist_ok=True)
upstream = project / "licenses" / "upstream"
manifest = json.loads((upstream / "manifest.json").read_text(encoding="utf-8"))
required = {"openpyxl", "et_xmlfile", "PySide6_Essentials", "shiboken6"}
if {entry["package"] for entry in manifest} != required:
    raise RuntimeError("Required official redistribution license texts are missing")
required_files = {"openpyxl/LICENCE.rst", "et_xmlfile/LICENCE.rst", "et_xmlfile/LICENCE.python",
                  "PySide6_Essentials/LGPL-3.0-only.txt", "PySide6_Essentials/GPL-3.0-only.txt",
                  "shiboken6/LGPL-3.0-only.txt", "shiboken6/GPL-3.0-only.txt"}
if not required_files <= {entry["file"] for entry in manifest}:
    raise RuntimeError("Required LGPL/GPL/MIT/PSF license text files are missing")
for entry in manifest:
    if md.version(entry["package"]) != entry["version"]:
        raise RuntimeError(f"Refresh official license texts for {entry['package']} version")
    data = (upstream / entry["file"]).read_bytes()
    if hashlib.sha256(data).hexdigest() != entry["sha256"]:
        raise RuntimeError(f"Official license text checksum mismatch: {entry['file']}")
    destination = root / entry["package"] / "official-source" / Path(entry["file"]).name
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
shutil.copyfile(upstream / "manifest.json", root / "official-source-manifest.json")
runtime_license = Path(sys.base_prefix) / "LICENSE.txt"
if not runtime_license.is_file():
    raise RuntimeError("Python runtime LICENSE.txt is required for redistribution")
(root / "Python").mkdir(exist_ok=True)
shutil.copyfile(runtime_license, root / "Python" / "LICENSE.txt")
inventory = []
for distribution in sorted(md.distributions(), key=lambda d: d.metadata["Name"].lower()):
    name = distribution.metadata["Name"]
    entry = {"name": name, "version": distribution.version,
             "license": distribution.metadata.get("License-Expression") or distribution.metadata.get("License", ""),
             "classifiers": [v for v in distribution.metadata.get_all("Classifier", []) if "License" in v],
             "files": []}
    for file in distribution.files or []:
        if any(word in str(file).lower() for word in ("license", "copying", "notice")):
            source = Path(distribution.locate_file(file))
            if source.is_file() and source.stat().st_size < 2_000_000:
                destination = root / name / str(file).replace("../", "").replace("..\\", "")
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, destination)
                entry["files"].append(str(destination.relative_to(root)))
    for official in manifest:
        if official["package"] == name:
            entry["files"].append(str(Path(name) / "official-source" / Path(official["file"]).name))
    inventory.append(entry)
(root / "inventory.json").write_text(json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Collected {len(inventory)} dependency license inventories")
