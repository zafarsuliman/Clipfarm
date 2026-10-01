from __future__ import annotations

from pathlib import Path

from clipfarm.core.io import write_json
from clipfarm.core.models import Segment, Transcript, Word


def transcribe(
    video_path: Path,
    out_path: Path,
    model_size: str = "small",
    device: str = "cpu",
    compute_type: str = "int8",
    language: str | None = None,
) -> Transcript:
    from faster_whisper import WhisperModel

    model = WhisperModel(model_size, device=device, compute_type=compute_type)
    segments_iter, info = model.transcribe(
        str(video_path),
        word_timestamps=True,
        vad_filter=True,
        language=language,
    )

    segments: list[Segment] = []
    words: list[Word] = []
    for seg in segments_iter:
        segments.append(Segment(start=float(seg.start), end=float(seg.end), text=seg.text.strip()))
        for word in seg.words or []:
            if word.start is None or word.end is None:
                continue
            words.append(Word(text=word.word.strip(), start=float(word.start), end=float(word.end)))

    transcript = Transcript(
        video=str(video_path),
        language=getattr(info, "language", None),
        duration=float(getattr(info, "duration", 0.0) or 0.0),
        model=model_size,
        segments=segments,
        words=words,
    )
    write_json(out_path, transcript)
    return transcript
