# YouTube Automation V3

Independent, modular pipeline for producing educational technical videos. The first sample is "How a Four-Stroke Engine Works".

## What is implemented

- Topic planning with duplicate tracking
- Online research with recorded sources
- Script generation and validation
- espeak-ng narration and SRT subtitles
- Lightweight 2D sepia technical animation
- Thumbnail generation
- FFmpeg MP4 assembly
- Quality checks and reports
- Dry-run YouTube publishing interface
- Scheduler/status scaffolding
- Tests and sample outputs

## Requirements

- Python 3.11+
- ffmpeg and ffprobe
- espeak-ng
- Pillow and NumPy (installed via system or pip)

## Local run

```bash
python -m youtube_automation.cli build-sample
```

Outputs are written to `outputs/four-stroke-engine/`.

## Cloud execution

A GitHub Actions workflow is included as a starting point. It is not a continuously running service; GitHub Actions jobs are time-limited and ephemeral. Persist outputs as artifacts or external storage.

## Limitations

- Narration uses eSpeak NG, which sounds robotic compared with neural TTS.
- Research relies on network access and Wikipedia-style sources.
- Live YouTube upload requires OAuth credentials and explicit approval.
- Cloud execution must respect runner time and storage limits.
