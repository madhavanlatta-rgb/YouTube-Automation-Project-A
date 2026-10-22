from pathlib import Path

from .models import NarrationSegment
from .utils import ensure_dir


def _timestamp(seconds: float) -> str:
    if seconds < 0:
        seconds = 0.0
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds - int(seconds)) * 1000))
    if millis == 1000:
        millis = 0
        secs += 1
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def write_srt(path: Path, segments: list[NarrationSegment]) -> Path:
    ensure_dir(path.parent)
    lines: list[str] = []
    for index, segment in enumerate(segments, start=1):
        lines.append(str(index))
        lines.append(f"{_timestamp(segment.start_sec)} --> {_timestamp(segment.end_sec)}")
        lines.append(segment.text.strip())
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def parse_srt(path: Path) -> list[dict]:
    entries = []
    blocks = path.read_text(encoding="utf-8").strip().split("\n\n")
    for block in blocks:
        rows = block.strip().splitlines()
        if len(rows) < 3:
            continue
        timing = rows[1]
        start_text, end_text = [part.strip() for part in timing.split("-->")]
        entries.append({"index": rows[0], "start": start_text, "end": end_text, "text": " ".join(rows[2:])})
    return entries


def validate_srt(path: Path, max_duration_sec: float) -> list[str]:
    errors: list[str] = []
    if not path.exists():
        return ["Subtitle file is missing"]
    try:
        entries = parse_srt(path)
    except Exception as exc:  # noqa: BLE001
        return [f"Could not parse SRT: {exc}"]
    if not entries:
        errors.append("Subtitle file has no entries")
    for entry in entries:
        if not entry["text"].strip():
            errors.append(f"Empty subtitle entry {entry['index']}")
    # Basic timestamp ordering check.
    previous_end = 0.0
    def to_seconds(value: str) -> float:
        h, m, s = value.split(":")
        sec, ms = s.split(",")
        return int(h) * 3600 + int(m) * 60 + int(sec) + int(ms) / 1000.0
    for entry in entries:
        start = to_seconds(entry["start"])
        end = to_seconds(entry["end"])
        if end <= start:
            errors.append(f"Invalid timing in subtitle {entry['index']}")
        if start < previous_end - 0.05:
            errors.append(f"Overlapping subtitles at entry {entry['index']}")
        previous_end = max(previous_end, end)
    if entries:
        last_end = to_seconds(entries[-1]["end"])
        if last_end > max_duration_sec + 2:
            errors.append("Subtitle timing exceeds maximum duration")
    return errors
