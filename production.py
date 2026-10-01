from __future__ import annotations

import json
from pathlib import Path

from clipfarm.core.io import read_json, write_json
from clipfarm.core.models import ClipCandidate, RunManifest, Transcript
from clipfarm.dedupe import dedupe_candidates
from clipfarm.editing.renderer import render_candidate
from clipfarm.qa import technical_qa


def _parse_manifest(path: Path) -> RunManifest:
    return RunManifest.model_validate(read_json(path))


def _parse_transcript(path: str) -> Transcript:
    return Transcript.model_validate(read_json(Path(path)))


def _parse_candidates(path: str) -> list[ClipCandidate]:
    return [ClipCandidate.model_validate(x) for x in read_json(Path(path))]


def execute_run(
    manifest_path: Path,
    top_n: int = 8,
    output_dir: Path | None = None,
    preview: bool = False,
) -> dict:
    manifest = _parse_manifest(manifest_path)
    transcript = _parse_transcript(manifest.transcript_path)
    candidates = _parse_candidates(manifest.candidates_path)
    candidates = dedupe_candidates(candidates)[:top_n]

    source = Path(manifest.source.local_path)
    out_dir = output_dir or (Path(manifest.run_dir) / "finished")
    out_dir.mkdir(parents=True, exist_ok=True)

    rendered = []
    rejected = []

    for idx, candidate in enumerate(candidates, 1):
        try:
            output = render_candidate(
                source=source,
                transcript=transcript,
                candidate=candidate,
                output_dir=out_dir,
                index=idx,
                aspect="9:16",
                caption_style="default",
                preview=preview,
                loudnorm=True,
            )
            qa = technical_qa(output, "9:16")
            item = {
                "candidate_index": idx,
                "score": candidate.overall,
                "path": str(output),
                "qa": qa,
            }
            if qa["passed"]:
                rendered.append(item)
            else:
                rejected.append(item)
        except Exception as exc:  # noqa: BLE001
            rejected.append({
                "candidate_index": idx,
                "score": candidate.overall,
                "error": f"{type(exc).__name__}: {exc}",
            })

    report = {
        "manifest": str(manifest_path),
        "rendered": rendered,
        "rejected": rejected,
        "summary": {
            "requested": top_n,
            "rendered": len(rendered),
            "rejected": len(rejected),
        },
    }
    write_json(out_dir / "production_report.json", report)
    return report
