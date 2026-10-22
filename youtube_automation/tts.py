import subprocess
from dataclasses import asdict
from pathlib import Path

from .config import TTSConfig
from .models import NarrationSegment, Script
from .utils import ensure_dir, media_duration, run_command, split_sentences, write_json


def synthesize_sentence(text: str, output_path: Path, config: TTSConfig) -> Path:
    ensure_dir(output_path.parent)
    args = [
        "espeak-ng",
        "-v", config.voice,
        "-s", str(config.rate),
        "-p", str(config.pitch),
        "-w", str(output_path),
        text,
    ]
    result = run_command(args, timeout=120)
    if result.returncode != 0 or not output_path.exists() or output_path.stat().st_size == 0:
        raise RuntimeError(f"espeak-ng failed for {text!r}: {result.stderr}")
    return output_path


def build_narration(script: Script, output_dir: Path, config: TTSConfig) -> tuple[list[NarrationSegment], Path]:
    audio_dir = ensure_dir(output_dir / "audio" / "segments")
    segments: list[NarrationSegment] = []
    concat_list = output_dir / "audio" / "concat.txt"
    lines: list[str] = []
    cursor = 0.0
    index = 0
    for scene in script.scenes:
        for sentence in split_sentences(scene.narration):
            index += 1
            seg_id = f"{scene.id}-{index:03d}"
            path = audio_dir / f"{seg_id}.wav"
            synthesize_sentence(sentence, path, config)
            duration = media_duration(path)
            segment = NarrationSegment(seg_id, sentence, path, duration, cursor, cursor + duration)
            segments.append(segment)
            cursor += duration
            lines.append(f"file '{path.resolve().as_posix()}'")
    concat_list.write_text("\n".join(lines) + "\n", encoding="utf-8")
    raw_path = output_dir / "audio" / "narration_raw.wav"
    result = run_command([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list),
        "-c:a", "pcm_s16le", str(raw_path)
    ], timeout=300)
    if result.returncode != 0 or not raw_path.exists():
        raise RuntimeError(f"Audio concatenation failed: {result.stderr}")
    normalized_path = output_dir / "audio" / "narration.wav"
    result = run_command([
        "ffmpeg", "-y", "-i", str(raw_path),
        "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
        "-ar", "44100", "-ac", "1", str(normalized_path)
    ], timeout=300)
    if result.returncode != 0 or not normalized_path.exists():
        raise RuntimeError(f"Audio normalization failed: {result.stderr}")
    # Keep durations aligned to the normalized file only if its duration is close.
    final_duration = media_duration(normalized_path)
    if abs(final_duration - cursor) > 1.0:
        # Scale segment boundaries proportionally if normalization changed length.
        scale = final_duration / cursor if cursor else 1.0
        pos = 0.0
        for segment in segments:
            segment.start_sec = pos
            segment.duration_sec *= scale
            pos += segment.duration_sec
            segment.end_sec = pos
            segment.audio_path = segment.audio_path
    else:
        # Recompute end times from raw durations; normalized duration is effectively same.
        pos = 0.0
        for segment in segments:
            segment.start_sec = pos
            segment.end_sec = pos + segment.duration_sec
            pos = segment.end_sec
    write_json(output_dir / "audio" / "voice_report.json", {
        "engine": "espeak-ng",
        "voice": config.voice,
        "rate": config.rate,
        "pitch": config.pitch,
        "segment_count": len(segments),
        "total_duration_sec": final_duration,
        "limitations": [
            "eSpeak NG is a compact open-source synthesizer and sounds robotic compared with neural TTS.",
            "Pronunciation of technical terms may be imperfect.",
            "No paid or cloud TTS is used.",
        ],
    })
    return segments, normalized_path
