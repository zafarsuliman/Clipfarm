from clipfarm.core.models import ClipCandidate, MultimodalSignals, ScoreBreakdown, SignalPoint
from clipfarm.intelligence import rank_candidates, score_candidate


def _candidate(text: str) -> ClipCandidate:
    return ClipCandidate(
        start=0.0,
        end=24.0,
        hook="here's why this works",
        overall=7.0,
        reasons=[],
        scores=ScoreBreakdown(
            hook=0.8, shock=0.2, humour=0.1, controversy=0.1,
            insight=0.7, emotion=0.3, energy=0.7, arc=1.0,
        ),
        transcript=text,
        multimodal_score=0.5,
        signal_summary={"audio_energy":0.55,"motion_energy":0.4,"scene_density":0.5,"face_presence":0.3},
    )


def _signals() -> MultimodalSignals:
    return MultimodalSignals(
        duration=30,
        audio_rms=[SignalPoint(t=0.2,value=0.9), SignalPoint(t=4,value=0.45), SignalPoint(t=10,value=0.85)],
        scene_changes=[SignalPoint(t=3,value=0.7), SignalPoint(t=12,value=0.8)],
        motion=[SignalPoint(t=0.4,value=0.8), SignalPoint(t=8,value=0.7)],
        face_presence=[SignalPoint(t=0.1,value=0.35), SignalPoint(t=5,value=0.2)],
    )


def test_viral_score_is_bounded():
    score, events = score_candidate(_candidate("Why does this work? Here's the secret. Step one saves money. Finally, that's why it works."), _signals())
    assert 0 <= score.final <= 10
    assert 0 <= score.attention_debt <= 1
    assert events


def test_curiosity_and_payoff_are_detected():
    score, _ = score_candidate(_candidate("Why does this happen? Nobody knew the reason. Finally, the answer is simple."), _signals())
    assert score.curiosity_tension > 0.3
    assert score.payoff > 0.5


def test_rank_candidates_sets_viral_model():
    ranked = rank_candidates([
        _candidate("A plain statement with a complete explanation."),
        _candidate("Why does this happen? Here's the secret. Finally, that's why it works."),
    ], _signals())
    assert all(c.viral is not None for c in ranked)
    assert ranked[0].overall >= ranked[1].overall
