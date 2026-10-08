"""Deterministic rules. AI cannot change values, matches or findings."""
from __future__ import annotations
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, localcontext
from difflib import SequenceMatcher
from threading import Event
from .models import Document, Finding, Kind, Line, Result, Rules, Source
from .normalize import key
from .parsers import checkpoint

TEXT = {
    "missing_field": "补充缺失字段后重新核对 / Supply missing fields and rerun",
    "arithmetic": "核查数量、单价及行金额 / Check quantity × unit price",
    "duplicate_line": "确认重复行是否为真实交易 / Verify whether repeated lines are legitimate",
    "duplicate_invoice": "确认是否重复导入或重复开票 / Check repeated invoice identifiers across documents",
    "missing_invoice_item": "检查是否未开票；部分开票请标记批次 / Check unbilled item or declare partial invoicing",
    "extra_invoice_item": "核查发票商品是否属于订单 / Verify item against purchase order",
    "sku_mismatch": "标识符近似但未经确认，修正后重新核对 / Similar identifiers require correction and rerun",
    "ambiguous_match": "存在多个候选，需人工指定正确标识符 / Multiple candidates; resolve identifiers manually",
    "quantity": "核对累计数量及分批出货范围 / Check cumulative quantities and shipment scope",
    "unit_price": "检查合同价格与计价单位 / Verify contract price and unit of measure",
    "currency": "币种不同或缺失，金额无法核实 / Different or missing currencies; amount comparison unavailable",
    "document_relation": "补充或修正 PO / 发票编号对应关系 / Correct document references",
    "partial_pending": "部分批次尚未覆盖全部订单，余额无法核实 / Partial batch; remaining balance is unverified",
    "total_amount": "核查总金额是否包含税费、运费或折扣 / Check taxes, freight or discounts against stated total",
    "unverified": "比较依据不足，需补充资料 / Insufficient comparison evidence",
}


def reconcile(documents: list[Document], rules: Rules | None = None, cancel: Event | None = None) -> Result:
    # Exact products and 100k-row sums for accepted 20-digit numeric inputs.
    with localcontext() as context:
        context.prec = 64
        return _reconcile(documents, rules, cancel)


