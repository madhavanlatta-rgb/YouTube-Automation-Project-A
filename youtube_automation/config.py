import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class TTSConfig:
    engine: str = "espeak-ng"
    voice: str = "en-us"
    rate: int = 150
    pitch: int = 40
    gap_sec: float = 0.12


@dataclass
class RenderConfig:
    width: int = 1280
    height: int = 720
    fps: int = 12
    max_duration_sec: float = 1200.0
    style: str = "sepia_technical"


@dataclass
class AppConfig:
    project_name: str = "youtube-automation"
    output_root: Path = Path("outputs")
    work_root: Path = Path("work")
    max_duration_sec: float = 1200.0
    tts: TTSConfig = field(default_factory=TTSConfig)
    render: RenderConfig = field(default_factory=RenderConfig)
    completed_topics_path: Path = Path("config/completed_topics.json")
    youtube: dict = field(default_factory=lambda: {
        "enabled": False,
        "dry_run": True,
        "client_secrets_env": "YOUTUBE_CLIENT_SECRETS",
        "token_path": "config/youtube_token.json",
    })
    scheduler: dict = field(default_factory=lambda: {
        "interval_days": 2,
        "max_retries": 2,
        "job_timeout_sec": 7200,
    })

    @classmethod
    def from_file(cls, path: Path) -> "AppConfig":
        raw = json.loads(path.read_text(encoding="utf-8"))
        cfg = cls()
        for key, value in raw.items():
            if key == "output_root":
                cfg.output_root = Path(value)
            elif key == "work_root":
                cfg.work_root = Path(value)
            elif key == "completed_topics_path":
                cfg.completed_topics_path = Path(value)
            elif key == "tts" and isinstance(value, dict):
                cfg.tts = TTSConfig(**value)
            elif key == "render" and isinstance(value, dict):
                cfg.render = RenderConfig(**value)
            else:
                setattr(cfg, key, value)
        return cfg

    def to_dict(self) -> dict:
        return {
            "project_name": self.project_name,
            "output_root": str(self.output_root),
            "work_root": str(self.work_root),
            "max_duration_sec": self.max_duration_sec,
            "tts": self.tts.__dict__,
            "render": self.render.__dict__,
            "completed_topics_path": str(self.completed_topics_path),
            "youtube": self.youtube,
            "scheduler": self.scheduler,
        }
