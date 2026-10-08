from pathlib import Path
import csv

HEADERS = ["PO Number", "Invoice Number", "SKU", "Product Description", "Quantity", "Unit Price", "Line Total", "Currency", "Supplier", "Shipment Date"]


def create_demo(directory: Path) -> list[str]:
    directory.mkdir(parents=True, exist_ok=True)
    po = [("GOOD-01", 10, "2.50"), ("QTY-02", 10, "3.00"), ("PRICE-03", 5, "4.00"),
          ("MISSING-04", 8, "1.00"), ("DUP-05", 2, "6.00"), ("FUZZY-06", 3, "2.00"), ("BATCH-07", 100, "1.25")]
    invoice = [("GOOD-01", 10, "2.50"), ("QTY-02", 9, "3.00"), ("PRICE-03", 5, "4.50"),
               ("DUP-05", 2, "6.00"), ("DUP-05", 2, "6.00"), ("FUZZY-0G", 3, "2.00"),
               ("BATCH-07", 40, "1.25"), ("BATCH-07", 60, "1.25"), ("EXTRA-08", 1, "8.00")]
    paths = []
    from decimal import Decimal
    for name, lines in (("PO", po), ("Invoice", invoice), ("Packing List", [v for i, v in enumerate(invoice) if i != 4])):
        path = directory / f"Demo {name}.csv"
        with path.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(HEADERS)
            for sku, qty, price in lines:
                packing = name == "Packing List"
                invoice_id = "DEMO-INV-002" if sku == "BATCH-07" and qty == 60 else "DEMO-INV-001"
                writer.writerow(["DEMO-PO-001", "" if name == "PO" else invoice_id, sku,
                                 f"Fictional item {sku}", qty, "" if packing else price,
                                 "" if packing else str(Decimal(qty) * Decimal(price)),
                                 "USD", "Fictional Example Supplier", "2026-01-15"])
        paths.append(str(path))
    return paths
