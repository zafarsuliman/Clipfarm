from __future__ import annotations

import math
import re
from statistics import mean

from clipfarm.core.models import ClipCandidate, MultimodalSignals, ViralScore
from clipfarm.research.events import AttentionEvent, AttentionEventType

QUESTION_RE = re.compile(r"\b(why|how|what|when|where|who|which|did|does|do|can|could|would|should|is|are|was|were)\b", re.I)
CURIOSITY_CUES = (
    "you won't believe", "nobody knew", "what happened next", "the reason", "here's why",
    "here is why", "the secret", "turns out", "until", "but then", "however",
    "you need to see", "wait for", "the truth", "this changed everything",
)
PAYOFF_CUES = (
    "so that's why", "that's why", "the answer", "it worked", "finally", "in the end",
    "the result", "turns out", "therefore", "that means", "which is why", "so now",
)
UTILITY_CUES = (
    "how to", "step", "tip", "hack", "guide", "method", "framework", "strategy", "lesson",
    "avoid", "save", "make money", "cost", "cheaper", "faster", "better", "fix",
)
SHARE_CUES = (
    "send this", "share this", "tag", "everyone", "people need to know", "warning",
    "remember this", "save this", "tell your", "if you know someone",
)
NOVELTY_CUES = (
    "first ever", "never seen", "new", "strange", "weird", "unexpected", "rare", "nobody",
    "different", "unusual", "wild", "insane",
)
EMOTION_CUES = (
    "love", "hate", "angry", "furious", "scared", "terrified", "excited", "amazing",
    "terrible", "cried", "crying", "proud", "embarrassed", "shocked", "surprised",
)
CONFLICT_CUES = (
    "i disagree", "you're wrong", "you are wrong", "argument", "fight", "versus", "vs",
    "controversial", "hot take", "debate", "called out", "exposed",
)
SUCCESS_CUES = (
    "million", "billion", "won", "winner", "built", "grew", "success", "profitable",
    "record", "champion", "top", "best", "number one", "sold out",
)


def _clip_text(candidate: ClipCandidate) -> str:
    return (candidate.transcript or "").strip()


def _cue_fraction(text: str, cues: tuple[str, ...], divisor: float = 2.0) -> float:
    low = text.lower()
    return min(1.0, sum(c in low for c in cues) / divisor)


def _window_values(points, start: float, end: float) -> list[float]:
    return [p.value for p in points if start <= p.t <= end]


def _spike_events(points, start: float, end: float, event_type: AttentionEventType, threshold: float = 0.72) -> list[AttentionEvent]:
    vals = [p for p in points if start <= p.t <= end]
    if not vals:
        return []
    avg = mean(p.value for p in vals)
    events: list[AttentionEvent] = []
    for p in vals:
        dynamic = max(threshold, avg + 0.18)
        if p.value >= dynamic:
            events.append(AttentionEvent(type=event_type, start=p.t, confidence=min(1.0, p.value), evidence=f"signal={p.value:.3f}"))
    return events


def _scene_events(signals: MultimodalSignals, start: float, end: float) -> list[AttentionEvent]:
    return [
        AttentionEvent(type=AttentionEventType.SCENE_CHANGE, start=p.t, confidence=min(1.0, max(0.5, p.value)), evidence=f"scene_score={p.value:.3f}")
        for p in signals.scene_changes if start <= p.t <= end
    ]


def _face_event(signals: MultimodalSignals, start: float, end: float) -> list[AttentionEvent]:
    opening = [p for p in signals.face_presence if start <= p.t <= min(end, start + 1.25)]
    if opening and max(p.value for p in opening) >= 0.15:
        best = max(opening, key=lambda p: p.value)
        return [AttentionEvent(type=AttentionEventType.FACE_APPEARS, start=best.t, confidence=min(1.0, best.value), evidence=f"opening_face={best.value:.3f}")]
    return []


