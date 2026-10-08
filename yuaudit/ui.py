from __future__ import annotations
import copy
import logging
from pathlib import Path
from threading import Event
from PySide6.QtCore import Qt, QThread, Signal, QUrl, QTimer
from PySide6.QtGui import QDesktopServices, QIcon, QColor, QPixmap
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QLabel, QComboBox, QCheckBox, QListWidget, QStackedWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QSplitter, QPlainTextEdit, QFileDialog, QMessageBox,
    QFormLayout, QLineEdit, QDoubleSpinBox, QProgressBar, QInputDialog, QScrollArea,
    QAbstractItemView, QFrame)
from .models import Document, FIELDS, Kind, Result, Rules
from .normalize import structure
from .parsers import read_document, Cancelled, checkpoint
from .engine import reconcile
from .demo import create_demo
from .reports import export_report
from .storage import data_dir, save_json, load_json, save_session, load_session
from .ai import OllamaProvider
from .i18n import LABELS, FIELD_NAMES, CODE_NAMES


def asset_path(name: str) -> Path:
    import sys
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent)) / "assets" / name


class Worker(QThread):
    completed = Signal(object)
    failed = Signal(str)
    message = Signal(str)

    def __init__(self, operation, parent=None):
        super().__init__(parent)
        self.operation = operation
        self.cancel = Event()

    def run(self):
        try:
            output = self.operation(self.cancel, self.message.emit)
            checkpoint(self.cancel)
            self.completed.emit(output)
        except Cancelled:
            self.failed.emit("Cancelled / 已取消；工作台数据已保留")
        except Exception as exc:
            logging.getLogger("yuaudit").exception("Background task failed")
            self.failed.emit(str(exc))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YuAudit · Local AI Document Reconciliation Studio")
        self.setWindowIcon(QIcon(str(asset_path("icon.ico"))))
        self.resize(1320, 860)
        self.setMinimumSize(980, 680)
        self.setAcceptDrops(True)
        self.docs: list[Document] = []
        self.result: Result | None = None
        self.worker: Worker | None = None
        self.config = load_json("settings.json")
        self.lang = self.config.get("language", "zh")
        try:
            self.rules = Rules.model_validate(self.config.get("rules", {}))
        except ValueError:
            self.rules = Rules()
        self.labels = []
        self.mapping_boxes = {}
        self.display_headers = []
        self.selected_sources = []
        self.build()
        self.translate()
        self.style()

    def t(self, code):
        return LABELS[code][0 if self.lang == "zh" else 1]

    def text_widget(self, widget, key):
        self.labels.append((widget, key))
        widget.setText(self.t(key))
        return widget

    def button(self, key, callback):
        b = self.text_widget(QPushButton(), key)
        b.clicked.connect(lambda: self.guarded(callback))
        return b

    def guarded(self, callback):
        try:
            callback()
        except Exception as exc:
            logging.getLogger("yuaudit").exception("UI action failed")
            self.error(str(exc))

    def build(self):
        shell = QWidget()
        self.setCentralWidget(shell)
        outer = QVBoxLayout(shell)
        outer.setContentsMargins(24, 20, 24, 16)
        header = QHBoxLayout()
        logo = QLabel("YuAudit")
        logo.setObjectName("brand")
        mark = QLabel()
        mark.setPixmap(QPixmap(str(asset_path("icon.png"))).scaled(36, 36, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        header.addWidget(mark)
        header.addWidget(logo)
        header.addWidget(QLabel("Local AI Document Reconciliation Studio"))
        header.addStretch()
        self.language = QComboBox()
        self.language.addItems(["简体中文", "English"])
        self.language.setCurrentIndex(0 if self.lang == "zh" else 1)
        self.language.currentIndexChanged.connect(self.change_language)
        self.dark = self.text_widget(QCheckBox(), "theme")
        self.dark.setChecked(self.config.get("dark", False))
        self.dark.toggled.connect(self.style)
        header.addWidget(self.dark)
        header.addWidget(self.language)
        outer.addLayout(header)
        middle = QHBoxLayout()
        self.navigation = QListWidget()
        self.navigation.setFixedWidth(182)
        self.pages = QStackedWidget()
        self.navigation.currentRowChanged.connect(self.pages.setCurrentIndex)
        middle.addWidget(self.navigation)
        middle.addWidget(self.pages, 1)
        outer.addLayout(middle, 1)
        self.create_home()
        self.create_files()
        self.create_results()
        self.create_rules()
        self.create_ai()
        bottom = QHBoxLayout()
        self.status = self.text_widget(QLabel(), "ready")
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.progress.setMaximumWidth(200)
        self.cancel_button = self.button("cancel", self.cancel_task)
        self.cancel_button.setEnabled(False)
        self.run_button = self.button("run", self.start_audit)
        self.run_button.setObjectName("primary")
        bottom.addWidget(self.status, 1)
        bottom.addWidget(self.progress)
        bottom.addWidget(self.cancel_button)
        bottom.addWidget(self.run_button)
        outer.addLayout(bottom)
        self.navigation.setCurrentRow(0)

    def page(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(18, 12, 0, 0)
        self.pages.addWidget(w)
        return layout

    def create_home(self):
        layout = self.page()
        title = self.text_widget(QLabel(), "intro")
        title.setObjectName("title")
        layout.addWidget(title)
        description = self.text_widget(QLabel(), "description")
        description.setWordWrap(True)
        layout.addWidget(description)
        layout.addSpacing(28)
        self.metrics = QLabel()
        self.metrics.setObjectName("card")
        self.metrics.setMinimumHeight(100)
        layout.addWidget(self.metrics)
        self.drop_label = self.text_widget(QLabel(), "drop")
        self.drop_label.setObjectName("drop")
        self.drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_label.setMinimumHeight(145)
        layout.addWidget(self.drop_label)
        actions = QHBoxLayout()
        self.import_button = self.button("import", self.pick_files)
        self.demo_button = self.button("demo", self.load_demo)
        actions.addWidget(self.import_button)
        actions.addWidget(self.demo_button)
        actions.addWidget(self.button("restore", self.restore_session))
        actions.addStretch()
        layout.addLayout(actions)
        layout.addStretch()
        layout.addWidget(self.text_widget(QLabel(), "offline"))

    def create_files(self):
        layout = self.page()
        toolbar = QHBoxLayout()
        toolbar.addWidget(self.button("import", self.pick_files))
        toolbar.addWidget(self.button("remove", self.remove_doc))
        toolbar.addWidget(self.button("clear", self.clear_docs))
        toolbar.addStretch()
        layout.addLayout(toolbar)
        splitter = QSplitter()
        self.doc_list = QListWidget()
        self.doc_list.currentRowChanged.connect(self.show_doc)
        splitter.addWidget(self.doc_list)
        right = QWidget()
        panel = QVBoxLayout(right)
        meta = QHBoxLayout()
        self.kind_box = QComboBox()
        for kind in Kind:
            self.kind_box.addItem(kind.value, kind.value)
        self.kind_box.currentIndexChanged.connect(self.metadata_changed)
        self.partial = self.text_widget(QCheckBox(), "partial")
        self.partial.toggled.connect(self.metadata_changed)
        meta.addWidget(self.kind_box)
        meta.addWidget(self.partial)
        meta.addStretch()
        panel.addLayout(meta)
        panel.addWidget(self.text_widget(QLabel(), "mapping"))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(185)
        self.mapping_widget = QWidget()
        self.mapping_widget.setObjectName("mappingContent")
        self.mapping_form = QFormLayout(self.mapping_widget)
        scroll.setWidget(self.mapping_widget)
        panel.addWidget(scroll)
        panel.addWidget(self.text_widget(QLabel(), "preview"))
        self.preview = QTableWidget()
        self.preview.setAlternatingRowColors(True)
        self.preview.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.preview.cellChanged.connect(self.edit_raw)
        panel.addWidget(self.preview, 1)
        self.file_warning = QLabel()
        self.file_warning.setWordWrap(True)
        panel.addWidget(self.file_warning)
        actions = QHBoxLayout()
        actions.addWidget(self.button("apply", self.apply_doc))
        actions.addWidget(self.button("suggest", self.ai_mapping))
        actions.addStretch()
        panel.addLayout(actions)
        splitter.addWidget(right)
        splitter.setSizes([220, 800])
        layout.addWidget(splitter)

    def create_results(self):
        layout = self.page()
        toolbar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.textChanged.connect(self.filter_results)
        self.severity = QComboBox()
        self.severity.addItems(["", "error", "warning", "info"])
        self.severity.currentIndexChanged.connect(self.filter_results)
        toolbar.addWidget(self.search, 1)
        toolbar.addWidget(self.severity)
        toolbar.addWidget(self.button("export", self.export))
        toolbar.addWidget(self.button("summary", self.ai_summary))
        layout.addLayout(toolbar)
        self.result_label = QLabel()
        self.result_label.setWordWrap(True)
        layout.addWidget(self.result_label)
        vertical = QSplitter(Qt.Orientation.Vertical)
        self.findings_table = QTableWidget()
        self.findings_table.setColumnCount(8)
        self.findings_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.findings_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.findings_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.findings_table.setAlternatingRowColors(True)
        self.findings_table.setSortingEnabled(True)
        self.findings_table.itemSelectionChanged.connect(self.show_evidence)
        vertical.addWidget(self.findings_table)
        evidence_panel = QWidget()
        evidence_layout = QVBoxLayout(evidence_panel)
        evidence_layout.addWidget(self.text_widget(QLabel(), "evidence"))
        self.evidence = QPlainTextEdit()
        self.evidence.setReadOnly(True)
        evidence_layout.addWidget(self.evidence)
        actions = QHBoxLayout()
        actions.addWidget(self.button("open", self.open_source))
        actions.addWidget(self.button("review", self.review_finding))
        actions.addStretch()
        evidence_layout.addLayout(actions)
        vertical.addWidget(evidence_panel)
        vertical.setSizes([360, 230])
        layout.addWidget(vertical, 1)

    def create_rules(self):
        layout = self.page()
        form = QFormLayout()
        self.amount_input = QLineEdit(str(self.rules.amount_tolerance))
        self.qty_input = QLineEdit(str(self.rules.quantity_tolerance))
        self.fuzzy_input = self.text_widget(QCheckBox(), "fuzzy")
        self.fuzzy_input.setChecked(self.rules.fuzzy_enabled)
        self.norm_input = self.text_widget(QCheckBox(), "normalize")
        self.norm_input.setChecked(self.rules.normalize_identifiers)
        self.threshold = QDoubleSpinBox()
        self.threshold.setRange(0.5, 1)
        self.threshold.setSingleStep(0.01)
        self.threshold.setValue(self.rules.fuzzy_threshold)
        for key, widget in (("amount", self.amount_input), ("quantity", self.qty_input), ("threshold", self.threshold)):
            form.addRow(self.text_widget(QLabel(), key), widget)
        form.addRow(self.fuzzy_input)
        form.addRow(self.norm_input)
        layout.addLayout(form)
        layout.addWidget(self.button("save_rules", self.save_rules))
        layout.addStretch()

    def create_ai(self):
        layout = self.page()
        text = self.text_widget(QLabel(), "ai_intro")
        text.setWordWrap(True)
        layout.addWidget(text)
        self.ai_enabled = self.text_widget(QCheckBox(), "ai_enabled")
        self.ai_enabled.setChecked(self.config.get("ai_enabled", False))
        self.endpoint = QLineEdit(self.config.get("endpoint", "http://127.0.0.1:11434"))
        self.model_name = QLineEdit(self.config.get("model", "qwen2.5:7b"))
        form = QFormLayout()
        form.addRow(self.ai_enabled)
        form.addRow(self.text_widget(QLabel(), "endpoint"), self.endpoint)
        form.addRow(self.text_widget(QLabel(), "model"), self.model_name)
        layout.addLayout(form)
        layout.addWidget(self.button("save_ai", self.save_ai))
        self.ai_text = QPlainTextEdit()
        self.ai_text.setReadOnly(True)
        layout.addWidget(self.ai_text, 1)

    def translate(self):
        for widget, key in self.labels:
            widget.setText(self.t(key))
        current = self.navigation.currentRow()
        self.navigation.blockSignals(True)
        self.navigation.clear()
        self.navigation.addItems([self.t(k) for k in ("home", "files", "results", "rules", "ai")])
        self.navigation.setCurrentRow(max(0, current))
        self.navigation.blockSignals(False)
        self.search.setPlaceholderText(self.t("search"))
        self.severity.setItemText(0, self.t("all"))
        self.update_metrics()
        self.show_doc(self.doc_list.currentRow())
        self.render_results()

    def change_language(self, index):
        self.lang = "zh" if index == 0 else "en"
        self.translate()
        self.persist_settings()

    def style(self, *_):
        dark = self.dark.isChecked()
        bg, panel, ink, muted, border, selection = (
            ("#111827", "#1f2937", "#e5e7eb", "#94a3b8", "#374151", "#334155") if dark else
            ("#f6f7f9", "#ffffff", "#1e293b", "#64748b", "#dce2ea", "#e2e8f0"))
        self.setStyleSheet(f"""
            QWidget {{ font-family: 'Segoe UI', 'Microsoft YaHei UI'; font-size: 13px; color: {ink}; }}
            QMainWindow, QStackedWidget {{ background: {bg}; }}
            QWidget#mappingContent {{ background: {panel}; }}
            QLabel#brand {{ font-size: 25px; font-weight: 700; padding-right: 14px; }}
            QLabel#title {{ font-size: 30px; font-weight: 600; padding: 20px 0; }}
            QLabel#card {{ background: {panel}; border: 1px solid {border}; border-radius: 6px; padding: 24px; font-size: 18px; }}
            QLabel#drop {{ border: 2px dashed {border}; border-radius: 6px; color: {muted}; }}
            QListWidget, QTableWidget, QPlainTextEdit, QLineEdit, QComboBox, QDoubleSpinBox, QScrollArea {{
                background: {panel}; border: 1px solid {border}; border-radius: 5px; selection-background-color: {selection}; selection-color: {ink}; }}
            QTableWidget {{ alternate-background-color: {bg}; gridline-color: {border}; }}
            QListWidget::item {{ padding: 15px 8px; }}
            QListWidget::item:selected {{ background: {selection}; border-radius: 4px; }}
            QHeaderView::section {{ background: {selection}; color: {ink}; padding: 9px; border: 0; }}
            QPushButton {{ background: {panel}; border: 1px solid {border}; border-radius: 6px; padding: 9px 14px; min-height: 20px; }}
            QPushButton:hover {{ background: {selection}; }}
            QPushButton:disabled {{ color: {muted}; }}
            QPushButton#primary {{ background: #334155; color: white; border: 1px solid #475569; }}
            QLineEdit, QComboBox, QDoubleSpinBox {{ padding: 7px; }}
            QProgressBar {{ border: 1px solid {border}; border-radius: 3px; background: {panel}; }}
            QProgressBar::chunk {{ background: #64748b; }}
            QToolTip {{ background: {panel}; color: {ink}; border: 1px solid {border}; }}
        """)
        if hasattr(self, "ai_enabled"):
            self.persist_settings()

    def persist_settings(self):
        self.config.update(language=self.lang, dark=self.dark.isChecked(), rules=self.rules.model_dump(mode="json"))
        try:
            save_json("settings.json", self.config)
        except OSError as exc:
            self.status.setText(str(exc))

    def error(self, text):
        self.status.setText(text[:180])
        QMessageBox.warning(self, "YuAudit", text)

    def start_task(self, operation, callback):
        if self.worker and self.worker.isRunning():
            return
        self.worker = Worker(operation, self)
        self.pages.setEnabled(False)
        self.run_button.setEnabled(False)
        self.language.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.progress.setVisible(True)
        self.status.setText(self.t("busy"))
        self.worker.message.connect(self.status.setText)
        self.worker.completed.connect(callback)
        self.worker.failed.connect(self.task_failed)
        self.worker.finished.connect(self.task_finished)
        self.worker.start()

    def task_failed(self, message):
        if message.startswith("Cancelled"):
            self.status.setText(message)
        else:
            self.error(message)

    def task_finished(self):
        self.pages.setEnabled(True)
        self.run_button.setEnabled(True)
        self.language.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.progress.setVisible(False)

    def cancel_task(self):
        if self.worker:
            self.worker.cancel.set()
            self.status.setText("正在取消 / Cancelling…")

    def pick_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, self.t("import"), "", "Documents (*.xlsx *.csv *.pdf)")
        if paths:
            self.import_paths(paths)

    def import_paths(self, paths, demo=False):
        existing = {d.path for d in self.docs}
        paths = list(dict.fromkeys(str(Path(p).resolve()) for p in paths if str(Path(p).resolve()) not in existing))
        if not paths:
            return
        def operation(cancel, message):
            docs, errors = [], []
            current_rows = sum(len(d.rows) for d in self.docs)
            for path in paths:
                checkpoint(cancel)
                message(Path(path).name)
                try:
                    doc = read_document(path, cancel=cancel)
                    if current_rows + len(doc.rows) > 200000:
                        raise ValueError("Workspace exceeds 200,000 rows / 工作台总行数超过二十万，请分批核对")
                    current_rows += len(doc.rows)
                    if demo and doc.kind == Kind.INVOICE:
                        # Demonstrate full PO completeness checks and one explicitly partial SKU via a separate batch file.
                        doc.partial = False
                    docs.append(doc)
                except Cancelled:
                    raise
                except Exception as exc:
                    errors.append(f"{Path(path).name}: {exc}")
            return docs, errors
        def complete(output):
            docs, errors = output
            self.docs.extend(docs)
            self.invalidate()
            self.refresh_docs()
            self.navigation.setCurrentRow(1)
            self.status.setText(f"{len(docs)} files imported / 文件已导入")
            if errors:
                self.error("\n\n".join(errors))
        self.start_task(operation, complete)

    def load_demo(self):
        if self.docs:
            self.error("请先清空工作台 / Clear workspace before loading demo")
            return
        paths = create_demo(data_dir() / "demo")
        self.import_paths(paths, demo=True)

    def refresh_docs(self):
        self.doc_list.blockSignals(True)
        self.doc_list.clear()
        for doc in self.docs:
            self.doc_list.addItem(f"{doc.kind.value}\n{Path(doc.path).name}")
        self.doc_list.blockSignals(False)
        if self.docs:
            self.doc_list.setCurrentRow(0)
        else:
            self.show_doc(-1)
        self.update_metrics()

    def selected_doc(self):
        row = self.doc_list.currentRow()
        return self.docs[row] if 0 <= row < len(self.docs) else None

    def show_doc(self, row):
        self.kind_box.blockSignals(True)
        self.partial.blockSignals(True)
        self.preview.blockSignals(True)
        while self.mapping_form.rowCount():
            self.mapping_form.removeRow(0)
        self.mapping_boxes = {}
        self.preview.clear()
        self.preview.setRowCount(0)
        doc = self.selected_doc()
        if doc:
            self.kind_box.setCurrentIndex(list(Kind).index(doc.kind))
            self.partial.setChecked(doc.partial)
            headers = doc.headers or list(dict.fromkeys(h for raw in doc.rows[:500] for h in raw.values))
            self.display_headers = headers
            for header in headers:
                combo = QComboBox()
                combo.addItem("忽略 / Ignore", "")
                for field in FIELDS:
                    combo.addItem(f"{FIELD_NAMES[field]} · {field}" if self.lang == "zh" else field, field)
                combo.setCurrentIndex(max(0, combo.findData(doc.mapping.get(header, ""))))
                combo.currentIndexChanged.connect(lambda _, h=header, box=combo: self.mapping_changed(h, box))
                self.mapping_boxes[header] = combo
                self.mapping_form.addRow(header, combo)
            # Paginated preview avoids creating millions of Qt items. Edits affect first 500 rows.
            self.preview.setColumnCount(len(headers))
            self.preview.setHorizontalHeaderLabels(headers)
            visible = doc.rows[:500]
            self.preview.setRowCount(len(visible))
            for r, raw in enumerate(visible):
                for c, h in enumerate(headers):
                    item = QTableWidgetItem(raw.values.get(h, ""))
                    item.setToolTip(raw.source.location())
                    self.preview.setItem(r, c, item)
            self.preview.resizeColumnsToContents()
            for c in range(len(headers)):
                self.preview.setColumnWidth(c, min(240, max(100, self.preview.columnWidth(c))))
            self.file_warning.setText("\n".join([f"{len(doc.rows)} rows; preview first 500 / 预览前 500 行", *doc.warnings]))
        else:
            self.file_warning.setText(self.t("empty"))
        self.kind_box.blockSignals(False)
        self.partial.blockSignals(False)
        self.preview.blockSignals(False)

    def metadata_changed(self, *_):
        doc = self.selected_doc()
        if doc:
            doc.kind = Kind(self.kind_box.currentData())
            doc.partial = self.partial.isChecked()
            self.invalidate()

    def mapping_changed(self, header, box):
        doc = self.selected_doc()
        if doc:
            value = box.currentData()
            if value:
                doc.mapping[header] = value
            else:
                doc.mapping.pop(header, None)
            self.invalidate()

    def edit_raw(self, row, column):
        doc = self.selected_doc()
        if doc and row < len(doc.rows):
            doc.rows[row].values[self.display_headers[column]] = self.preview.item(row, column).text()
            self.invalidate()

    def apply_doc(self):
        doc = self.selected_doc()
        if doc:
            # Validate asynchronously; big files must not freeze GUI.
            def complete(parsed):
                doc.lines = parsed.lines
                self.status.setText(f"{len(parsed.lines)} lines validated / 行已验证")
            self.start_task(lambda c, m: structure(doc, c), complete)

    def invalidate(self):
        self.result = None
        self.render_results()
        self.update_metrics()

    def remove_doc(self):
        index = self.doc_list.currentRow()
        if index >= 0:
            self.docs.pop(index)
            self.invalidate()
            self.refresh_docs()

    def clear_docs(self):
        self.docs.clear()
        self.invalidate()
        self.refresh_docs()

    def start_audit(self):
        if not self.docs:
            self.error(self.t("empty"))
            return
        # UI is disabled during work, so worker owns the document state until completion.
        docs = self.docs
        rules = self.rules.model_copy(deep=True)
        def operation(cancel, message):
            for doc in docs:
                checkpoint(cancel)
                message(f"Validate / 验证: {Path(doc.path).name}")
                structure(doc, cancel)
            message("Reconcile / 核对…")
            result = reconcile(docs, rules, cancel)
            checkpoint(cancel)
            save_session(result)
            return result
        def complete(result):
            self.result = result
            self.render_results()
            self.update_metrics()
            self.navigation.setCurrentRow(2)
            self.status.setText(self.t("done"))
        self.start_task(operation, complete)

    def update_metrics(self):
        if not hasattr(self, "metrics"):
            return
        n = len(self.docs)
        rows = sum(len(d.rows) for d in self.docs)
        f = len(self.result.findings) if self.result else "—"
        self.metrics.setText(f"{n}  单据     ·     {rows}  数据行     ·     {f}  审查事项" if self.lang == "zh" else
                             f"{n}  documents     ·     {rows}  rows     ·     {f}  review findings")

    def render_results(self):
        if not hasattr(self, "findings_table"):
            return
        table = self.findings_table
        table.setSortingEnabled(False)
        table.setHorizontalHeaderLabels(["异常类型", "严重程度", "SKU / 编号", "左侧值", "右侧值", "差异", "状态", "规则"] if self.lang == "zh" else
                                        ["Finding", "Severity", "SKU / reference", "Left", "Right", "Difference", "Status", "Rule"])
        table.setRowCount(len(self.result.findings) if self.result else 0)
        if self.result:
            for row, finding in enumerate(self.result.findings):
                code = CODE_NAMES[finding.code][0 if self.lang == "zh" else 1]
                severity = {"error": "错误", "warning": "警告", "info": "信息"}.get(finding.severity, finding.severity) if self.lang == "zh" else finding.severity
                status = {"open": "待审核", "reviewed": "已记录审核"}.get(finding.status, finding.status) if self.lang == "zh" else finding.status
                for col, value in enumerate([code, severity, finding.identifier, finding.left, finding.right,
                                             finding.difference, status, finding.rule]):
                    item = QTableWidgetItem(value)
                    item.setData(Qt.ItemDataRole.UserRole, row)
                    item.setToolTip(value)
                    table.setItem(row, col, item)
            self.result_label.setText(f"{len(self.result.findings)} findings / 审查事项 · {self.result.checks} checks / 确定性检查\n"
                                      + ("存在待审核或无法核实事项；记录审核不会改变检测结论。" if self.lang == "zh" else
                                         "Review or unverified items remain. Review notes do not change deterministic findings.") if self.result.findings else
                                      "No exceptions in checked scope / 已核对范围内未发现异常")
        else:
            self.result_label.setText("请导入并核对；修改数据或规则后需重新核对。" if self.lang == "zh" else "Import and reconcile. Changes to data or rules require another run.")
        table.resizeColumnsToContents()
        for c in range(8):
            table.setColumnWidth(c, min(300, max(95, table.columnWidth(c))))
        table.setSortingEnabled(True)
        self.filter_results()
        self.evidence.clear()

    def filter_results(self, *_):
        if not self.result:
            return
        search = self.search.text().casefold()
        severity = ["", "error", "warning", "info"][self.severity.currentIndex()]
        for row in range(self.findings_table.rowCount()):
            index = self.findings_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            finding = self.result.findings[index]
            text = " ".join([finding.code, finding.identifier, finding.rule, finding.suggestion]).casefold()
            self.findings_table.setRowHidden(row, bool((severity and finding.severity != severity) or (search and search not in text)))

    def selected_finding(self):
        items = self.findings_table.selectedItems()
        if self.result and items:
            return self.result.findings[items[0].data(Qt.ItemDataRole.UserRole)]
        return None

    def show_evidence(self):
        finding = self.selected_finding()
        if not finding:
            return
        self.selected_sources = finding.sources
        self.evidence.setPlainText(f"{finding.rule}\n{finding.suggestion}\n\n" + "\n".join(
            f"{s.location()}\n  {s.raw}" + (f"  [corrected / 已修正; original / 原值={s.original_raw}]" if s.corrected else "") +
            (f"  bbox={s.bbox}" if s.bbox else "") for s in finding.sources) +
            f"\n\nReview / 人工审核: {finding.review_note}")

    def open_source(self):
        if not self.selected_sources:
            self.error("请先选择带来源的异常 / Select a finding with source evidence")
            return
        paths = list(dict.fromkeys(s.file for s in self.selected_sources))
        selected, ok = QInputDialog.getItem(self, "YuAudit", "Source / 源文件", paths, 0, False)
        if ok:
            if not Path(selected).is_file():
                self.error("Source missing / 源文件已移动或删除")
            else:
                QDesktopServices.openUrl(QUrl.fromLocalFile(selected))

    def review_finding(self):
        finding = self.selected_finding()
        if not finding:
            self.error("请先选择异常 / Select a finding")
            return
        note, ok = QInputDialog.getMultiLineText(self, "YuAudit", "审核备注（不会修改检测结论） / Review note (finding stays unchanged)", finding.review_note)
        if ok and note.strip():
            finding.review_note = note
            finding.status = "reviewed"
            try:
                save_session(self.result)
            except OSError as exc:
                self.error(str(exc))
            self.render_results()

    def export(self):
        if not self.result:
            self.error("请先核对 / Reconcile first")
            return
        path, _ = QFileDialog.getSaveFileName(self, self.t("export"), "YuAudit-report.xlsx", "Excel (*.xlsx);;CSV (*.csv);;JSON (*.json)")
        if path:
            self.start_task(lambda c, m: export_report(self.result, path),
                            lambda _: self.status.setText(f"Exported / 已导出: {path}"))

    def restore_session(self):
        def complete(result):
            if result is None:
                self.error("没有已保存的审查 / No saved review")
                return
            self.result = result
            self.docs = result.documents
            self.rules = result.rules
            self.amount_input.setText(str(self.rules.amount_tolerance))
            self.qty_input.setText(str(self.rules.quantity_tolerance))
            self.fuzzy_input.setChecked(self.rules.fuzzy_enabled)
            self.norm_input.setChecked(self.rules.normalize_identifiers)
            self.threshold.setValue(self.rules.fuzzy_threshold)
            self.refresh_docs()
            self.render_results()
            self.navigation.setCurrentRow(2)
        self.start_task(lambda c, m: load_session(), complete)

    def save_rules(self):
        try:
            self.rules = Rules(amount_tolerance=self.amount_input.text(), quantity_tolerance=self.qty_input.text(),
                               fuzzy_threshold=self.threshold.value(), fuzzy_enabled=self.fuzzy_input.isChecked(),
                               normalize_identifiers=self.norm_input.isChecked())
            self.invalidate()
            self.persist_settings()
            self.status.setText("规则已保存 / Rules saved")
        except ValueError as exc:
            self.error(str(exc))

    def save_ai(self):
        try:
            OllamaProvider(self.endpoint.text(), self.model_name.text())
            self.config.update(ai_enabled=self.ai_enabled.isChecked(), endpoint=self.endpoint.text(), model=self.model_name.text())
            self.persist_settings()
            self.status.setText("模型设置已保存 / AI settings saved")
        except ValueError as exc:
            self.error(str(exc))

    def provider(self):
        if not self.ai_enabled.isChecked():
            raise ValueError("请在本地模型页面启用 AI / Enable AI on Local AI page")
        return OllamaProvider(self.endpoint.text(), self.model_name.text())

    def ai_mapping(self):
        doc = self.selected_doc()
        if not doc:
            self.error(self.t("empty"))
            return
        try:
            provider = self.provider()
        except ValueError as exc:
            self.error(str(exc))
            return
        headers = self.display_headers[:]
        def complete(advice):
            self.ai_text.setPlainText("AI DRAFT / 未确认建议\n" + advice.model_dump_json(indent=2))
            self.navigation.setCurrentRow(4)
            # Advice deliberately stays separate: user edits mapping after reading it.
            self.status.setText("建议已展示；请人工修改映射 / Advice ready; edit mapping manually")
        self.start_task(lambda c, m: provider.mapping(headers), complete)

    def ai_summary(self):
        if not self.result:
            self.error("请先核对 / Reconcile first")
            return
        try:
            provider = self.provider()
        except ValueError as exc:
            self.error(str(exc))
            return
        compact = [f.model_dump(exclude={"sources"}) for f in self.result.findings]
        def complete(advice):
            text = "AI DRAFT / 未核实草稿\n" + advice.summary + "\n" + advice.uncertainty
            self.result.ai_summary = text
            self.ai_text.setPlainText(text)
            self.navigation.setCurrentRow(4)
        self.start_task(lambda c, m: provider.summary(compact), complete)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        if not self.worker or not self.worker.isRunning():
            paths = [u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
            self.import_paths(paths)

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.cancel_task()
            event.ignore()
            self.status.setText("等待任务取消后关闭 / Wait for task cancellation before closing")
        else:
            self.persist_settings()
            event.accept()
