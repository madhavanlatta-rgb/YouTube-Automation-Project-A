import json
from dataclasses import asdict
from pathlib import Path

from .animation import render_animation
from .assembler import assemble_video, decode_check
from .config import AppConfig
from .models import Claim, NarrationSegment, Scene, Script, Topic
from .quality import run_quality_checks
from .research import research_topic
from .scene_planner import plan_scenes
from .scriptwriter import build_script, validate_script
from .subtitles import write_srt
from .thumbnail import create_thumbnail
from .topic_planner import TopicPlanner
from .tts import build_narration
from .utils import ensure_dir, media_duration, slugify, write_json


def _output_dir(config: AppConfig, topic: Topic) -> Path:
    return ensure_dir(config.output_root / slugify(topic.id))


def _load_script(path: Path) -> Script:
    data = json.loads(path.read_text(encoding="utf-8"))
    scenes = [Scene(**s) for s in data["scenes"]]
    claims = [Claim(**c) for c in data.get("claims", [])]
    return Script(data["topic_id"], data["title"], data["hook"], scenes, data["conclusion"], data["estimated_runtime_sec"], claims)


def _save_script(path: Path, script: Script) -> None:
    write_json(path, {
        "topic_id": script.topic_id,
        "title": script.title,
        "hook": script.hook,
        "scenes": [s.__dict__ for s in script.scenes],
        "conclusion": script.conclusion,
        "estimated_runtime_sec": script.estimated_runtime_sec,
        "claims": [c.__dict__ for c in script.claims],
    })


def _load_segments(path: Path) -> list[NarrationSegment]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [NarrationSegment(s["id"], s["text"], Path(s["audio_path"]), s["duration_sec"], s["start_sec"], s["end_sec"]) for s in data]


def _save_segments(path: Path, segments: list[NarrationSegment]) -> None:
    write_json(path, [s.__dict__ for s in segments])


def run_pipeline(config: AppConfig, topic_id: str | None = None, force: bool = False, max_stage_retries: int = 1) -> dict:
    planner = TopicPlanner(config.completed_topics_path)
    topic = planner.select(topic_id=topic_id)
    if planner.is_duplicate(topic.id) and not force:
        return {"status": "skipped_duplicate", "topic_id": topic.id, "message": "Topic already completed"}

    output_dir = _output_dir(config, topic)
    ensure_dir(output_dir)
    stages: dict[str, str] = {}

    # Research
    research_path = output_dir / "research.json"
    if research_path.exists() and not force:
        research_data = json.loads(research_path.read_text(encoding="utf-8"))
        from .models import ResearchResult, Source, Claim
        research = ResearchResult(
            topic.id,
            [Source(**s) for s in research_data["sources"]],
            [Claim(**c) for c in research_data["claims"]],
            research_data.get("notes", []),
            research_data.get("network_used", False),
        )
        stages["research"] = "cached"
    else:
        research = research_topic(topic, research_path)
        stages["research"] = "completed"

    # Script
    script_path = output_dir / "script.json"
    if script_path.exists() and not force:
        script = _load_script(script_path)
        stages["script"] = "cached"
    else:
        script = build_script(topic, research)
        errors = validate_script(script)
        if errors:
            raise RuntimeError("Script validation failed: " + "; ".join(errors))
        _save_script(script_path, script)
        stages["script"] = "completed"

    # Scene plan
    scene_plan_path = output_dir / "scene_plan.json"
    if scene_plan_path.exists() and not force:
        stages["scene_planning"] = "cached"
    else:
        plan_scenes(script, output_dir)
        stages["scene_planning"] = "completed"

    # TTS
    segments_path = output_dir / "audio" / "segments.json"
    narration_path = output_dir / "audio" / "narration.wav"
    if narration_path.exists() and segments_path.exists() and not force:
        segments = _load_segments(segments_path)
        stages["narration"] = "cached"
    else:
        segments, narration_path = build_narration(script, output_dir, config.tts)
        _save_segments(segments_path, segments)
        stages["narration"] = "completed"

    # Subtitles
    srt_path = output_dir / "subtitles.srt"
    if srt_path.exists() and not force:
        stages["subtitles"] = "cached"
    else:
        write_srt(srt_path, segments)
        stages["subtitles"] = "completed"

    # Animation
    frames_dir = output_dir / "frames"
    first_frame = frames_dir / "frame_000000.png"
    if first_frame.exists() and not force:
        stages["animation"] = "cached"
    else:
        render_animation(script, output_dir, config.render)
        stages["animation"] = "completed"

    # Thumbnail
    thumb_path = output_dir / "thumbnail.png"
    if thumb_path.exists() and not force:
        stages["thumbnail"] = "cached"
    else:
        create_thumbnail(topic.title, thumb_path, config.render)
        stages["thumbnail"] = "completed"

    # Assembly
    video_path = output_dir / "final.mp4"
    if video_path.exists() and not force:
        stages["assembly"] = "cached"
    else:
        assemble_video(frames_dir, narration_path, srt_path, video_path, config.render.fps)
        stages["assembly"] = "completed"

    # Quality with bounded repair
    quality = None
    for attempt in range(max_stage_retries + 1):
        quality = run_quality_checks(output_dir, config.max_duration_sec)
        if quality["status"] == "PASS":
            break
        if attempt < max_stage_retries:
            # Targeted repair: regenerate frames and final video.
            for old_frame in frames_dir.glob("frame_*.png"):
                old_frame.unlink()
            if video_path.exists():
                video_path.unlink()
            render_animation(script, output_dir, config.render)
            assemble_video(frames_dir, narration_path, srt_path, video_path, config.render.fps)
            stages["repair"] = f"attempt_{attempt + 1}"
    stages["quality"] = quality["status"]

    manifest_files = {}
    for path in output_dir.rglob("*"):
        if path.is_file():
            manifest_files[str(path.relative_to(output_dir))] = str(path)
    manifest = {
        "topic_id": topic.id,
        "title": topic.title,
        "output_dir": str(output_dir),
        "files": manifest_files,
        "stages": stages,
        "quality_status": quality["status"] if quality else "unknown",
        "errors": quality["errors"] if quality else [],
    }
    write_json(output_dir / "manifest.json", manifest)

    if quality and quality["status"] == "PASS":
        planner.mark_completed(topic.id)

    return {
        "status": quality["status"] if quality else "unknown",
        "topic_id": topic.id,
        "title": topic.title,
        "output_dir": str(output_dir),
        "quality": quality,
        "stages": stages,
    }
