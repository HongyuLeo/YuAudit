from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QMessageBox
from .storage import configure_logging
from .ui import MainWindow


def main():
    parser = argparse.ArgumentParser(description="YuAudit local reconciliation")
    parser.add_argument("--smoke-test", type=Path, help="Run demo through actual UI, export reports and save screenshot/result")
    parser.add_argument("--language", choices=["zh", "en"])
    args = parser.parse_args()
    app = QApplication(sys.argv[:1])
    app.setStyle("Fusion")
    app.setApplicationName("YuAudit")
    app.setOrganizationName("YuAudit")
    configure_logging()
    window = MainWindow()
    if args.language:
        window.language.setCurrentIndex(0 if args.language == "zh" else 1)
    window.show()
    if args.smoke_test:
        output = args.smoke_test.resolve()
        output.mkdir(parents=True, exist_ok=True)
        state = {"stage": "import", "ticks": 0}
        # Error paths terminate rather than hanging a CI modal dialog.
        def failed(text):
            (output / "failure.txt").write_text(text, encoding="utf-8")
            app.exit(2)
        window.error = failed
        def tick():
            state["ticks"] += 1
            if state["ticks"] > 600:
                failed("Smoke test timeout")
                return
            if window.worker and window.worker.isRunning():
                return
            if state["stage"] == "import" and window.docs:
                state["stage"] = "audit"
                window.start_audit()
            elif state["stage"] == "audit" and window.result:
                from .reports import export_report
                from .parsers import read_document
                from .normalize import structure
                from .engine import reconcile
                from .models import Document, Kind, Line
                from decimal import Decimal
                resource_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
                for fixture in ("PO.xlsx", "PO.pdf"):
                    parsed = structure(read_document(str(resource_root / "demo" / "format-fixtures" / fixture)))
                    if len(parsed.lines) != 1 or parsed.lines[0].sku != "FORMAT-01":
                        failed(f"Packaged parser fixture failed: {fixture}")
                        return
                # Prove the packaged engine includes the pre-release collision fix.
                base = dict(po_number="PO-1", sku="S1", unit_price=Decimal(1), currency="USD")
                guard_docs = [Document(id="guard-po", path="fictional-po", kind=Kind.PO, lines=[
                    Line(**base, quantity=Decimal(10)),
                    Line(**{**base, "po_number": "PO1"}, quantity=Decimal(20))]),
                    Document(id="guard-invoice", path="fictional-invoice", kind=Kind.INVOICE, lines=[
                        Line(**base, invoice_number="INV1", quantity=Decimal(30), line_total=Decimal(30))]),
                    Document(id="guard-packing", path="fictional-packing", kind=Kind.PACKING, lines=[
                        Line(**base, invoice_number="INV1", quantity=Decimal(30))])]
                guard_result = reconcile(guard_docs)
                if (guard_result.conclusion != "review_required" or guard_result.checks != 1 or
                        not any(f.code == "ambiguous_match" for f in guard_result.findings)):
                    failed("Packaged identifier collision regression failed")
                    return
                for suffix in ("json", "xlsx", "csv"):
                    export_report(window.result, str(output / f"report.{suffix}"))
                window.findings_table.selectRow(0)
                state["stage"] = "capture"
            elif state["stage"] == "capture":
                window.grab().save(str(output / f"screenshot-{window.lang}.png"))
                result = {"version": "0.1.0", "documents": len(window.docs), "checks": window.result.checks,
                          "findings": len(window.result.findings), "language": window.lang,
                          "frozen": bool(getattr(sys, "frozen", False)), "platform": sys.platform}
                result["parser_formats"] = ["csv", "xlsx", "text-pdf"]
                result["identifier_collision_guard"] = "passed"
                (output / f"smoke-{window.lang}.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
                app.quit()
        timer = QTimer(window)
        timer.timeout.connect(tick)
        timer.start(100)
        QTimer.singleShot(0, window.load_demo)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
