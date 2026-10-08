import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QEventLoop
from yuaudit.ui import MainWindow
from yuaudit.demo import create_demo
from yuaudit.parsers import read_document
from yuaudit.normalize import structure
from yuaudit.engine import reconcile


def test_languages_themes_mapping_and_results(tmp_path, monkeypatch):
    monkeypatch.setenv("YUAUDIT_DATA_DIR", str(tmp_path / "界面 设置"))
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.show()
    window.docs = [structure(read_document(p)) for p in create_demo(tmp_path / "demo")]
    window.refresh_docs()
    window.result = reconcile(window.docs)
    window.render_results()
    assert window.findings_table.rowCount() == 8
    assert window.run_button.text() == "开始核对"
    window.language.setCurrentIndex(1)
    assert window.run_button.text() == "Reconcile"
    assert window.navigation.item(1).text() == "Documents & mapping"
    window.dark.setChecked(True)
    assert "#111827" in window.styleSheet()
    window.findings_table.selectRow(0)
    assert window.evidence.toPlainText()
    window.search.setText("GOOD-01")
    assert all(window.findings_table.isRowHidden(i) for i in range(8))
    window.search.clear()
    window.navigation.setCurrentRow(1)
    window.doc_list.setCurrentRow(0)
    window.preview.item(0, 4).setText("12")
    assert window.docs[0].rows[0].values["Quantity"] == "12"
    assert window.result is None
    window.close()
    app.processEvents()
