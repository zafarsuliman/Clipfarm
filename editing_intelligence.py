from __future__ import annotations

import re
from dataclasses import dataclass
from statistics import mean

from clipfarm.core.models import ClipCandidate, Transcript, Word

FILLER_WORDS = {"um", "uh", "uhh", "umm", "erm", "er", "hmm", "mmm", "mm", "ah", "eh"}
PUNCT_RE = re.compile(r"[.!?…][\"')\]]?$")
EMPHASIS_CUES = {
    "money", "million", "billion", "never", "always", "secret", "mistake", "best", "worst",
    "why", "how", "truth", "scam", "crazy", "insane", "warning", "important", "finally",
}

@dataclass
class EditProfile:
    name: str
    pacing: str
    tighten: bool
    zoom_strength: float
    caption_emphasis: bool
    max_silence: float

PROFILES = {
    "story": EditProfile("story", "balanced", True, 1.06, True, 0.55),
    "utility": EditProfile("utility", "tight", True, 1.05, True, 0.35),
    "reaction": EditProfile("reaction", "dynamic", False, 1.08, True, 0.65),
    "debate": EditProfile("debate", "balanced", True, 1.04, True, 0.45),
    "default": EditProfile("default", "balanced", True, 1.05, True, 0.50),
}

def _candidate_profile(candidate: ClipCandidate) -> EditProfile:
    viral = candidate.viral
    if viral:
        if viral.utility >= 0.58:
            return PROFILES["utility"]
        if viral.emotion_change >= 0.58 and candidate.signal_summary.get("motion_energy", 0.0) >= 0.22:
            return PROFILES["reaction"]
        if candidate.scores.controversy >= 0.55:
            return PROFILES["debate"]
        if viral.narrative_progress >= 0.55:
            return PROFILES["story"]
    return PROFILES["default"]

def _clip_words(transcript: Transcript, start: float, end: float) -> list[Word]:
    return [w for w in transcript.words if w.end > start and w.start < end]

def _is_complete(word: Word) -> bool:
    return bool(PUNCT_RE.search((word.text or "").strip()))

def _nearest_sentence_start(words: list[Word], start: float, lookback: float = 3.0) -> float:
    previous = [w for w in words if start - lookback <= w.start <= start]
    if not previous:
        return start
    boundary = previous[0].start
    for i, word in enumerate(previous):
        if i > 0 and _is_complete(previous[i - 1]):
            boundary = word.start
    return min(start, boundary)

def _nearest_sentence_end(words: list[Word], end: float, lookahead: float = 3.0) -> float:
    following = [w for w in words if end <= w.end <= end + lookahead]
    for word in following:
        if _is_complete(word):
            return max(end, word.end)
    return end

def repair_boundaries(candidate: ClipCandidate, transcript: Transcript, max_duration: float = 60.0) -> tuple[float, float]:
    words = transcript.words
    start = _nearest_sentence_start(words, candidate.start)
    end = _nearest_sentence_end(words, candidate.end)
    if end - start > max_duration:
        end = start + max_duration
    return round(max(0.0, start), 3), round(max(start + 0.25, end), 3)

def _pause_ranges(words: list[Word], start: float, end: float, min_pause: float) -> list[tuple[float, float]]:
    clip = [w for w in words if w.end > start and w.start < end]
    out = []
    for left, right in zip(clip, clip[1:]):
        gap = right.start - left.end
        if gap >= min_pause:
            out.append((left.end, right.start))
    return out

def _filler_ranges(words: list[Word], start: float, end: float) -> list[tuple[float, float]]:
    out = []
    for w in words:
        if w.end <= start or w.start >= end:
            continue
        token = re.sub(r"[^\w']", "", w.text.lower())
        if token in FILLER_WORDS:
            out.append((w.start, w.end))
    return out

def plan_tightening(
    transcript: Transcript,
    start: float,
    end: float,
    profile: EditProfile,
) -> list[dict]:
    if not profile.tighten:
        return []
    edits: list[dict] = []
    for a, b in _pause_ranges(transcript.words, start, end, profile.max_silence):
        trim = min((b - a) - 0.18, 0.8)
        if trim > 0.08:
            edits.append({"type": "trim_silence", "start": round(a + 0.09, 3), "end": round(a + 0.09 + trim, 3)})
    for a, b in _filler_ranges(transcript.words, start, end):
        if b - a <= 0.9:
            edits.append({"type": "remove_filler", "start": round(max(start, a - 0.03), 3), "end": round(min(end, b + 0.03), 3)})
    return edits

def caption_emphasis(candidate: ClipCandidate, transcript: Transcript, start: float, end: float) -> list[dict]:
    words = _clip_words(transcript, start, end)
    out: list[dict] = []
    for w in words:
        token = re.sub(r"[^\w']", "", w.text.lower())
        if token in EMPHASIS_CUES:
            out.append({"start": round(w.start, 3), "end": round(w.end, 3), "word": w.text.strip(), "strength": 1.0})
    return out[:18]

def zoom_events(candidate: ClipCandidate) -> list[dict]:
    profile = _candidate_profile(candidate)
    events = []
    for e in candidate.attention_events:
        local_t = e.start - candidate.start
        if local_t < 0:
            continue
        if e.type.value in {"MOTION_SPIKE", "AUDIO_SPIKE", "SURPRISE", "PAYOFF", "EMOTION_CHANGE"}:
            events.append({
                "time": round(local_t, 3),
                "scale": profile.zoom_strength,
                "duration": 0.42 if e.type.value != "PAYOFF" else 0.6,
                "reason": e.type.value.lower(),
            })
    deduped = []
    last = -99.0
    for item in sorted(events, key=lambda x: x["time"]):
        if item["time"] - last >= 1.0:
            deduped.append(item)
            last = item["time"]
    return deduped[:10]

def build_edit_plan(candidate: ClipCandidate, transcript: Transcript) -> dict:
    profile = _candidate_profile(candidate)
    start, end = repair_boundaries(candidate, transcript)
    return {
        "profile": profile.name,
        "start": start,
        "end": end,
        "pacing": profile.pacing,
        "tighten": profile.tighten,
        "tighten_edits": plan_tightening(transcript, start, end, profile),
        "zoom_events": zoom_events(candidate),
        "caption_emphasis": caption_emphasis(candidate, transcript, start, end),
        "caption_style": "emphasis" if profile.caption_emphasis else "default",
    }

def build_edit_plans(candidates: list[ClipCandidate], transcript: Transcript) -> list[dict]:
    return [build_edit_plan(c, transcript) for c in candidates]

def build_variants(edit_plan: dict) -> list[dict]:
    base = dict(edit_plan)
    tight = dict(edit_plan)
    punchy = dict(edit_plan)

    base["variant"] = "balanced"
    tight["variant"] = "tight"
    tight["tighten"] = True
    punchy["variant"] = "punchy"
    punchy["pacing"] = "dynamic"
    punchy["zoom_events"] = [
        {**z, "scale": round(min(1.12, float(z["scale"]) + 0.02), 3)}
        for z in edit_plan.get("zoom_events", [])
    ]

    return [base, tight, punchy]
