"""Refresh missing license texts from versioned official source distributions.

Developer maintenance command only; builds use the checked-in files offline.
"""
from __future__ import annotations
import hashlib
import io
import json
from pathlib import Path
import tarfile
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent.parent / "licenses" / "upstream"


def download(url: str) -> bytes:
    with urlopen(url, timeout=30) as response:
        return response.read()


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    entries = []
    for name, version in (("openpyxl", "3.1.5"), ("et_xmlfile", "2.0.0")):
        metadata_url = f"https://pypi.org/pypi/{name}/{version}/json"
        metadata = json.loads(download(metadata_url))
        source = next(item for item in metadata["urls"] if item["packagetype"] == "sdist")
        archive = download(source["url"])
        archive_hash = hashlib.sha256(archive).hexdigest()
        if archive_hash != source["digests"]["sha256"]:
            raise RuntimeError(f"Official source archive checksum mismatch: {name}")
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
            members = [m for m in tar.getmembers() if m.isfile() and
                       Path(m.name).name.lower().split(".")[0] in ("licence", "license")]
            if not members:
                raise RuntimeError(f"No license text in official source: {name}")
            for member in members:
                data = tar.extractfile(member).read()
                relative = f"{name}/{Path(member.name).name}"
                path = ROOT / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
                entries.append(dict(package=name, version=version, file=relative,
                                    sha256=hashlib.sha256(data).hexdigest(), url=source["url"],
                                    archive_sha256=archive_hash, archive_member=member.name,
                                    metadata_url=metadata_url))
    # Both distributions are built from this exact Qt for Python source tag.
    for name in ("PySide6_Essentials", "shiboken6"):
        for filename in ("LGPL-3.0-only.txt", "GPL-3.0-only.txt"):
            url = f"https://code.qt.io/cgit/pyside/pyside-setup.git/plain/LICENSES/{filename}?h=v6.8.3"
            data = download(url)
            if b"GNU" not in data or b"Version 3" not in data or b"<html" in data.lower():
                raise RuntimeError(f"Invalid official Qt license response: {url}")
            relative = f"{name}/{filename}"
            path = ROOT / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            entries.append(dict(package=name, version="6.8.3", file=relative,
                                sha256=hashlib.sha256(data).hexdigest(), url=url,
                                source_tag="v6.8.3"))
    (ROOT / "manifest.json").write_text(json.dumps(entries, indent=2), encoding="utf-8")
    print(f"Saved {len(entries)} official license texts and source/hash provenance")


if __name__ == "__main__":
    main()
