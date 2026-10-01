# Clipfarm v0.1 architecture

## Design rule

Keep the first version as a modular monorepo and prove one complete pipeline before adding publishing, dashboards, or distributed workers.

## Processing path

1. Ingest authorized source with yt-dlp or local copy.
2. Probe source with ffprobe.
3. Transcribe with faster-whisper using VAD and word timestamps.
4. Sentenceize on punctuation and pauses.
5. Generate candidate windows around high-scoring sentences.
6. Preserve complete-thought endings where possible.
7. Emit transparent score breakdowns and research reasons.
8. Build a 9:16 render plan.
9. Human reviews candidates before any publishing.

## Next implementation milestone

Port the permissively licensed rendering concepts from Chopify into `editing/renderer.py`:
- dynamic 9:16 crop
- YuNet/OpenCV face tracking fallback
- ASS word highlighting
- FFmpeg rendering
- preview mode

Then add cheap audio/scene signals before any Qwen/InternVideo integration.
