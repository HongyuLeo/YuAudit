"""Capture actual running Qt views in two languages and themes."""
import os
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from yuaudit.ui import MainWindow
from yuaudit.demo import create_demo
from yuaudit.parsers import read_document
from yuaudit.normalize import structure
from yuaudit.engine import reconcile

root = Path(__file__).resolve().parent.parent
os.environ["YUAUDIT_DATA_DIR"] = str(root / "build" / "capture-profile")
app = QApplication([])
app.setStyle("Fusion")
window = MainWindow()
window.docs = [structure(read_document(p)) for p in create_demo(root / "demo")]
window.refresh_docs()
window.result = reconcile(window.docs)
window.render_results()
window.update_metrics()
window.show()
directory = root / "docs" / "screenshots"
directory.mkdir(parents=True, exist_ok=True)
jobs = [(lang, dark, page) for lang in (0, 1) for dark in (False, True) for page in (0, 1, 2, 3, 4)]


def capture():
    if not jobs:
        window.close()
        app.quit()
        return
    lang, dark, page = jobs.pop(0)
    window.language.setCurrentIndex(lang)
    window.dark.setChecked(dark)
    window.navigation.setCurrentRow(page)
    if page == 2:
        window.findings_table.selectRow(0)
    def save():
        name = f"{'zh' if lang == 0 else 'en'}-{'dark' if dark else 'light'}-{page}.png"
        window.grab().save(str(directory / name))
        QTimer.singleShot(50, capture)
    QTimer.singleShot(120, save)

QTimer.singleShot(100, capture)
raise SystemExit(app.exec())
