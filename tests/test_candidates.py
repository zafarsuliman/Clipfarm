from clipfarm.analysis.candidates import build_candidates
from clipfarm.core.models import Transcript, Word


def _transcript() -> Transcript:
    text = [
        ("Here's", 0.0, 0.4), ("why", 0.4, 0.8), ("this", 0.8, 1.1), ("works.", 1.1, 1.5),
        ("The", 1.7, 1.9), ("reason", 1.9, 2.3), ("is", 2.3, 2.5), ("simple.", 2.5, 3.0),
        ("Most", 3.3, 3.6), ("people", 3.6, 4.0), ("make", 4.0, 4.3), ("the", 4.3, 4.5), ("biggest", 4.5, 5.0), ("mistake.", 5.0, 5.5),
        ("Because", 5.8, 6.2), ("they", 6.2, 6.4), ("skip", 6.4, 6.8), ("the", 6.8, 7.0), ("system.", 7.0, 7.5),
        ("Then", 7.8, 8.1), ("everything", 8.1, 8.8), ("breaks.", 8.8, 9.3),
        ("This", 9.5, 9.8), ("is", 9.8, 10.0), ("the", 10.0, 10.2), ("key.", 10.2, 10.6),
        ("Do", 10.8, 11.0), ("it", 11.0, 11.2), ("in", 11.2, 11.4), ("this", 11.4, 11.7), ("order.", 11.7, 12.2),
        ("First", 12.4, 12.7), ("capture", 12.7, 13.1), ("the", 13.1, 13.3), ("data.", 13.3, 13.8),
        ("Second", 14.0, 14.4), ("measure", 14.4, 14.9), ("the", 14.9, 15.1), ("result.", 15.1, 15.7),
        ("Third", 15.9, 16.2), ("improve", 16.2, 16.7), ("the", 16.7, 16.9), ("next", 16.9, 17.2), ("version.", 17.2, 17.8),
        ("That's", 18.0, 18.4), ("the", 18.4, 18.6), ("whole", 18.6, 18.9), ("framework.", 18.9, 19.5),
    ]
    return Transcript(video="sample.mp4", language="en", duration=20.0, model="tiny", words=[Word(text=t, start=s, end=e) for t, s, e in text])


def test_build_candidates_returns_complete_window():
    items = build_candidates(_transcript(), min_duration=8.0, max_duration=20.0, max_clips=3)
    assert items
    assert all(item.end > item.start for item in items)
    assert items[0].overall >= 0
    assert items[0].transcript.endswith((".", "!", "?", "…"))
