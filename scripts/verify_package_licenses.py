"""Verify actual redistribution files in the final ZIP, including both copies."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile


def main():
    root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--zip", type=Path, default=root / "dist/YuAudit-Windows-x64.zip")
    parser.add_argument("--output", type=Path, default=root / "docs/verification/package-audit.json")
    args = parser.parse_args()
    official = json.loads((root / "licenses/upstream/manifest.json").read_text(encoding="utf-8"))
    with zipfile.ZipFile(args.zip) as archive:
        if archive.testzip() is not None:
            raise RuntimeError("ZIP integrity failure")
        prefix = "YuAudit-Windows-x64/"
        inventory = json.loads(archive.read(prefix + "THIRD_PARTY_LICENSES/inventory.json"))
        checked = 0
        for directory in ("THIRD_PARTY_LICENSES/", "_internal/THIRD_PARTY_LICENSES/"):
            base = prefix + directory
            if json.loads(archive.read(base + "official-source-manifest.json")) != official:
                raise RuntimeError("Package official-source manifest differs from source")
            for package in inventory:
                if not package["files"]:
                    raise RuntimeError(f"No license files for {package['name']}")
                for filename in package["files"]:
                    if not archive.read(base + filename.replace("\\", "/")):
                        raise RuntimeError(f"Empty license file: {filename}")
                    checked += 1
            if len(archive.read(base + "Python/LICENSE.txt")) < 1000:
                raise RuntimeError("Python runtime license missing")
            for entry in official:
                filename = f"{entry['package']}/official-source/{Path(entry['file']).name}"
                data = archive.read(base + filename)
                if hashlib.sha256(data).hexdigest() != entry["sha256"]:
                    raise RuntimeError(f"Packaged official license checksum mismatch: {filename}")
        exe_hash = hashlib.sha256(archive.read(prefix + "YuAudit.exe")).hexdigest()
    report = dict(zip_integrity="passed", inventoried_packages=len(inventory),
                  license_file_checks=checked, official_texts_per_copy=len(official),
                  license_locations=["THIRD_PARTY_LICENSES", "_internal/THIRD_PARTY_LICENSES"],
                  python_runtime_license="passed", official_text_hashes="passed", exe_sha256=exe_hash)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
