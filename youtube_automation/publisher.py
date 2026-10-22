import json
import os
from pathlib import Path

from .utils import ensure_dir, write_json


def upload_status_path(output_dir: Path) -> Path:
    return output_dir / "upload_status.json"


def dry_run_publish(metadata: dict, video_path: Path, output_dir: Path) -> dict:
    status = {
        "mode": "dry_run",
        "uploaded": False,
        "video_path": str(video_path),
        "title": metadata.get("title"),
        "would_upload": video_path.exists(),
        "message": "Dry run only. No network upload was attempted.",
    }
    write_json(upload_status_path(output_dir), status)
    return status


def publish_video(metadata: dict, video_path: Path, output_dir: Path, dry_run: bool = True, client_secrets_env: str = "YOUTUBE_CLIENT_SECRETS") -> dict:
    if dry_run:
        return dry_run_publish(metadata, video_path, output_dir)

    secrets_path = os.environ.get(client_secrets_env)
    if not secrets_path or not Path(secrets_path).exists():
        status = {
            "mode": "live",
            "uploaded": False,
            "status": "awaiting_credentials",
            "message": f"Missing YouTube client secrets. Set {client_secrets_env} to an OAuth client secrets JSON path.",
        }
        write_json(upload_status_path(output_dir), status)
        return status

    try:
        import googleapiclient.discovery  # noqa: F401
    except Exception as exc:  # noqa: BLE001
        status = {
            "mode": "live",
            "uploaded": False,
            "status": "dependency_missing",
            "message": f"google-api-python-client is not installed: {exc}",
        }
        write_json(upload_status_path(output_dir), status)
        return status

    status = {
        "mode": "live",
        "uploaded": False,
        "status": "not_implemented",
        "message": "Live upload requires configured OAuth tokens; this build intentionally stops before uploading without explicit approval.",
    }
    write_json(upload_status_path(output_dir), status)
    return status
