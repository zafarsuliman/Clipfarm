from clipfarm.core.models import ClipCandidate, ScoreBreakdown
from clipfarm.dedupe import dedupe_candidates

def c(start, end, text, score):
    return ClipCandidate(
        start=start,
        end=end,
        hook="x",
        overall=score,
        transcript=text,
        scores=ScoreBreakdown(
            hook=0.5, shock=0.0, humour=0.0, controversy=0.0,
            insight=0.5, emotion=0.0, energy=0.5, arc=1.0
        ),
    )

def test_dedupe_keeps_best_duplicate():
    items = [
        c(0, 20, "this is almost the same clip", 8.0),
        c(2, 21, "this is almost the same clip", 7.0),
        c(40, 60, "totally different topic", 6.5),
    ]
    out = dedupe_candidates(items)
    assert len(out) == 2
    assert out[0].overall == 8.0
