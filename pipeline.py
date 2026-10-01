from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from clipfarm.analysis.candidates import build_candidates
from clipfarm.analysis.multimodal import analyze_multimodal, enrich_candidates, write_signals
from clipfarm.core.io import write_json
from clipfarm.core.models import RunManifest
from clipfarm.editing.render_plan import build_render_plans
from clipfarm.ingest.source import ingest_source
from clipfarm.transcription.whisper import transcribe


def run_pipeline(
    source: str,
    output_root: Path,
    model: str = "small",
    device: str = "cpu",
    compute_type: str = "int8",
    language: str | None = None,
    min_duration: float = 18.0,
    max_duration: float = 45.0,
    clips: int = 8,
) -> RunManifest:
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    source_meta = ingest_source(source, run_dir)
    transcript_path = run_dir / "transcript.json"
    transcript = transcribe(
        Path(source_meta.local_path),
        transcript_path,
        model_size=model,
        device=device,
        compute_type=compute_type,
        language=language,
    )

    signals = analyze_multimodal(Path(source_meta.local_path), transcript)
    signals_path = write_signals(signals, run_dir / "signals.json")

    candidates = build_candidates(
        transcript,
        min_duration=min_duration,
        max_duration=max_duration,
        max_clips=clips,
    )
    candidates = enrich_candidates(candidates, signals)
    candidates_path = write_json(run_dir / "candidates.json", candidates)
    plans = build_render_plans(candidates)
    render_plan_path = write_json(run_dir / "render_plan.json", plans)

    manifest = RunManifest(
        run_id=run_id,
        run_dir=str(run_dir.resolve()),
        source=source_meta,
        transcript_path=str(transcript_path.resolve()),
        candidates_path=str(candidates_path.resolve()),
        render_plan_path=str(render_plan_path.resolve()),
        signals_path=str(signals_path.resolve()),
    )
    write_json(manifest.path, manifest)
    return manifest
