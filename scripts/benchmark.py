"""Generate and run a reproducible large CSV test without retaining business data."""
import csv
import json
import tempfile
import time
import tracemalloc
from pathlib import Path
from yuaudit.parsers import read_document
from yuaudit.normalize import structure
from yuaudit.engine import reconcile

root = Path(__file__).resolve().parent.parent
tracemalloc.start()
start = time.perf_counter()
with tempfile.TemporaryDirectory(prefix="YuAudit 中文 ") as temp:
    documents = []
    for kind in ("PO", "Invoice", "Packing List"):
        path = Path(temp) / f"{kind}.csv"
        with path.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(["PO Number", "Invoice Number", "SKU", "Quantity", "Unit Price", "Line Total", "Currency"])
            for index in range(5000):
                writer.writerow(["PO1", "INV1" if kind != "PO" else "", f"ITEM-{index:06}", "3", "0.10", "0.30", "USD"])
        documents.append(structure(read_document(str(path))))
    result = reconcile(documents)
    assert not result.findings
    elapsed = time.perf_counter() - start
    _, peak = tracemalloc.get_traced_memory()
    report = {"rows_per_document": 5000, "documents": 3, "checks": result.checks,
              "findings": len(result.findings), "seconds_with_tracemalloc": round(elapsed, 3),
              "peak_python_allocations_mb": round(peak / 1024 / 1024, 2)}
    destination = root / "docs" / "benchmark.json"
    destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))
