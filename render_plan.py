from __future__ import annotations

from clipfarm.core.models import ClipCandidate, RenderPlan, Transcript
from clipfarm.editing.editing_intelligence import build_edit_plans, build_variants


def build_render_plans(
    candidates: list[ClipCandidate],
    transcript: Transcript | None = None,
) -> list[RenderPlan]:
    edit_plans = build_edit_plans(candidates, transcript) if transcript is not None else [None] * len(candidates)
    plans: list[RenderPlan] = []
    for i, (candidate, edit_plan) in enumerate(zip(candidates, edit_plans), start=1):
        if edit_plan is None:
            plans.append(
                RenderPlan(
                    candidate_index=i,
                    start=candidate.start,
                    end=candidate.end,
                )
            )
            continue

        for variant in build_variants(edit_plan):
            plans.append(
                RenderPlan(
                    candidate_index=i,
                    start=variant["start"],
                    end=variant["end"],
                    caption_style=variant.get("caption_style", "default"),
                    tracking_mode="face_fallback",
                    edit_profile=variant["profile"],
                    variant=variant["variant"],
                    edit_plan=variant,
                )
            )
    return plans
