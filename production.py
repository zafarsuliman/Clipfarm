from __future__ import annotations

from pathlib import Path

from clipfarm.core.io import read_json, write_json
from clipfarm.core.models import ClipCandidate, RenderPlan, RunManifest, Transcript
from clipfarm.dedupe import dedupe_candidates
from clipfarm.editing.renderer_v2 import render_plan
from clipfarm.qa import technical_qa


def _parse_manifest(path: Path) -> RunManifest:
    return RunManifest.model_validate(read_json(path))


def execute_run(
    manifest_path: Path,
    top_n: int = 8,
    variants: tuple[str, ...] = ("balanced", "tight", "punchy"),
    output_dir: Path | None = None,
    preview: bool = False,
) -> dict:
    manifest = _parse_manifest(manifest_path)
    transcript = Transcript.model_validate(read_json(Path(manifest.transcript_path)))
    candidates = [ClipCandidate.model_validate(x) for x in read_json(Path(manifest.candidates_path))]
    plans = [RenderPlan.model_validate(x) for x in read_json(Path(manifest.render_plan_path))]

    candidates = dedupe_candidates(candidates)[:top_n]
    candidate_map = {i + 1: c for i, c in enumerate(candidates)}
    source = Path(manifest.source.local_path)
    out_dir = output_dir or (Path(manifest.run_dir) / "finished")
    reject_dir = Path(manifest.run_dir) / "rejected"
    out_dir.mkdir(parents=True, exist_ok=True)
    reject_dir.mkdir(parents=True, exist_ok=True)

    rendered, rejected = [], []

    selected_plans = [
        p for p in plans
        if p.candidate_index in candidate_map and p.variant in set(variants)
    ]

    for plan in selected_plans:
        candidate = candidate_map[plan.candidate_index]
        try:
            output = render_plan(
                source=source,
                transcript=transcript,
                candidate=candidate,
                plan=plan,
                output_dir=out_dir,
                index=plan.candidate_index,
                preview=preview,
                loudnorm=True,
            )
            qa = technical_qa(output, "9:16")
            item = {
                "candidate_index": plan.candidate_index,
                "variant": plan.variant,
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
                "candidate_index": plan.candidate_index,
                "variant": plan.variant,
                "score": candidate.overall,
                "error": f"{type(exc).__name__}: {exc}",
            })

    report = {
        "manifest": str(manifest_path),
        "rendered": rendered,
        "rejected": rejected,
        "summary": {
            "candidates": len(candidates),
            "variants_requested": list(variants),
            "rendered": len(rendered),
            "rejected": len(rejected),
        },
    }
    write_json(out_dir / "production_report.json", report)
    return report
