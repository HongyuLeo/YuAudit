from __future__ import annotations
import re
import unicodedata
from .models import Document, FIELDS, Line, MONEY_FIELDS, decimal_value

ALIASES = {
    "po_number": ["po number", "po", "purchase order", "purchase order number", "采购订单号", "订单号"],
    "invoice_number": ["invoice number", "invoice no", "invoice", "发票号", "发票编号"],
    "sku": ["sku", "item number", "item no", "item", "product code", "物料编码", "商品编号", "货号"],
    "description": ["product description", "description", "product", "品名", "产品描述"],
    "quantity": ["quantity", "qty", "数量", "装箱数量"],
    "unit_price": ["unit price", "price", "单价"],
    "line_total": ["line total", "amount", "extended price", "行金额", "金额"],
    "currency": ["currency", "ccy", "币种", "货币"],
    "supplier": ["supplier", "vendor", "供应商"],
    "shipment_date": ["shipment date", "ship date", "出货日期"],
    "total_amount": ["total amount", "grand total", "总金额"],
}


def key(text: str | None) -> str:
    return re.sub(r"[^\w]", "", unicodedata.normalize("NFKC", text or "").casefold()).replace("_", "")


def guess_mapping(headers: list[str]) -> dict[str, str]:
    lookup = {key(alias): field for field, aliases in ALIASES.items() for alias in [field, *aliases]}
    return {header: lookup[key(header)] for header in headers if key(header) in lookup}


def structure(doc: Document, cancel=None) -> Document:
    targets = list(doc.mapping.values())
    if len(set(targets)) != len(targets):
        raise ValueError("Multiple columns map to one field / 多列映射至同一字段")
    if any(field not in FIELDS for field in targets):
        raise ValueError("Unknown mapped field")
    lines = []
    for row in doc.rows:
        if cancel and cancel.is_set():
            from .parsers import Cancelled
            raise Cancelled()
        values = {}
        evidence = {}
        for column, field in doc.mapping.items():
            raw = row.values.get(column, "").strip()
            if not raw:
                continue
            try:
                values[field] = decimal_value(raw) if field in MONEY_FIELDS else raw
            except ValueError as exc:
                raise ValueError(f"{row.source.location()} | {column}: {exc}") from exc
            original = row.cells.get(column, row.source)
            evidence[field] = original.model_copy(update={"column": column, "raw": raw,
                         "corrected": original.original_raw is not None and raw != original.original_raw})
        if values:
            lines.append(Line(**values, evidence=evidence))
    doc.lines = lines
    return doc
