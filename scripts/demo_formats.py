from pathlib import Path
from openpyxl import Workbook
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
from yuaudit.demo import create_demo

root = Path(__file__).resolve().parent.parent / "demo"
create_demo(root)
directory = root / "format-fixtures"
directory.mkdir(exist_ok=True)
data = [["PO Number", "SKU", "Quantity", "Unit Price", "Currency"],
        ["FORMAT-PO", "FORMAT-01", "3", "0.10", "USD"]]
book = Workbook()
for row in data:
    book.active.append(row)
book.save(directory / "PO.xlsx")
table = Table(data)
table.setStyle(TableStyle([("GRID", (0,0), (-1,-1), 1, colors.black)]))
SimpleDocTemplate(str(directory / "PO.pdf")).build([table])
