# Clipfarm v0.9 — End-to-End Integration

Pass 7 closes the largest remaining integration gap: v0.5 edit plans are now consumed by
the production renderer.

## Added

- renderer v2
- actual silence/filler cut execution
- transcript time remapping after cuts
- balanced/tight/punchy variant rendering
- attention-event zoom execution
- edit-profile metadata in finished files
- production runner now consumes `render_plan.json`
- unified `clipfarm produce` command
- unified `clipfarm batch` command
- environment doctor helper
- integration tests for time-remapping/cut logic

## Working end-to-end flow

```text
source
 -> ingest
 -> faster-whisper
 -> multimodal signals
 -> candidate generation
 -> viral/retention ranking
 -> editing intelligence
 -> render variants
 -> technical QA
 -> production report
```

## Recommended first real test

```bash
pip install -e ".[analysis,render]"
clipfarm run "<authorized-video-url>" --clips 8
clipfarm produce runs/<run-id>/manifest.json --top 5 --variants balanced,tight --preview
```

Then repeat without `--preview` after visually reviewing the preview outputs.

## Remaining work before v1.0

No major architecture pass should be added before testing this on real videos. The next step is
validation/tuning: run different source types, inspect failures and awkward edits, then change
thresholds/weights based on observed results.
