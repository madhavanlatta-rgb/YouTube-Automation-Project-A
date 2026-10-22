from youtube_automation.topic_planner import TopicPlanner
from youtube_automation.research import research_topic
from youtube_automation.scriptwriter import build_script, validate_script
from pathlib import Path
import tempfile


def test_sample_script_validates():
    with tempfile.TemporaryDirectory() as d:
        planner = TopicPlanner(Path(d) / "completed.json")
        topic = planner.select(topic_id="four-stroke-engine")
        research = research_topic(topic)
        script = build_script(topic, research)
        assert validate_script(script) == []
        assert script.estimated_runtime_sec <= 1200
        assert len(script.scenes) >= 5
