from clipfarm.analysis.multimodal import enrich_candidates
from clipfarm.core.models import ClipCandidate, MultimodalSignals, ScoreBreakdown, SignalPoint


def _candidate(score: float = 7.0) -> ClipCandidate:
    return ClipCandidate(
        start=0.0,
        end=20.0,
        hook="test",
        overall=score,
        reasons=[],
        scores=ScoreBreakdown(
            hook=.5, shock=.2, humour=.1, controversy=.1,
            insight=.5, emotion=.2, energy=.6, arc=1.0,
        ),
        transcript="test clip",
    )


def test_enrich_candidates_adds_signal_summary_and_score():
    signals = MultimodalSignals(
        duration=30,
        audio_rms=[SignalPoint(t=1, value=.8), SignalPoint(t=2, value=.7)],
        scene_changes=[SignalPoint(t=4, value=.9), SignalPoint(t=8, value=.8)],
        motion=[SignalPoint(t=1, value=.7), SignalPoint(t=2, value=.6)],
        face_presence=[SignalPoint(t=1, value=.5), SignalPoint(t=2, value=.4)],
    )
    result = enrich_candidates([_candidate()], signals)[0]
    assert result.multimodal_score > 0
    assert result.signal_summary["audio_energy"] > 0
    assert result.overall != 7.0
