import json
from dataclasses import asdict
from pathlib import Path

from .models import Topic


DEFAULT_TOPICS = [
    {
        "id": "four-stroke-engine",
        "title": "How a Four-Stroke Engine Works",
        "central_question": "How do intake, compression, power, and exhaust strokes turn fuel into motion?",
        "outline": [
            "What a four-stroke engine is",
            "Main components and their roles",
            "Intake stroke",
            "Compression stroke",
            "Power stroke",
            "Exhaust stroke",
            "Valve timing and crankshaft motion",
            "Efficiency, heat, lubrication, and failure modes",
            "Real-world applications",
        ],
        "title_candidates": [
            "How a Four-Stroke Engine Works",
            "Inside a Four-Stroke Engine: From Air and Fuel to Motion",
            "The Four Strokes That Power Most Cars",
        ],
        "audience": "General technical learners and students",
        "keywords": ["internal combustion", "piston", "crankshaft", "valves", "thermodynamics"],
    }
]


class TopicPlanner:
    def __init__(self, completed_path: Path, topics: list[dict] | None = None):
        self.completed_path = completed_path
        self.topics = topics if topics is not None else [dict(t) for t in DEFAULT_TOPICS]

    def _completed_ids(self) -> set[str]:
        if not self.completed_path.exists():
            return set()
        try:
            data = json.loads(self.completed_path.read_text(encoding="utf-8"))
            return set(data.get("completed", []))
        except json.JSONDecodeError:
            return set()

    def mark_completed(self, topic_id: str) -> None:
        completed = self._completed_ids()
        completed.add(topic_id)
        self.completed_path.parent.mkdir(parents=True, exist_ok=True)
        self.completed_path.write_text(json.dumps({"completed": sorted(completed)}, indent=2), encoding="utf-8")

    def list_topics(self) -> list[Topic]:
        completed = self._completed_ids()
        result = []
        for item in self.topics:
            topic = Topic(**item)
            topic.title = topic.title
            result.append(topic)
        return result

    def select(self, topic_id: str | None = None, title: str | None = None) -> Topic:
        completed = self._completed_ids()
        candidates = self.topics
        if topic_id:
            for item in candidates:
                if item["id"] == topic_id:
                    return Topic(**item)
            raise ValueError(f"Unknown topic id: {topic_id}")
        if title:
            for item in candidates:
                if item["title"].lower() == title.lower():
                    return Topic(**item)
            raise ValueError(f"Unknown topic title: {title}")
        for item in candidates:
            if item["id"] not in completed:
                return Topic(**item)
        raise RuntimeError("All configured topics are already completed")

    def is_duplicate(self, topic_id: str) -> bool:
        return topic_id in self._completed_ids()
