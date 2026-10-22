from pathlib import Path

from .utils import ensure_dir, run_command, media_duration


def assemble_video(frames_dir: Path, audio_path: Path, srt_path: Path, output_path: Path, fps: int) -> Path:
    ensure_dir(output_path.parent)
    frame_pattern = frames_dir / "frame_%06d.png"
    # Burn SRT captions directly into the video for visible, synchronized captions.
    vf = f"subtitles={srt_path.as_posix()}"
    args = [
        "ffmpeg", "-y",
        "-framerate", str(fps),
        "-i", str(frame_pattern),
        "-i", str(audio_path),
        "-vf", vf,
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        "-shortest",
        str(output_path),
    ]
    result = run_command(args, timeout=1800)
    if result.returncode != 0 or not output_path.exists():
        raise RuntimeError(f"Video assembly failed: {result.stderr}")
    return output_path


def decode_check(path: Path) -> list[str]:
    errors = []
    result = run_command(["ffmpeg", "-v", "error", "-i", str(path), "-f", "null", "-"], timeout=600)
    if result.returncode != 0:
        errors.append(f"Decode check failed: {result.stderr}")
    if result.stderr.strip():
        errors.append(f"Decoder warnings: {result.stderr.strip()[:500]}")
    return errors
