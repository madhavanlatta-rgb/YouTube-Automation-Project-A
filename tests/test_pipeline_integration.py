from pathlib import Path
from youtube_automation.config import AppConfig
from youtube_automation.pipeline import run_pipeline


def test_end_to_end_sample_build(tmp_path):
    config = AppConfig()
    config.output_root = tmp_path / "outputs"
    config.work_root = tmp_path / "work"
    config.completed_topics_path = tmp_path / "completed.json"
    config.completed_topics_path.write_text('{"completed": []}', encoding="utf-8")
    result = run_pipeline(config, topic_id="four-stroke-engine", max_stage_retries=1)
    assert result["status"] == "PASS", result
    output_dir = Path(result["output_dir"])
    assert (output_dir / "final.mp4").exists()
    assert (output_dir / "thumbnail.png").exists()
    assert (output_dir / "subtitles.srt").exists()
    assert (output_dir / "quality_report.json").exists()
    assert (output_dir / "manifest.json").exists()
