import json
from pathlib import Path

from .models import Script
from .utils import ensure_dir, write_json


def plan_scenes(script: Script, output_dir: Path) -> list[dict]:
    scenes = []
    cursor = 0.0
    for scene in script.scenes:
        item = {
            "id": scene.id,
            "title": scene.title,
            "narration": scene.narration,
            "visual": scene.visual,
            "duration_sec": scene.duration_sec,
            "start_sec": cursor,
            "end_sec": cursor + scene.duration_sec,
            "claims": scene.claims,
        }
        scenes.append(item)
        cursor += scene.duration_sec
    ensure_dir(output_dir)
    write_json(output_dir / "scene_plan.json", {"scenes": scenes, "total_duration_sec": cursor})
    return scenes
