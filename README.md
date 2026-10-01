# Clipfarm v0.1

Clipfarm is a local-first, research-instrumented short-form clipping pipeline.

## Immediate goal

Turn an authorized source video into 5-10 reviewable short-form clip candidates with transparent scoring and reproducible metadata.

Pipeline:

`URL/local file -> ingest -> transcription -> candidate generation -> scoring -> boundary repair -> render plan -> human review`

## Quick start

Requirements:
- Python 3.11+
- FFmpeg + ffprobe on PATH
- yt-dlp

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -e .
clipfarm run "<authorized-video-url>" --clips 8 --model small
```

For a Ryzen 7 5700U / integrated GPU laptop, start with `--model small --device cpu --compute-type int8`.

## What v0.1 does

- downloads an authorized source with yt-dlp or accepts a local file
- probes video metadata with ffprobe
- transcribes locally with faster-whisper using word timestamps
- builds transparent transcript-based clip candidates
- records a score breakdown per candidate
- writes a render manifest for later 9:16 rendering
- stores all outputs in a run directory for future research/analytics

## What v0.1 intentionally does not do yet

- automatic posting
- dashboard UI
- paid API calls
- large video-language models on every clip
- aggressive multi-platform automation

## License and upstream code

Clipfarm itself is MIT licensed. Some implementation ideas and permissively licensed code patterns are adapted from upstream projects; see `THIRD_PARTY_NOTICES.md`.
