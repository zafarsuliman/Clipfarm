from clipfarm.core.models import ClipCandidate, ScoreBreakdown, Transcript, Word, ViralScore
from clipfarm.editing.editing_intelligence import build_edit_plan, build_variants

def candidate():
    return ClipCandidate(
        start=2.0,
        end=15.0,
        hook="here is why",
        overall=7.2,
        reasons=["hook"],
        transcript="Here is why this matters. Um this is the key point. Finally it works.",
        scores=ScoreBreakdown(
            hook=0.8, shock=0.1, humour=0.0, controversy=0.0,
            insight=0.6, emotion=0.2, energy=0.5, arc=1.0
        ),
        viral=ViralScore(
            attention_acquisition=0.7, attention_maintenance=0.7, reward=0.7,
            transmission=0.5, audience_match=0.65, hook_quality=0.8,
            curiosity_tension=0.6, payoff=0.7, novelty=0.4,
            emotion_change=0.3, narrative_progress=0.7, utility=0.6,
            share_motive=0.4, attention_event_density=0.6, attention_debt=0.2, final=7.0
        ),
    )

def transcript():
    words = [
        Word(text="Here", start=1.5, end=1.8),
        Word(text="is", start=1.8, end=2.0),
        Word(text="why", start=2.0, end=2.2),
        Word(text="this", start=2.2, end=2.4),
        Word(text="matters.", start=2.4, end=2.8),
        Word(text="Um", start=4.0, end=4.2),
        Word(text="this", start=4.8, end=5.0),
        Word(text="is", start=5.0, end=5.1),
        Word(text="the", start=5.1, end=5.2),
        Word(text="key", start=5.2, end=5.4),
        Word(text="point.", start=5.4, end=5.8),
        Word(text="Finally", start=12.0, end=12.4),
        Word(text="it", start=12.4, end=12.6),
        Word(text="works.", start=12.6, end=13.0),
    ]
    return Transcript(video="x.mp4", duration=30, model="test", words=words)

def test_edit_plan_has_tightening_and_emphasis():
    plan = build_edit_plan(candidate(), transcript())
    assert plan["end"] >= 15.0
    assert isinstance(plan["tighten_edits"], list)
    assert any(e["word"].lower().startswith("key") for e in plan["caption_emphasis"])

def test_variants_are_three():
    plan = build_edit_plan(candidate(), transcript())
    variants = build_variants(plan)
    assert [v["variant"] for v in variants] == ["balanced", "tight", "punchy"]
