import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .config import RenderConfig
from .models import Script
from .utils import ensure_dir


INK = (52, 38, 24)
PAPER = (236, 220, 188)
PAPER_DARK = (214, 194, 156)
ACCENT = (110, 72, 40)
RED = (150, 45, 35)
BLUE = (45, 75, 135)
GRAY = (95, 90, 82)


def _font(size: int):
    try:
        return ImageFont.truetype("/usr/share/fonts/Adwaita/AdwaitaSans-Regular.ttf", size)
    except Exception:  # noqa: BLE001
        return ImageFont.load_default(size=size)


FONT_TITLE = _font(34)
FONT_LABEL = _font(20)
FONT_SMALL = _font(16)
FONT_CAPTION = _font(22)


def _smoothstep(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return value * value * (3 - 2 * value)


def _wrap(text: str, width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = (current + " " + word).strip()
        if len(candidate) <= width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _paper(draw: ImageDraw.ImageDraw, w: int, h: int) -> None:
    draw.rectangle((0, 0, w, h), fill=PAPER)
    for y in range(0, h, 42):
        draw.line((0, y, w, y), fill=PAPER_DARK, width=1)
    for x in range(0, w, 42):
        draw.line((x, 0, x, h), fill=PAPER_DARK, width=1)


def _title(draw, text: str, w: int) -> None:
    draw.text((42, 30), text, font=FONT_TITLE, fill=INK)
    draw.line((42, 72, w - 42, 72), fill=ACCENT, width=2)


def _caption(draw, text: str, w: int, h: int) -> None:
    lines = _wrap(text, 78)
    y = h - 34 * len(lines) - 24
    for line in lines:
        draw.text((42, y), line, font=FONT_CAPTION, fill=INK)
        y += 34


def _label(draw, x: int, y: int, text: str, color=INK) -> None:
    draw.text((x, y), text, font=FONT_LABEL, fill=color)


def _slider_piston_y(theta: float, crank_y: float, r: float = 72, rod: float = 210) -> float:
    crank_x_offset = r * math.sin(theta)
    crank_y_offset = -r * math.cos(theta)
    crank_pin_y = crank_y + crank_y_offset
    horizontal = r * math.sin(theta)
    vertical = math.sqrt(max(rod * rod - horizontal * horizontal, 1.0))
    return crank_pin_y - vertical


def _draw_engine_base(draw, cx: int, crank_y: int, piston_y: float, intake_open: float, exhaust_open: float, spark: bool = False, crank_angle: float = 0.0) -> None:
    # Cylinder walls
    draw.rectangle((cx - 78, 150, cx + 78, 470), outline=INK, width=4)
    # Cylinder head
    draw.rectangle((cx - 92, 118, cx + 92, 152), outline=INK, width=4, fill=PAPER_DARK)
    # Intake valve (left)
    intake_stem_top = 70
    intake_head_y = 150 + int(28 * intake_open)
    draw.line((cx - 42, intake_stem_top, cx - 42, intake_head_y), fill=INK, width=3)
    draw.ellipse((cx - 52, intake_head_y - 6, cx - 32, intake_head_y + 6), outline=INK, width=2, fill=PAPER)
    # Exhaust valve (right)
    exhaust_head_y = 150 + int(28 * exhaust_open)
    draw.line((cx + 42, intake_stem_top, cx + 42, exhaust_head_y), fill=INK, width=3)
    draw.ellipse((cx + 32, exhaust_head_y - 6, cx + 52, exhaust_head_y + 6), outline=INK, width=2, fill=PAPER)
    # Spark plug
    draw.line((cx, 92, cx, 132), fill=RED, width=3)
    draw.ellipse((cx - 7, 128, cx + 7, 142), outline=RED, width=2)
    if spark:
        draw.ellipse((cx - 12, 145, cx + 12, 165), fill=(255, 210, 90), outline=RED, width=2)
    # Piston
    piston_top = int(piston_y)
    draw.rectangle((cx - 58, piston_top, cx + 58, piston_top + 52), outline=INK, width=3, fill=PAPER_DARK)
    draw.line((cx - 45, piston_top + 12, cx + 45, piston_top + 12), fill=ACCENT, width=1)
    # Connecting rod
    piston_center = (cx, piston_top + 26)
    crank_pin = (cx + 72 * math.sin(crank_angle), crank_y - 72 * math.cos(crank_angle))
    draw.line((piston_center[0], piston_center[1], crank_pin[0], crank_pin[1]), fill=ACCENT, width=4)
    draw.ellipse((crank_pin[0]-8, crank_pin[1]-8, crank_pin[0]+8, crank_pin[1]+8), fill=ACCENT)
    # Crankshaft
    draw.ellipse((cx - 55, crank_y - 55, cx + 55, crank_y + 55), outline=INK, width=4)
    draw.ellipse((cx - 12, crank_y - 12, cx + 12, crank_y + 12), fill=INK)
    # Labels
    _label(draw, cx - 150, 125, "intake valve")
    _label(draw, cx + 95, 125, "exhaust valve")
    _label(draw, cx + 95, 260, "cylinder")
    _label(draw, cx - 165, int(piston_y) + 10, "piston")
    _label(draw, cx + 95, crank_y - 10, "crankshaft")


def render_animation(script: Script, output_dir: Path, config: RenderConfig, start_frame: int = 0, end_frame: int | None = None) -> Path:
    frames_dir = ensure_dir(output_dir / "frames")
    w, h = config.width, config.height
    scenes = script.scenes
    total_duration = sum(s.duration_sec for s in scenes)
    total_frames = int(total_duration * config.fps) + 1
    # Precompute scene boundaries
    boundaries = []
    cursor = 0.0
    for scene in scenes:
        boundaries.append((cursor, cursor + scene.duration_sec, scene))
        cursor += scene.duration_sec

    def scene_at(t: float):
        for start, end, scene in boundaries:
            if start <= t < end:
                return start, end, scene
        return boundaries[-1]

    if end_frame is None:
        end_frame = total_frames
    start_frame = max(0, start_frame)
    end_frame = min(total_frames, end_frame)
    for frame_index in range(start_frame, end_frame):
        t = frame_index / config.fps
        start, end, scene = scene_at(t)
        local = (t - start) / max(scene.duration_sec, 0.001)
        p = _smoothstep(local)
        img = Image.new("RGB", (w, h), PAPER)
        draw = ImageDraw.Draw(img)
        _paper(draw, w, h)
        _title(draw, scene.title, w)

        cx = w // 2
        crank_y = 560
        if scene.id in {"intake"}:
            theta = p * math.pi
            piston_y = _slider_piston_y(theta, crank_y)
            _draw_engine_base(draw, cx, crank_y, piston_y, 1.0, 0.0, crank_angle=theta)
            # incoming air arrows
            for i in range(3):
                yy = 120 + i * 18
                draw.line((cx - 130, yy, cx - 95, yy + 20), fill=BLUE, width=2)
        elif scene.id in {"compression"}:
            theta = math.pi + p * math.pi
            piston_y = _slider_piston_y(theta, crank_y)
            _draw_engine_base(draw, cx, crank_y, piston_y, 0.0, 0.0, crank_angle=theta)
            _label(draw, cx - 100, 250, "compressed charge", ACCENT)
        elif scene.id in {"power"}:
            theta = p * math.pi
            piston_y = _slider_piston_y(theta, crank_y)
            spark = p < 0.25
            _draw_engine_base(draw, cx, crank_y, piston_y, 0.0, 0.0, spark=spark, crank_angle=theta)
            if p < 0.35:
                draw.text((cx - 30, 160), "IGNITION", font=FONT_LABEL, fill=RED)
        elif scene.id in {"exhaust"}:
            theta = math.pi + p * math.pi
            piston_y = _slider_piston_y(theta, crank_y)
            _draw_engine_base(draw, cx, crank_y, piston_y, 0.0, 1.0, crank_angle=theta)
            # exhaust flow
            for i in range(4):
                x = cx + 95 + i * 18
                draw.line((x, 135, x + 20, 120), fill=GRAY, width=2)
        elif scene.id == "hook":
            theta = (t * 0.35) % (2 * math.pi)
            piston_y = _slider_piston_y(theta, crank_y)
            _draw_engine_base(draw, cx, crank_y, piston_y, 0.0, 0.0, crank_angle=theta)
            _label(draw, 50, 100, "Intake -> Compression -> Power -> Exhaust", ACCENT)
        elif scene.id == "components":
            # Exploded view: draw engine parts separated
            _draw_engine_base(draw, cx, crank_y, 300, 0.0, 0.0)
            _label(draw, 60, 120, "Exploded view: cylinder, piston, rod, crankshaft, valves, spark plug", ACCENT)
        elif scene.id == "timing":
            theta = (t * 0.8) % (2 * math.pi)
            intake_open = 1.0 if 1.2 < (theta % (2 * math.pi)) < 2.6 else 0.0
            exhaust_open = 1.0 if 4.0 < (theta % (2 * math.pi)) < 5.6 else 0.0
            piston_y = _slider_piston_y(theta % math.pi, crank_y)
            _draw_engine_base(draw, cx, crank_y, piston_y, intake_open, exhaust_open)
            _label(draw, 50, 100, "Camshaft timing controls valve lift", ACCENT)
            # camshaft indicator
            cam_angle = theta
            cam_x = cx - 150
            cam_y = 250
            draw.ellipse((cam_x - 40, cam_y - 40, cam_x + 40, cam_y + 40), outline=INK, width=3)
            px = cam_x + int(30 * math.cos(cam_angle))
            py = cam_y + int(30 * math.sin(cam_angle))
            draw.line((cam_x, cam_y, px, py), fill=RED, width=4)
        elif scene.id == "reliability":
            theta = (t * 0.4) % (2 * math.pi)
            piston_y = _slider_piston_y(theta % math.pi, crank_y)
            _draw_engine_base(draw, cx, crank_y, piston_y, 0.0, 0.0, crank_angle=theta)
            _label(draw, 55, 110, "Heat, friction, sealing, cooling, and lubrication decide reliability", ACCENT)
            # heat arrows
            for i in range(5):
                x = cx - 120 + i * 45
                draw.line((x, 100, x, 70), fill=RED, width=2)
        else:
            theta = (t * 0.4) % (2 * math.pi)
            piston_y = _slider_piston_y(theta % math.pi, crank_y)
            _draw_engine_base(draw, cx, crank_y, piston_y, 0.0, 0.0, crank_angle=theta)
            _label(draw, 55, 110, "Cars, motorcycles, generators, and aircraft use this cycle", ACCENT)

        _caption(draw, scene.visual, w, h)
        # progress bar
        progress = t / total_duration
        draw.rectangle((42, h - 14, 42 + int((w - 84) * progress), h - 6), fill=ACCENT)

        frame_path = frames_dir / f"frame_{frame_index:06d}.png"
        img.save(frame_path)

    return frames_dir
