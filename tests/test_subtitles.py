from pathlib import Path
import tempfile
from youtube_automation.models import NarrationSegment
from youtube_automation.subtitles import write_srt, parse_srt, validate_srt


def test_srt_roundtrip():
    with tempfile.TemporaryDirectory() as d:
        segs = [NarrationSegment("s1", "Hello world.", Path("/tmp/a.wav"), 1.2, 0.0, 1.2)]
        path = Path(d) / "t.srt"
        write_srt(path, segs)
        entries = parse_srt(path)
        assert len(entries) == 1
        assert entries[0]["text"] == "Hello world."
        assert validate_srt(path, 10) == []
