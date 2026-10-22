import json
import time
from pathlib import Path

from .config import AppConfig
from .pipeline import run_pipeline
from .publisher import publish_video
from .utils import ensure_dir, write_json


def status_path(config: AppConfig) -> Path:
    return ensure_dir(config.work_root) / "job_status.json"


def lock_path(config: AppConfig) -> Path:
    return ensure_dir(config.work_root) / "job.lock"


def acquire_lock(config: AppConfig) -> bool:
    path = lock_path(config)
    if path.exists():
        try:
            age = time.time() - path.stat().st_mtime
            if age < config.scheduler.get("job_timeout_sec", 7200):
                return False
        except OSError:
            return False
    path.write_text(str(time.time()), encoding="utf-8")
    return True


def release_lock(config: AppConfig) -> None:
    path = lock_path(config)
    if path.exists():
        path.unlink()


def record_status(config: AppConfig, payload: dict) -> None:
    payload["timestamp"] = time.time()
    write_json(status_path(config), payload)


def run_scheduled_job(config: AppConfig, topic_id: str | None = None, dry_run_upload: bool = True) -> dict:
    if not acquire_lock(config):
        result = {"status": "skipped_locked", "message": "Another job appears to be running"}
        record_status(config, result)
        return result
    try:
        result = run_pipeline(config, topic_id=topic_id, max_stage_retries=config.scheduler.get("max_retries", 2))
        if result.get("status") == "PASS":
            output_dir = Path(result["output_dir"])
            publish_video(
                {"title": result["title"]},
                output_dir / "final.mp4",
                output_dir,
                dry_run=dry_run_upload,
                client_secrets_env=config.youtube.get("client_secrets_env", "YOUTUBE_CLIENT_SECRETS"),
            )
        record_status(config, result)
        return result
    except Exception as exc:  # noqa: BLE001
        result = {"status": "ERROR", "error": f"{type(exc).__name__}: {exc}"}
        record_status(config, result)
        return result
    finally:
        release_lock(config)


def status_report(config: AppConfig) -> dict:
    path = status_path(config)
    if not path.exists():
        return {"status": "no_runs", "message": "No job status recorded yet"}
    return json.loads(path.read_text(encoding="utf-8"))
