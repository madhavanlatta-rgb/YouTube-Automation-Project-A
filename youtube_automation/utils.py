import json
import re
import shutil
import subprocess
from pathlib import Path


def run_command(args: list[str], timeout: int = 300, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout, check=False)


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: Path, data: Any) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def ffprobe_json(path: Path) -> dict:
    result = run_command([
        "ffprobe", "-v", "error", "-show_entries", "stream=index,codec_type,codec_name,width,height,r_frame_rate,duration",
        "-show_entries", "format=duration,size", "-of", "json", str(path)
    ])
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr}")
    return json.loads(result.stdout)


def media_duration(path: Path) -> float:
    info = ffprobe_json(path)
    duration = info.get("format", {}).get("duration")
    if duration is None and info.get("streams"):
        duration = info["streams"][0].get("duration")
    if duration is None:
        raise RuntimeError(f"Could not determine duration for {path}")
    return float(duration)


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def slugify(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-").lower()
    return value or "item"


def sha256_file(path: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()
