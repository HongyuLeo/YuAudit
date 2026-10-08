from __future__ import annotations

from decimal import Decimal, InvalidOperation
from enum import Enum
from pathlib import Path
from typing import Any
import re

from pydantic import BaseModel, Field, ConfigDict, field_validator


class Kind(str, Enum):
    PO = "PO"
    INVOICE = "Invoice"
    PACKING = "Packing List"


FIELDS = ("po_number", "invoice_number", "sku", "description", "quantity",
          "unit_price", "line_total", "currency", "supplier", "shipment_date", "total_amount")
MONEY_FIELDS = {"quantity", "unit_price", "line_total", "total_amount"}


def decimal_value(value: Any) -> Decimal | None:
    if value is None or str(value).strip() == "":
        return None
    text = str(value).strip()
    # Explicit decimal point convention. European decimal commas need manual correction.
    if not re.fullmatch(r"[+-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?", text):
        raise ValueError(f"Invalid decimal / 数值格式无效: {text}")
    try:
        result = Decimal(text.replace(",", ""))
    except InvalidOperation as exc:
        raise ValueError(text) from exc
    if not result.is_finite():
        raise ValueError("Non-finite decimal")
    if len(result.as_tuple().digits) > 20 or result.as_tuple().exponent < -8:
        raise ValueError("Maximum 20 significant digits and 8 decimal places / 最多 20 位有效数字、8 位小数")
    return result


class Source(BaseModel):
    file: str
    sheet: str | None = None
    row: int | None = None
    page: int | None = None
    column: str | None = None
    bbox: tuple[float, float, float, float] | None = None
    raw: str = ""
    original_raw: str | None = None
    corrected: bool = False

    def location(self) -> str:
        return f"{Path(self.file).name} | " + (
            f"page {self.page}" if self.page else f"{self.sheet or 'CSV'} : {self.row}") + (
            f" | {self.column}" if self.column else "")


class Line(BaseModel):
    model_config = ConfigDict(validate_assignment=True, allow_inf_nan=False)
    po_number: str | None = None
    invoice_number: str | None = None
    sku: str | None = None
    description: str | None = None
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    line_total: Decimal | None = None
    currency: str | None = None
    supplier: str | None = None
    shipment_date: str | None = None
    total_amount: Decimal | None = None
    evidence: dict[str, Source] = Field(default_factory=dict)

    @field_validator("quantity", "unit_price", "line_total", "total_amount")
    @classmethod
    def bounded_numbers(cls, value):
        if value is not None and (not value.is_finite() or len(value.as_tuple().digits) > 20 or value.as_tuple().exponent < -8):
            raise ValueError("Numeric input exceeds supported precision")
        return value


class RawRow(BaseModel):
    values: dict[str, str]
    source: Source
    cells: dict[str, Source] = Field(default_factory=dict)


class Document(BaseModel):
    id: str
    path: str
    kind: Kind
    rows: list[RawRow] = Field(default_factory=list)
    headers: list[str] = Field(default_factory=list)
    mapping: dict[str, str] = Field(default_factory=dict)
    lines: list[Line] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    partial: bool = False


class Rules(BaseModel):
    model_config = ConfigDict(validate_assignment=True)
    amount_tolerance: Decimal = Decimal("0.01")
    quantity_tolerance: Decimal = Decimal("0")
    fuzzy_threshold: float = Field(default=0.80, ge=0.5, le=1)
    fuzzy_enabled: bool = True
    normalize_identifiers: bool = True

    @field_validator("amount_tolerance", "quantity_tolerance")
    @classmethod
    def valid_tolerance(cls, v: Decimal) -> Decimal:
        if not v.is_finite() or v < 0:
            raise ValueError("Tolerance must be finite and nonnegative")
        return v


class Finding(BaseModel):
    code: str
    severity: str
    identifier: str
    left: str = ""
    right: str = ""
    difference: str = ""
    rule: str
    suggestion: str
    sources: list[Source] = Field(default_factory=list)
    status: str = "open"
    review_note: str = ""


class Result(BaseModel):
    version: str = "0.1.0"
    created_at: str
    rules: Rules
    documents: list[Document]
    findings: list[Finding]
    checks: int = 0
    conclusion: str = "review_required"
    ai_summary: str | None = None
