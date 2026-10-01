from __future__ import annotations

from clipfarm.core.models import ClipCandidate, RenderPlan


def build_render_plans(candidates: list[ClipCandidate]) -> list[RenderPlan]:
    return [
        RenderPlan(
            candidate_index=i,
            start=candidate.start,
            end=candidate.end,
        )
        for i, candidate in enumerate(candidates, start=1)
    ]
