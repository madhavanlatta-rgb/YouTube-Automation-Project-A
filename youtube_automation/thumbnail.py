from pathlib import Path

from PIL import Image, ImageDraw

from .config import RenderConfig
from .utils import ensure_dir


INK = (42, 30, 20)
PAPER = (232, 214, 180)
ACCENT = (118, 70, 36)
RED = (160, 50, 35)


def _font(size):
    try:
        from PIL import ImageFont
        return ImageFont.truetype("/usr/share/fonts/Adwaita/AdwaitaSans-Regular.ttf", size)
    except Exception:  # noqa: BLE001
        from PIL import ImageFont
        return ImageFont.load_default(size=size)


def create_thumbnail(title: str, output_path: Path, config: RenderConfig) -> Path:
    ensure_dir(output_path.parent)
    w, h = config.width, config.height
    img = Image.new("RGB", (w, h), PAPER)
    draw = ImageDraw.Draw(img)
    # Paper texture
    for y in range(0, h, 36):
        draw.line((0, y, w, y), fill=(210, 190, 155), width=1)
    cx = int(w * 0.62)
    crank_y = 500
    # Simple engine cutaway
    draw.rectangle((cx - 90, 180, cx + 90, 470), outline=INK, width=5)
    draw.rectangle((cx - 110, 145, cx + 110, 182), outline=INK, width=5, fill=(205, 185, 150))
    draw.rectangle((cx - 70, 285, cx + 70, 335), outline=INK, width=4, fill=(190, 170, 135))
    draw.ellipse((cx - 62, crank_y - 62, cx + 62, crank_y + 62), outline=INK, width=5)
    draw.line((cx - 45, 100, cx - 45, 180), fill=INK, width=4)
    draw.line((cx + 45, 100, cx + 45, 180), fill=INK, width=4)
    draw.line((cx, 95, cx, 145), fill=RED, width=4)
    # Title block
    title_font = _font(62)
    subtitle_font = _font(30)
    draw.text((55, 95), "How a", font=_font(42), fill=INK)
    draw.text((55, 145), "Four-Stroke", font=title_font, fill=INK)
    draw.text((55, 215), "Engine Works", font=title_font, fill=ACCENT)
    draw.text((55, 300), "Intake  •  Compression  •  Power  •  Exhaust", font=subtitle_font, fill=INK)
    # Border
    draw.rectangle((8, 8, w - 9, h - 9), outline=ACCENT, width=4)
    img.save(output_path)
    return output_path
