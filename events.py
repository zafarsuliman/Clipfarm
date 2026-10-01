from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel


class AttentionEventType(StrEnum):
    FACE_APPEARS = "FACE_APPEARS"
    MOTION_SPIKE = "MOTION_SPIKE"
    SCENE_CHANGE = "SCENE_CHANGE"
    AUDIO_SPIKE = "AUDIO_SPIKE"
    VISUAL_NOVELTY = "VISUAL_NOVELTY"
    QUESTION_OPENED = "QUESTION_OPENED"
    INFORMATION_GAP = "INFORMATION_GAP"
    INFORMATION_REVEAL = "INFORMATION_REVEAL"
    SURPRISE = "SURPRISE"
    PAYOFF = "PAYOFF"
    PRESTIGE_CUE = "PRESTIGE_CUE"
    SUCCESS_CUE = "SUCCESS_CUE"
    CONFLICT = "CONFLICT"
    SOCIAL_REACTION = "SOCIAL_REACTION"
    RELATIONSHIP = "RELATIONSHIP"
    CONFORMITY_CUE = "CONFORMITY_CUE"
    HUMOUR = "HUMOUR"
    FEAR = "FEAR"
    ANGER = "ANGER"
    JOY = "JOY"
    EMOTION_CHANGE = "EMOTION_CHANGE"
    UTILITY = "UTILITY"
    MONEY = "MONEY"
    SAFETY = "SAFETY"
    SKILL = "SKILL"
    DECISION_VALUE = "DECISION_VALUE"


class AttentionEvent(BaseModel):
    type: AttentionEventType
    start: float
    end: float | None = None
    confidence: float = 1.0
    evidence: str | None = None
