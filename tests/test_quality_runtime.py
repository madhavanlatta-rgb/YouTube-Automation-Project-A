from youtube_automation.quality import run_quality_checks
from pathlib import Path
import tempfile


def test_quality_fails_missing_video():
    with tempfile.TemporaryDirectory() as d:
        out = Path(d)
        report = run_quality_checks(out, 1200)
        assert report["status"] == "FAIL"
        assert any("video" in e.lower() or "missing" in e.lower() for e in report["errors"])
