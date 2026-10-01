from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class Word(BaseModel):
    text: str
    start: float
    end: float


class Segment(BaseModel):
    start: float
    end: float
    text: str


class Transcript(BaseModel):
    video: str
    language: str | None = None
    duration: float
    model: str
    segments: list[Segment] = Field(default_factory=list)
    words: list[Word] = Field(default_factory=list)


class ScoreBreakdown(BaseModel):
    hook: float
    shock: float
    humour: float
    controversy: float
    insight: float
    emotion: float
    energy: float
    arc: float


class ClipCandidate(BaseModel):
    start: float
    end: float
    hook: str
    overall: float
    reasons: list[str] = Field(default_factory=list)
    scores: ScoreBreakdown
    transcript: str


class SourceMetadata(BaseModel):
    source: str
    local_path: str
    width: int | None = None
    height: int | None = None
    duration: float | None = None
    fps: float | None = None


class RenderPlan(BaseModel):
    candidate_index: int
    start: float
    end: float
    aspect_ratio: Literal["9:16"] = "9:16"
    target_width: int = 1080
    target_height: int = 1920
    caption_style: str = "default"
    tracking_mode: str = "face_fallback"


class RunManifest(BaseModel):
    run_id: str
    run_dir: str
    source: SourceMetadata
    transcript_path: str
    candidates_path: str
    render_plan_path: str

    @property
    def path(self) -> Path:
        return Path(self.run_dir) / "manifest.json"