def derive_attention_events(candidate: ClipCandidate, signals: MultimodalSignals) -> list[AttentionEvent]:
    text = _clip_text(candidate)
    low = text.lower()
    events: list[AttentionEvent] = []
    events.extend(_spike_events(signals.audio_rms, candidate.start, candidate.end, AttentionEventType.AUDIO_SPIKE))
    events.extend(_spike_events(signals.motion, candidate.start, candidate.end, AttentionEventType.MOTION_SPIKE))
    events.extend(_scene_events(signals, candidate.start, candidate.end))
    events.extend(_face_event(signals, candidate.start, candidate.end))

    if "?" in text or QUESTION_RE.search(text[:160]):
        events.append(AttentionEvent(type=AttentionEventType.QUESTION_OPENED, start=candidate.start, confidence=0.8, evidence="question language"))
    if any(c in low for c in CURIOSITY_CUES):
        events.append(AttentionEvent(type=AttentionEventType.INFORMATION_GAP, start=candidate.start, confidence=0.72, evidence="curiosity cue"))
    if any(c in low for c in PAYOFF_CUES):
        events.append(AttentionEvent(type=AttentionEventType.PAYOFF, start=max(candidate.start, candidate.end - min(5.0, (candidate.end-candidate.start)*0.25)), confidence=0.72, evidence="resolution cue"))
    if any(c in low for c in UTILITY_CUES):
        events.append(AttentionEvent(type=AttentionEventType.UTILITY, start=candidate.start, confidence=0.7, evidence="utility cue"))
    if any(c in low for c in CONFLICT_CUES):
        events.append(AttentionEvent(type=AttentionEventType.CONFLICT, start=candidate.start, confidence=0.68, evidence="conflict cue"))
    if any(c in low for c in SUCCESS_CUES):
        events.append(AttentionEvent(type=AttentionEventType.SUCCESS_CUE, start=candidate.start, confidence=0.65, evidence="success cue"))
    if any(c in low for c in EMOTION_CUES):
        events.append(AttentionEvent(type=AttentionEventType.EMOTION_CHANGE, start=candidate.start, confidence=0.62, evidence="emotion cue"))
    return sorted(events, key=lambda e: e.start)


def _attention_stats(events: list[AttentionEvent], start: float, end: float) -> tuple[float, float, float]:
    duration = max(0.1, end - start)
    ts = sorted({max(start, min(end, e.start)) for e in events})
    density = min(1.0, len(ts) / max(1.0, duration / 4.0))
    if len(ts) < 2:
        mean_gap = duration
    else:
        mean_gap = mean(b-a for a, b in zip(ts, ts[1:]))
    gap_score = math.exp(-max(0.0, mean_gap - 3.0) / 5.0)
    opening = min((t-start for t in ts), default=duration)
    opening_score = math.exp(-opening / 2.5)
    return density, gap_score, opening_score


def _attention_debt(events: list[AttentionEvent], candidate: ClipCandidate) -> float:
    duration = max(0.1, candidate.end - candidate.start)
    opened = [e for e in events if e.type in {AttentionEventType.QUESTION_OPENED, AttentionEventType.INFORMATION_GAP}]
    if not opened:
        return 0.25
    rewards = sorted(e.start for e in events if e.type in {AttentionEventType.INFORMATION_REVEAL, AttentionEventType.PAYOFF, AttentionEventType.SURPRISE})
    first_open = min(e.start for e in opened)
    if not rewards:
        return 1.0
    first_reward = min(rewards)
    wait = max(0.0, first_reward - first_open)
    debt = min(1.0, wait / max(6.0, duration * 0.55))
    if rewards[-1] >= candidate.end - min(4.0, duration * 0.2):
        debt *= 0.8
    return round(debt, 4)


