"""Vector-inspired application icon; generated from code, no external art."""
from pathlib import Path
from PIL import Image, ImageDraw

root = Path(__file__).resolve().parent.parent
image = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
draw = ImageDraw.Draw(image)
draw.rounded_rectangle((8, 8, 248, 248), radius=52, fill="#1e293b")
draw.rounded_rectangle((66, 42, 184, 212), radius=12, fill="#f8fafc")
draw.rectangle((86, 75, 154, 83), fill="#94a3b8")
draw.rectangle((86, 101, 148, 109), fill="#94a3b8")
draw.line([(88, 154), (115, 179), (169, 131)], fill="#334155", width=15)
image.save(root / "assets" / "icon.png")
image.save(root / "assets" / "icon.ico", sizes=[(16,16), (32,32), (48,48), (64,64), (128,128), (256,256)])
