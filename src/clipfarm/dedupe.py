from __future__ import annotations

import re
from difflib import SequenceMatcher

from clipfarm.core.models import ClipCandidate


def _norm(text: str) -> str:
    text = re.sub(r"\s+", " ", (text or "").lower()).strip()
    text = re.sub(r"[^\w\s]", "", text)
    return text


def transcript_similarity(a: ClipCandidate, b: ClipCandidate) -> float:
    return SequenceMatcher(None, _norm(a.transcript), _norm(b.transcript)).ratio()


def time_overlap(a: ClipCandidate, b: ClipCandidate) -> float:
    start = max(a.start, b.start)
    end = min(a.end, b.end)
    overlap = max(0.0, end - start)
    shorter = max(0.1, min(a.end - a.start, b.end - b.start))
    return overlap / shorter


def dedupe_candidates(
    candidates: list[ClipCandidate],
    transcript_threshold: float = 0.82,
    overlap_threshold: float = 0.70,
) -> list[ClipCandidate]:
    kept: list[ClipCandidate] = []
    for candidate in sorted(candidates, key=lambda c: c.overall, reverse=True):
        duplicate = False
        for chosen in kept:
            if (
                transcript_similarity(candidate, chosen) >= transcript_threshold
                or time_overlap(candidate, chosen) >= overlap_threshold
            ):
                duplicate = True
                break
        if not duplicate:
            kept.append(candidate)
    return kept