def score_candidate(candidate: ClipCandidate, signals: MultimodalSignals) -> tuple[ViralScore, list[AttentionEvent]]:
    text = _clip_text(candidate)
    duration = max(0.1, candidate.end - candidate.start)
    events = derive_attention_events(candidate, signals)
    density, gap_score, opening_event_score = _attention_stats(events, candidate.start, candidate.end)

    opening_audio = _window_values(signals.audio_rms, candidate.start, min(candidate.end, candidate.start+1.5))
    opening_motion = _window_values(signals.motion, candidate.start, min(candidate.end, candidate.start+1.5))
    opening_faces = _window_values(signals.face_presence, candidate.start, min(candidate.end, candidate.start+1.5))
    first_second = (
        0.38*(max(opening_audio) if opening_audio else 0.0)
        + 0.34*(max(opening_motion) if opening_motion else 0.0)
        + 0.18*(max(opening_faces) if opening_faces else 0.0)
        + 0.10*opening_event_score
    )

    hook_quality = min(1.0, 0.62*candidate.scores.hook + 0.38*first_second)
    curiosity = min(1.0, 0.45*_cue_fraction(text, CURIOSITY_CUES, 1.5) + 0.35*(1.0 if any(e.type == AttentionEventType.INFORMATION_GAP for e in events) else 0.0) + 0.20*(1.0 if any(e.type == AttentionEventType.QUESTION_OPENED for e in events) else 0.0))
    payoff = min(1.0, 0.58*(1.0 if any(e.type == AttentionEventType.PAYOFF for e in events) else candidate.scores.arc) + 0.42*candidate.scores.arc)
    novelty = min(1.0, 0.45*_cue_fraction(text, NOVELTY_CUES, 1.5) + 0.30*candidate.signal_summary.get("scene_density", 0.0) + 0.25*candidate.signal_summary.get("motion_energy", 0.0))
    emotion_change = min(1.0, 0.58*candidate.scores.emotion + 0.22*_cue_fraction(text, EMOTION_CUES, 1.5) + 0.20*candidate.signal_summary.get("audio_energy", 0.0))
    narrative_progress = min(1.0, 0.55*candidate.scores.arc + 0.25*payoff + 0.20*curiosity)
    utility = min(1.0, 0.65*_cue_fraction(text, UTILITY_CUES, 1.5) + 0.35*candidate.scores.insight)
    share_motive = min(1.0, 0.40*_cue_fraction(text, SHARE_CUES, 1.2) + 0.18*utility + 0.14*emotion_change + 0.14*candidate.scores.humour + 0.14*candidate.scores.controversy)
    attention_density = min(1.0, 0.58*density + 0.42*gap_score)
    debt = _attention_debt(events, candidate)

    acquisition = min(1.0, 0.50*hook_quality + 0.22*novelty + 0.16*first_second + 0.12*(candidate.signal_summary.get("face_presence", 0.0)))
    maintenance = min(1.0, 0.34*attention_density + 0.24*narrative_progress + 0.17*emotion_change + 0.14*novelty + 0.11*(1.0-debt))
    reward = min(1.0, 0.44*payoff + 0.27*utility + 0.17*candidate.scores.insight + 0.12*candidate.scores.humour)
    transmission = min(1.0, 0.50*share_motive + 0.18*emotion_change + 0.14*utility + 0.10*candidate.scores.controversy + 0.08*candidate.scores.humour)
    match = 0.65  # neutral prior until audience/platform context is available

    # Geometric blend prevents a single very high dimension from masking a weak clip.
    eps = 1e-4
    total = ((acquisition+eps)*(maintenance+eps)*(reward+eps)*(transmission+eps)*(match+eps)) ** (1/5)
    # Preserve a modest connection to the legacy heuristic to reduce ranking shocks in v0.4.
    total = min(1.0, 0.84*total + 0.16*(candidate.overall/10.0))

    score = ViralScore(
        attention_acquisition=round(acquisition,4),
        attention_maintenance=round(maintenance,4),
        reward=round(reward,4),
        transmission=round(transmission,4),
        audience_match=round(match,4),
        hook_quality=round(hook_quality,4),
        curiosity_tension=round(curiosity,4),
        payoff=round(payoff,4),
        novelty=round(novelty,4),
        emotion_change=round(emotion_change,4),
        narrative_progress=round(narrative_progress,4),
        utility=round(utility,4),
        share_motive=round(share_motive,4),
        attention_event_density=round(attention_density,4),
        attention_debt=round(debt,4),
        final=round(total*10.0,2),
    )
    return score, events


def rank_candidates(candidates: list[ClipCandidate], signals: MultimodalSignals) -> list[ClipCandidate]:
    ranked: list[ClipCandidate] = []
    for candidate in candidates:
        viral, events = score_candidate(candidate, signals)
        candidate.viral = viral
        candidate.attention_events = events
        candidate.overall = viral.final
        reasons = [
            ("hook", viral.hook_quality), ("curiosity", viral.curiosity_tension),
            ("payoff", viral.payoff), ("attention-density", viral.attention_event_density),
            ("utility", viral.utility), ("share-motive", viral.share_motive),
            ("novelty", viral.novelty), ("emotion-change", viral.emotion_change),
        ]
        candidate.reasons = [name for name, value in sorted(reasons, key=lambda x: x[1], reverse=True) if value >= 0.45][:5]
        ranked.append(candidate)
    return sorted(ranked, key=lambda c: c.overall, reverse=True)
