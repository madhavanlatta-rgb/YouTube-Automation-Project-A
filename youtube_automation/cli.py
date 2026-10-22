import argparse
from pathlib import Path

from .config import AppConfig
from .scheduler import run_scheduled_job, status_report


def load_config(path: str | None) -> AppConfig:
    if path and Path(path).exists():
        return AppConfig.from_file(Path(path))
    default = Path("config/config.json")
    if default.exists():
        return AppConfig.from_file(default)
    return AppConfig()


def main() -> int:
    parser = argparse.ArgumentParser(prog="youtube-automation")
    parser.add_argument("--config", default="config/config.json")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("build-sample")
    p_status = sub.add_parser("status")
    p_status.add_argument("--json", action="store_true")

    p_publish = sub.add_parser("dry-run-publish")
    p_publish.add_argument("--output-dir", required=True)

    p_schedule = sub.add_parser("schedule-check")

    args = parser.parse_args()
    config = load_config(args.config)

    if args.command == "build-sample":
        result = run_scheduled_job(config, topic_id="four-stroke-engine", dry_run_upload=True)
        print(result["status"])
        if result.get("output_dir"):
            print(result["output_dir"])
        return 0 if result.get("status") == "PASS" else 1

    if args.command == "status":
        report = status_report(config)
        if args.json:
            import json
            print(json.dumps(report, indent=2))
        else:
            print(report.get("status"), report.get("message", ""))
        return 0

    if args.command == "dry-run-publish":
        from .publisher import dry_run_publish
        output_dir = Path(args.output_dir)
        result = dry_run_publish({"title": "How a Four-Stroke Engine Works"}, output_dir / "final.mp4", output_dir)
        print(result["status"] if "status" in result else result.get("mode"))
        return 0

    if args.command == "schedule-check":
        print("Scheduler configuration loaded; interval_days=", config.scheduler.get("interval_days"))
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
