from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Source:
    title: str
    url: str
    source_type: str
    notes: str = ""


@dataclass
class Claim:
    id: str
    text: str
    status: str = "supported"
    source_urls: list[str] = field(default_factory=list)
    uncertainty: str = ""


@dataclass
class Topic:
    id: str
    title: str
    central_question: str
    outline: list[str]
    title_candidates: list[str]
    audience: str
    keywords: list[str] = field(default_factory=list)


@dataclass
class Scene:
    id: str
    title: str
    narration: str
    visual: str
    duration_sec: float = 0.0
    claims: list[str] = field(default_factory=list)


@dataclass
class Script:
    topic_id: str
    title: str
    hook: str
    scenes: list[Scene]
    conclusion: str
    estimated_runtime_sec: float
    claims: list[Claim] = field(default_factory=list)


@dataclass
class ResearchResult:
    topic_id: str
    sources: list[Source]
    claims: list[Claim]
    notes: list[str] = field(default_factory=list)
    network_used: bool = False


@dataclass
class NarrationSegment:
    id: str
    text: str
    audio_path: Path
    duration_sec: float
    start_sec: float = 0.0
    end_sec: float = 0.0


@dataclass
class ProductionManifest:
    topic_id: str
    title: str
    output_dir: Path
    files: dict[str, str] = field(default_factory=dict)
    stages: dict[str, str] = field(default_factory=dict)
    tests: list[dict[str, Any]] = field(default_factory=list)
    quality_report: str = ""
    errors: list[str] = field(default_factory=list)
