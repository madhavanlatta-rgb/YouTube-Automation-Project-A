from pathlib import Path
import tempfile
from youtube_automation.topic_planner import TopicPlanner


def test_select_and_duplicate_tracking():
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "completed.json"
        planner = TopicPlanner(path)
        topic = planner.select(topic_id="four-stroke-engine")
        assert topic.id == "four-stroke-engine"
        assert not planner.is_duplicate(topic.id)
        planner.mark_completed(topic.id)
        assert planner.is_duplicate(topic.id)
