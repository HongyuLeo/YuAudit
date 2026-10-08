from __future__ import annotations
import csv
from pathlib import Path
from threading import Event
from uuid import uuid4
from .models import Document, Kind, RawRow, Source
from .normalize import guess_mapping, key


class Cancelled(Exception):
    pass


def checkpoint(cancel: Event | None) -> None:
    if cancel and cancel.is_set():
        raise Cancelled("Cancelled / 已取消")


def guess_kind(path: str, headers: list[str]) -> Kind:
    name = Path(path).stem.casefold()
    if any(v in name for v in ("packing", "装箱", "packlist")):
        return Kind.PACKING
    if any(v in name for v in ("invoice", "发票")):
        return Kind.INVOICE
    if any(v in name for v in ("po", "purchase", "采购", "订单")):
        return Kind.PO
    if "invoice_number" in guess_mapping(headers).values():
        return Kind.INVOICE
    return Kind.PO


def headers_for(values: list) -> list[str]:
    headers = [str(v).strip() if v is not None else f"Column {i + 1}" for i, v in enumerate(values)]
    if len(set(headers)) != len(headers):
        raise ValueError("Duplicate column names / 列名重复，请修正源文件或导出为 CSV")
    return headers


def read_document(path: str, kind: Kind | None = None, cancel: Event | None = None) -> Document:
    file = Path(path).resolve()
    if not file.is_file():
        raise ValueError("File not found / 文件不存在")
    if file.stat().st_size > 100_000_000:
        raise ValueError("File exceeds 100 MB / 单文件超过 100 MB，请拆分")
    rows: list[RawRow] = []
    headers: list[str] = []
    warnings: list[str] = []

    def append(values, source: Source, columns: list[str], cells=None):
        checkpoint(cancel)
        if len(rows) >= 100000:
            raise ValueError("100,000 row limit / 首版最多支持十万行，请拆分文件")
        if not any(v is not None and str(v).strip() for v in values):
            return
        if len(values) > len(columns) and any(v not in (None, "") for v in values[len(columns):]):
            raise ValueError(f"{source.location()}: extra cells / 数据列超过表头列数")
        data = {h: str(v) if v is not None else "" for h, v in zip(columns, values)}
        cell_sources = {h: (cells or {}).get(h, source).model_copy(update={"column": h, "raw": v, "original_raw": v})
                        for h, v in data.items()}
        rows.append(RawRow(values=data, source=source, cells=cell_sources))

    suffix = file.suffix.lower()
    if suffix == ".csv":
        encoding = None
        for candidate in ("utf-8-sig", "gbk"):
            try:
                with file.open(encoding=candidate, newline="") as stream:
                    while stream.read(65536):
                        checkpoint(cancel)
                encoding = candidate
                break
            except UnicodeDecodeError:
                continue
        if encoding is None:
            raise ValueError("Expected UTF-8 / GBK CSV / CSV 编码不支持")
        with file.open(encoding=encoding, newline="") as stream:
            sample = stream.read(8192)
            stream.seek(0)
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
            except csv.Error:
                dialect = csv.excel
            reader = csv.reader(stream, dialect)
            headers = headers_for(next(reader, []))
            for values in reader:
                append(values, Source(file=str(file), row=reader.line_num), headers)
    elif suffix == ".xlsx":
        from openpyxl import load_workbook
        book = load_workbook(file, read_only=True, data_only=True)
        try:
            for sheet in book:
                checkpoint(cancel)
                iterator = sheet.iter_rows()
                columns = []
                for cells in iterator:
                    if any(cell.value is not None for cell in cells):
                        columns = headers_for([cell.value for cell in cells])
                        break
                for column in columns:
                    if column not in headers:
                        headers.append(column)
                for cells in iterator:
                    values = [cell.value for cell in cells]
                    source = Source(file=str(file), sheet=sheet.title, row=cells[0].row if cells else None)
                    append(values, source, columns)
            warnings.append("Excel formulas require saved cached values; blank cells stay missing / Excel 公式需要已保存的计算缓存，空值不补填")
        finally:
            book.close()
    elif suffix == ".pdf":
        import pdfplumber
        with pdfplumber.open(file) as pdf:
            any_text = False
            for page in pdf.pages:
                checkpoint(cancel)
                text = page.extract_text() or ""
                any_text |= bool(text.strip())
                for table in page.find_tables():
                    data = table.extract()
                    if not data:
                        continue
                    columns = headers_for(data[0])
                    if not guess_mapping(columns):
                        continue
                    for column in columns:
                        if column not in headers:
                            headers.append(column)
                    for index, values in enumerate(data[1:], 1):
                        if [str(v).strip() if v is not None else "" for v in values] == columns:
                            continue
                        boxes = table.rows[index].cells
                        cells = {h: Source(file=str(file), page=page.page_number, row=index + 1,
                                 column=h, bbox=box) for h, box in zip(columns, boxes) if box}
                        append(values, Source(file=str(file), page=page.page_number, row=index + 1,
                                             bbox=table.bbox), columns, cells)
            if not any_text:
                raise ValueError("Scanned PDF: OCR extension is not installed / 扫描 PDF：未安装 OCR 扩展，请提供文本 PDF、Excel 或 CSV")
            if not rows:
                raise ValueError("No supported table found in text PDF / 文本 PDF 未找到带表头的可识别表格，请转换为 Excel/CSV；非结构化提取尚不支持")
        warnings.append("PDF extraction requires visual verification / PDF 表格提取请对照原件确认")
    else:
        raise ValueError("Supported: .xlsx, .csv, .pdf / 不支持此文件格式")
    if not rows:
        raise ValueError("No data rows / 文件没有数据行")
    return Document(id=uuid4().hex, path=str(file), kind=kind or guess_kind(str(file), headers),
                    rows=rows, headers=headers, mapping=guess_mapping(headers), warnings=warnings)
