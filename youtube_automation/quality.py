import hashlib
import json
import re
from pathlib import Path

from .utils import ensure_dir, ffprobe_json, media_duration, run_command, write_json


def _frame_hashes(frames_dir: Path, step: int = 10) -> set[str]:
    hashes = set()
    frames = sorted(frames_dir.glob("frame_*.png"))
    for path in frames[::step]:
        hashes.add(hashlib.sha256(path.read_bytes()).hexdigest())
    return hashes


def _silence_max(audio_path: Path) -> float:
    result = run_command(["ffmpeg", "-i", str(audio_path), "-af", "silencedetect=noise=-35dB:d=2", "-f", "null", "-"], timeout=300)
    text = result.stderr
    durations = [float(x) for x in re.findall(r"silence_duration:\s*([0-9.]+)", text)]
    return max(durations) if durations else 0.0


def _max_volume(audio_path: Path) -> float:
    result = run_command(["ffmpeg", "-i", str(audio_path), "-af", "volumedetect", "-f", "null", "-"], timeout=300)
    text = result.stderr
    match = re.search(r"max_volume:\s*(-?[0-9.]+)\s*dB", text)
    return float(match.group(1)) if match else -100.0


def run_quality_checks(output_dir: Path, max_duration_sec: float) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    evidence: dict = {}

    video_path = output_dir / "final.mp4"
    audio_path = output_dir / "audio" / "narration.wav"
    srt_path = output_dir / "subtitles.srt"
    thumb_path = output_dir / "thumbnail.png"
    frames_dir = output_dir / "frames"

    # Video
    if not video_path.exists():
        errors.append("Final video is missing")
    else:
        info = ffprobe_json(video_path)
        duration = float(info["format"]["duration"])
        evidence["video_duration_sec"] = duration
        if duration <= 0:
            errors.append("Video duration is zero")
        if duration > max_duration_sec:
            errors.append(f"Video duration {duration:.2f}s exceeds maximum {max_duration_sec:.2f}s")
        streams = info.get("streams", [])
        video_streams = [s for s in streams if s.get("codec_type") == "video"]
        audio_streams = [s for s in streams if s.get("codec_type") == "audio"]
        if not video_streams:
            errors.append("No video stream found")
        if not audio_streams:
            errors.append("No audio stream found")
        evidence["video_streams"] = len(video_streams)
        evidence["audio_streams"] = len(audio_streams)
        if video_streams:
            evidence["resolution"] = f"{video_streams[0].get('width')}x{video_streams[0].get('height')}"
        decode_errors = []
        result = run_command(["ffmpeg", "-v", "error", "-i", str(video_path), "-f", "null", "-"], timeout=600)
        if result.returncode != 0:
            decode_errors.append(result.stderr.strip())
        if result.stderr.strip():
            decode_errors.append(result.stderr.strip()[:500])
        if decode_errors:
            errors.append("Video decode check reported errors")
        evidence["decode_stderr"] = result.stderr.strip()[:500]

    # Audio
    if audio_path.exists():
        audio_duration = media_duration(audio_path)
        evidence["audio_duration_sec"] = audio_duration
        silence_max = _silence_max(audio_path)
        evidence["max_silence_sec"] = silence_max
        if silence_max > 4.0:
            errors.append(f"Excessive silence detected: {silence_max:.2f}s")
        max_volume = _max_volume(audio_path)
        evidence["max_volume_db"] = max_volume
        if max_volume >= -0.1:
            warnings.append(f"Audio may be clipping (max volume {max_volume} dB)")
    else:
        errors.append("Narration audio is missing")

    # Subtitles
    if srt_path.exists():
        from .subtitles import validate_srt
        sub_errors = validate_srt(srt_path, max_duration_sec)
        if sub_errors:
            errors.extend(sub_errors)
        from .subtitles import parse_srt
        evidence["subtitle_entries"] = len(parse_srt(srt_path))
    else:
        errors.append("Subtitle file is missing")

    # Thumbnail
    if thumb_path.exists():
        from PIL import Image
        with Image.open(thumb_path) as im:
            evidence["thumbnail_size"] = f"{im.width}x{im.height}"
            if (im.width, im.height) != (1280, 720):
                warnings.append(f"Thumbnail dimensions are {im.width}x{im.height}, expected 1280x720")
    else:
        errors.append("Thumbnail is missing")

    # Frames
    if frames_dir.exists():
        frames = list(frames_dir.glob("frame_*.png"))
        evidence["frame_count"] = len(frames)
        if len(frames) == 0:
            errors.append("No rendered frames found")
        hashes = _frame_hashes(frames_dir)
        evidence["unique_sampled_frames"] = len(hashes)
        if len(hashes) < 5:
            errors.append("Rendered frames appear static or repeated")
    else:
        errors.append("Frames directory is missing")

    # Scene plan
    scene_plan_path = output_dir / "scene_plan.json"
    if scene_plan_path.exists():
        scene_plan = json.loads(scene_plan_path.read_text(encoding="utf-8"))
        scenes = scene_plan.get("scenes", [])
        evidence["scene_count"] = len(scenes)
        if not scenes:
            errors.append("Scene plan has no scenes")
        if len({s.get("title") for s in scenes}) != len(scenes):
            warnings.append("Duplicate scene titles detected")
        for scene in scenes:
            if not scene.get("visual", "").strip():
                errors.append(f"Scene {scene.get('id')} has no visual direction")
            if not scene.get("narration", "").strip():
                errors.append(f"Scene {scene.get('id')} has no narration")
    else:
        warnings.append("Scene plan is missing")

    # Research / claims
    research_path = output_dir / "research.json"
    if research_path.exists():
        research = json.loads(research_path.read_text(encoding="utf-8"))
        unsupported = [c["id"] for c in research.get("claims", []) if c.get("status") == "unsupported"]
        unverified = [c["id"] for c in research.get("claims", []) if c.get("status") == "unverified"]
        if unsupported:
            errors.append("Unsupported claims: " + ", ".join(unsupported))
        if unverified:
            warnings.append("Unverified claims: " + ", ".join(unverified))
        evidence["source_count"] = len(research.get("sources", []))
        if len(research.get("sources", [])) == 0:
            warnings.append("No research sources recorded")
    else:
        warnings.append("Research file is missing")

    status = "PASS" if not errors else "FAIL"
    report = {
        "status": status,
        "errors": errors,
        "warnings": warnings,
        "evidence": evidence,
    }
    write_json(output_dir / "quality_report.json", report)
    # Markdown
    md = ["# Quality Report", "", f"Status: **{status}**", "", "## Errors"]
    md += [f"- {e}" for e in errors] if errors else ["- None"]
    md += ["", "## Warnings"]
    md += [f"- {w}" for w in warnings] if warnings else ["- None"]
    md += ["", "## Evidence"]
    for key, value in evidence.items():
        md.append(f"- {key}: {value}")
    (output_dir / "quality_report.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return report
