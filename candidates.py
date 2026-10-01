from __future__ import annotations

import re
from dataclasses import dataclass

from clipfarm.core.models import ClipCandidate, ScoreBreakdown, Transcript, Word

TERMINAL_RE = re.compile(r"[.!?…][\"')\]]?$")
FILLERS = {"um", "uh", "uhh", "umm", "erm", "er", "hmm", "mmm", "mm", "ah", "eh"}

CUES = {
    "hook": ("the secret", "nobody tells you", "here's why", "imagine", "the problem is", "the biggest mistake", "here's how", "the trick", "the key", "listen"),
    "shock": ("insane", "crazy", "shocking", "unbelievable", "never", "nobody", "banned", "illegal", "destroyed", "worst", "best", "million", "billion", "dead", "killed"),
    "humour": ("haha", "lol", "laugh", "joke", "funny", "hilarious", "kidding", "ridiculous"),
    "controversy": ("i disagree", "unpopular opinion", "hot take", "controversial", "stop doing", "overrated", "underrated", "myth", "lie", "scam"),
    "insight": ("because", "the reason", "how it works", "step one", "first", "second", "third", "the difference", "framework", "system", "lesson", "learned", "the point"),
    "emotion": ("love", "hate", "afraid", "scared", "amazing", "terrible", "proud", "embarrassed", "angry", "excited", "grateful", "hurts", "cried", "dream", "hope"),
}

WEIGHTS = {
    "hook": 0.20,
    "shock": 0.10,
    "humour": 0.05,
    "controversy": 0.10,
    "insight": 0.15,
    "emotion": 0.10,
    "energy": 0.15,
    "arc": 0.15,
}


@dataclass
class Sentence:
    start: float
    end: float
    text: str
    words: list[Word]


def _complete(text: str) -> bool:
    return bool(TERMINAL_RE.search((text or "").strip()))


def _sentenceize(words: list[Word], gap: float = 1.2) -> list[Sentence]:
    out: list[Sentence] = []
    cur: list[Word] = []
    for word in words:
        if cur and (word.start - cur[-1].end) > gap:
            out.append(_sentence(cur))
            cur = []
        cur.append(word)
        if _complete(word.text):
            out.append(_sentence(cur))
            cur = []
    if cur:
        out.append(_sentence(cur))
    return out


def _sentence(words: list[Word]) -> Sentence:
    text = " ".join(w.text for w in words).strip()
    return Sentence(words[0].start, words[-1].end, text, words[:])


def _cue_score(low: str, cues: tuple[str, ...]) -> float:
    return min(1.0, sum(c in low for c in cues) / 2.0)


def _score(start: float, end: float, text: str, words: list[Word]) -> ScoreBreakdown:
    low = f" {text.lower()} "
    duration = max(0.1, end - start)
    wps = len(words) / duration
    return ScoreBreakdown(
        hook=_cue_score(low, CUES["hook"]),
        shock=_cue_score(low, CUES["shock"]),
        humour=_cue_score(low, CUES["humour"]),
        controversy=_cue_score(low, CUES["controversy"]),
        insight=_cue_score(low, CUES["insight"]),
        emotion=_cue_score(low, CUES["emotion"]),
        energy=min(1.0, wps / 3.0),
        arc=1.0 if _complete(text) else 0.55,
    )


def _overall(scores: ScoreBreakdown) -> float:
    raw = scores.model_dump()
    return round(sum(WEIGHTS[k] * float(raw[k]) for k in WEIGHTS) * 10.0, 2)


def _hook(text: str, max_words: int = 7) -> str:
    tokens = [re.sub(r"[^\w']", "", t.lower()) for t in text.split()]
    tokens = [t for t in tokens if t and t not in FILLERS]
    return " ".join(tokens[:max_words]) or "clip"


def _reasons(scores: ScoreBreakdown) -> list[str]:
    ranked = sorted(scores.model_dump().items(), key=lambda item: item[1], reverse=True)
    return [name for name, value in ranked if value >= 0.5][:4]


def build_candidates(
    transcript: Transcript,
    min_duration: float = 18.0,
    max_duration: float = 45.0,
    max_clips: int = 8,
) -> list[ClipCandidate]:
    sentences = _sentenceize(transcript.words)
    if not sentences:
        return []

    seed_scores = []
    for idx, sentence in enumerate(sentences):
        scores = _score(sentence.start, sentence.end, sentence.text, sentence.words)
        seed_scores.append((idx, _overall(scores)))
    order = [idx for idx, _ in sorted(seed_scores, key=lambda item: item[1], reverse=True)]

    taken = [False] * len(sentences)
    candidates: list[ClipCandidate] = []
    for seed in order:
        if taken[seed] or len(candidates) >= max_clips:
            continue
        end_idx = seed
        while end_idx + 1 < len(sentences) and (sentences[end_idx].end - sentences[seed].start) < min_duration and not taken[end_idx + 1]:
            end_idx += 1
        while end_idx > seed and (sentences[end_idx].end - sentences[seed].start) > max_duration:
            end_idx -= 1
        while end_idx + 1 < len(sentences) and not _complete(sentences[end_idx].text) and not taken[end_idx + 1] and (sentences[end_idx + 1].end - sentences[seed].start) <= max_duration:
            end_idx += 1
        while end_idx > seed and not _complete(sentences[end_idx].text):
            end_idx -= 1

        duration = sentences[end_idx].end - sentences[seed].start
        if duration < min_duration * 0.6:
            continue

        window = sentences[seed : end_idx + 1]
        words = [w for sentence in window for w in sentence.words]
        text = " ".join(w.text for w in words).strip()
        scores = _score(window[0].start, window[-1].end, text, words)
        candidate = ClipCandidate(
            start=round(window[0].start, 2),
            end=round(window[-1].end, 2),
            hook=_hook(window[0].text),
            overall=_overall(scores),
            reasons=_reasons(scores),
            scores=scores,
            transcript=text,
        )
        candidates.append(candidate)
        for idx in range(seed, end_idx + 1):
            taken[idx] = True

    return sorted(candidates, key=lambda c: c.overall, reverse=True)
