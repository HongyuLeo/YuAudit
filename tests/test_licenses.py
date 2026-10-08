"""Redistribution must contain actual, versioned and checksum-verified texts."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import pytest

ROOT = Path(__file__).resolve().parent.parent


def test_license_collection_contains_official_texts(tmp_path):
    destination = tmp_path / "许可证 空格"
    subprocess.run([sys.executable, str(ROOT / "scripts/licenses.py"), "--output", str(destination)], check=True)
    manifest = json.loads((destination / "official-source-manifest.json").read_text(encoding="utf-8"))
    inventory = json.loads((destination / "inventory.json").read_text(encoding="utf-8"))
    assert len(manifest) == 7
    for entry in manifest:
        relative = Path(entry["package"]) / "official-source" / Path(entry["file"]).name
        data = (destination / relative).read_bytes()
        assert hashlib.sha256(data).hexdigest() == entry["sha256"]
        assert len(data) > 1000
        package = next(p for p in inventory if p["name"] == entry["package"])
        assert package["version"] == entry["version"]
        assert str(relative) in package["files"]
    for package in ("PySide6_Essentials", "shiboken6"):
        text = (destination / package / "official-source/LGPL-3.0-only.txt").read_text()
        assert "GNU LESSER GENERAL PUBLIC LICENSE" in text
        assert "Version 3, 29 June 2007" in text
    for package in ("openpyxl", "et_xmlfile"):
        assert "Permission is hereby granted" in (destination / package / "official-source/LICENCE.rst").read_text()


@pytest.mark.parametrize("damage", ["missing_lgpl", "changed_text", "wrong_version"])
def test_license_collection_fails_closed(tmp_path, damage):
    (tmp_path / "scripts").mkdir()
    shutil.copyfile(ROOT / "scripts/licenses.py", tmp_path / "scripts/licenses.py")
    shutil.copytree(ROOT / "licenses", tmp_path / "licenses")
    path = tmp_path / "licenses/upstream/manifest.json"
    manifest = json.loads(path.read_text())
    if damage == "missing_lgpl":
        manifest = [e for e in manifest if e["file"] != "shiboken6/LGPL-3.0-only.txt"]
    elif damage == "changed_text":
        (tmp_path / "licenses/upstream" / manifest[0]["file"]).write_text("MIT")
    else:
        manifest[0]["version"] = "0.0.0"
    path.write_text(json.dumps(manifest))
    process = subprocess.run([sys.executable, str(tmp_path / "scripts/licenses.py")], capture_output=True)
    assert process.returncode != 0
    assert not (tmp_path / "THIRD_PARTY_LICENSES/inventory.json").exists()