def _reconcile(documents: list[Document], rules: Rules | None = None, cancel: Event | None = None) -> Result:
    rules = rules or Rules()
    findings: list[Finding] = []
    checks = 0

    def emit(code, identifier="", left="", right="", diff="", lines=(), severity="warning", rule=""):
        sources: list[Source] = []
        for line in lines:
            for source in line.evidence.values():
                if source not in sources:
                    sources.append(source)
        findings.append(Finding(code=code, severity=severity, identifier=identifier,
                        left=str(left), right=str(right), difference=str(diff),
                        rule=rule or code, suggestion=TEXT[code], sources=sources))

    norm = key if rules.normalize_identifiers else lambda v: v or ""
    records = [(doc, line) for doc in documents for line in doc.lines]
    # Detect aliases within each document-kind namespace before building any
    # aggregate. A single spelling on each side may still match normally.
    identifier_fields = ("po_number", "invoice_number", "sku")
    identifier_index: dict[tuple, dict[str, list[Line]]] = defaultdict(lambda: defaultdict(list))
    blocked_identifiers: set[tuple[str, str]] = set()
    for doc, line in records:
        checkpoint(cancel)
        for field in identifier_fields:
            raw = getattr(line, field)
            if raw is None:
                continue
            token = norm(raw)
            if not key(raw):
                blocked_identifiers.add((field, token))
                emit("ambiguous_match", raw, right=field, lines=[line],
                     rule=f"{field}: identifier normalizes to empty; manual review required")
            else:
                identifier_index[(doc.kind, field, token)][raw].append(line)
    for (_, field, token), variants in identifier_index.items():
        if len(variants) > 1:
            blocked_identifiers.add((field, token))
            emit("ambiguous_match", token, left=" | ".join(sorted(variants)), right=field,
                 lines=[line for lines in variants.values() for line in lines],
                 rule=f"{field}: distinct raw identifiers collapse to one normalized identifier; aggregation blocked")

    def reliable_identifiers(line: Line) -> bool:
        return all((field, norm(getattr(line, field))) not in blocked_identifiers
                   for field in identifier_fields if getattr(line, field) is not None)

    duplicate_groups: set[tuple[str, str, str]] = set()
    invoice_files: dict[str, set[str]] = defaultdict(set)
    cross_document_seen: dict[tuple, tuple[str, Line]] = {}
    for doc in documents:
        checkpoint(cancel)
        if not doc.lines:
            emit("unverified", doc.path, rule="empty structured document")
        seen: dict[tuple, Line] = {}
        for line in doc.lines:
            checkpoint(cancel)
            ident = line.sku or line.invoice_number or line.po_number or "?"
            required = ["po_number", "sku", "quantity"]
            if doc.kind == Kind.INVOICE:
                required += ["invoice_number", "unit_price", "line_total", "currency"]
            if doc.kind == Kind.PO:
                required += ["unit_price", "currency"]
            missing = [f for f in required if getattr(line, f) is None]
            if missing:
                emit("missing_field", ident, right=", ".join(missing), lines=[line], rule="required fields")
            if line.quantity is not None and line.quantity < 0:
                emit("unverified", ident, right=line.quantity, lines=[line], rule="negative quantities / credit notes unsupported")
            fingerprint = tuple(getattr(line, f) for f in ("po_number", "invoice_number", "sku", "quantity", "unit_price", "line_total", "currency", "shipment_date"))
            cross_key = (doc.kind.value, fingerprint)
            previous = cross_document_seen.get(cross_key)
            if previous and previous[0] != doc.id:
                emit("duplicate_line", ident, lines=[previous[1], line], severity="error", rule="identical business line across documents")
                duplicate_groups.add((doc.kind.value, norm(line.po_number), norm(line.sku)))
            else:
                cross_document_seen[cross_key] = (doc.id, line)
            if fingerprint in seen:
                emit("duplicate_line", ident, lines=[seen[fingerprint], line], severity="error", rule="identical business line")
                duplicate_groups.add((doc.kind.value, norm(line.po_number), norm(line.sku)))
            else:
                seen[fingerprint] = line
            if (doc.kind == Kind.INVOICE and line.invoice_number and
                    ("invoice_number", norm(line.invoice_number)) not in blocked_identifiers):
                invoice_files[norm(line.invoice_number)].add(doc.id)
            if all(v is not None for v in (line.quantity, line.unit_price, line.line_total)):
                checks += 1
                expected = line.quantity * line.unit_price
                difference = line.line_total - expected
                if abs(difference) > rules.amount_tolerance:
                    emit("arithmetic", ident, expected, line.line_total, difference, [line], "error", "quantity × unit_price = line_total")
        # Header totals may be repeated per line; evaluate only within a single currency/reference.
        totals: dict[tuple, list[Line]] = defaultdict(list)
        for line in doc.lines:
            totals[(line.invoice_number if doc.kind == Kind.INVOICE else line.po_number, line.currency)].append(line)
        for (reference, currency), lines in totals.items():
            stated = {line.total_amount for line in lines if line.total_amount is not None}
            if not stated:
                continue
            if any(not reliable_identifiers(line) for line in lines):
                emit("unverified", reference or "?", lines=lines,
                     rule="ambiguous identifiers prevent reliable total aggregation")
                continue
            reference_currencies = {cur for ref, cur in totals if ref == reference}
            if len(stated) != 1 or not currency or len(reference_currencies) != 1 or any(line.line_total is None for line in lines):
                emit("unverified", reference or "?", lines=lines, rule="total requires one currency, one declared total and complete line amounts")
                continue
            checks += 1
            expected = sum((line.line_total for line in lines), Decimal(0))
            total = next(iter(stated))
            if abs(total - expected) > rules.amount_tolerance:
                emit("total_amount", reference or "?", expected, total, total - expected, lines, "error", "sum(line_total) = total_amount; exclusive of unspecified adjustments")
    for reference, files in invoice_files.items():
        if len(files) > 1:
            for doc, line in records:
                if doc.id in files:
                    duplicate_groups.add((doc.kind.value, norm(line.po_number), norm(line.sku)))
            emit("duplicate_invoice", reference, right=len(files),
                 lines=[l for d, l in records if d.id in files], severity="error", rule="invoice identifier appears in multiple files")

    def compare(left_kind: Kind, right_kind: Kind):
        nonlocal checks
        left_records = [(d, l) for d, l in records if d.kind == left_kind]
        right_records = [(d, l) for d, l in records if d.kind == right_kind]
        if not left_records or not right_records:
            emit("unverified", f"{left_kind.value} ↔ {right_kind.value}", rule="required document type unavailable")
            return
        # PO reference scopes all comparisons; invoice reference additionally scopes packing.
        def scope(line):
            return (norm(line.po_number), norm(line.invoice_number) if left_kind == Kind.INVOICE else "")
        left_groups: dict[tuple, list[Line]] = defaultdict(list)
        right_groups: dict[tuple, list[Line]] = defaultdict(list)
        partial_scopes = set()
        for doc, line in left_records:
            if not reliable_identifiers(line):
                continue
            if line.po_number and line.sku and (left_kind != Kind.INVOICE or line.invoice_number):
                left_groups[(scope(line), norm(line.sku))].append(line)
        left_scopes = {s for s, _ in left_groups}
        candidate_index: dict[tuple, list[tuple]] = defaultdict(list)
        for candidate_key in left_groups:
            candidate_index[candidate_key[0]].append(candidate_key)
        for doc, line in right_records:
            if not reliable_identifiers(line):
                continue
            if doc.partial:
                partial_scopes.add(scope(line))
            if not line.po_number or (left_kind == Kind.INVOICE and not line.invoice_number):
                emit("document_relation", line.sku or "?", lines=[line], rule="missing PO / invoice reference")
                continue
            if scope(line) not in left_scopes:
                emit("document_relation", line.po_number, right=line.invoice_number or "", lines=[line], rule="reference absent from comparison documents")
                continue
            if line.sku:
                right_groups[(scope(line), norm(line.sku))].append(line)
        used = set()
        for group_key, right_lines in right_groups.items():
            checkpoint(cancel)
            group_scope, sku = group_key
            left_lines = left_groups.get(group_key)
            if not left_lines:
                candidate_keys = candidate_index[group_scope]
                if rules.fuzzy_enabled and len(candidate_keys) > 2000:
                    emit("unverified", right_lines[0].sku, lines=right_lines,
                         rule="fuzzy scope exceeds 2000 candidates; explicit identifiers required")
                    continue
                candidates = [(k, left_groups[k]) for k in candidate_keys if rules.fuzzy_enabled
                              and SequenceMatcher(None, sku, k[1]).ratio() >= rules.fuzzy_threshold]
                if candidates:
                    emit("sku_mismatch" if len(candidates) == 1 else "ambiguous_match", right_lines[0].sku,
                         " | ".join(lines[0].sku or "" for _, lines in candidates), right_lines[0].sku,
                         lines=right_lines + [line for _, lines in candidates for line in lines], rule="fuzzy candidates only; never auto-approved")
                    used.update(k for k, _ in candidates)
                else:
                    emit("extra_invoice_item" if left_kind == Kind.PO else "unverified", right_lines[0].sku,
                         right=right_lines[0].sku, lines=right_lines, rule=f"{right_kind.value} item absent from {left_kind.value}")
                continue
            used.add(group_key)
            lines = left_lines + right_lines
            ident = right_lines[0].sku
            if any((k.value, group_scope[0], sku) in duplicate_groups for k in (left_kind, right_kind)):
                emit("unverified", ident, lines=lines, rule="duplicate rows prevent reliable quantity aggregation")
                continue
            if any(l.quantity is None or l.quantity < 0 for l in lines):
                emit("unverified", ident, lines=lines, rule="missing / negative quantity")
            else:
                checks += 1
                a = sum((l.quantity for l in left_lines), Decimal(0))
                b = sum((l.quantity for l in right_lines), Decimal(0))
                diff = b - a
                if abs(diff) > rules.quantity_tolerance:
                    if group_scope in partial_scopes and b < a:
                        emit("partial_pending", ident, a, b, diff, lines, "info", "declared partial batch: cumulative quantity ≤ reference")
                    else:
                        emit("quantity", ident, a, b, diff, lines, "error", f"{left_kind.value} ↔ {right_kind.value}: cumulative quantity")
            if left_kind == Kind.PO:
                currencies = {l.currency.strip().upper() if l.currency else None for l in lines}
                if len(currencies) != 1 or None in currencies:
                    emit("currency", ident, ", ".join(sorted(str(l.currency) for l in left_lines)),
                         ", ".join(sorted(str(l.currency) for l in right_lines)), lines=lines, rule="same explicit currency required; no FX conversion")
                    continue
                prices = {l.unit_price for l in left_lines}
                if len(prices) != 1 or None in prices or any(l.unit_price is None for l in right_lines):
                    emit("unverified", ident, lines=lines, rule="missing or ambiguous PO price")
                    continue
                expected = next(iter(prices))
                for line in right_lines:
                    checks += 1
                    if abs(line.unit_price - expected) > rules.amount_tolerance:
                        emit("unit_price", ident, expected, line.unit_price, line.unit_price - expected,
                             left_lines + [line], "error", "PO unit_price = Invoice unit_price in same currency")
        for group_key, lines in left_groups.items():
            if group_key not in used:
                partial = group_key[0] in partial_scopes
                emit("partial_pending" if partial else "missing_invoice_item", lines[0].sku,
                     left=lines[0].sku, lines=lines, severity="info" if partial else "warning",
                     rule=f"{left_kind.value} item missing from {right_kind.value}")

    compare(Kind.PO, Kind.INVOICE)
    compare(Kind.INVOICE, Kind.PACKING)
    conclusion = "review_required" if findings else "no_exceptions_in_checked_scope"
    return Result(created_at=datetime.now(timezone.utc).isoformat(), rules=rules, documents=documents,
                  findings=findings, checks=checks, conclusion=conclusion)
