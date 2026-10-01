from __future__ import annotations

from pydantic import BaseModel


class Hypothesis(BaseModel):
    id: str
    mechanism: str
    feature: str
    prior: str
    status: str = "untested"


HYPOTHESES = [
    Hypothesis(id="H01", mechanism="Information gap", feature="unresolved question / curiosity tension", prior="high candidate"),
    Hypothesis(id="H02", mechanism="Surprise / prediction error", feature="unexpected event", prior="high candidate"),
    Hypothesis(id="H03", mechanism="Faces", feature="face in opening frame", prior="medium-high"),
    Hypothesis(id="H04", mechanism="Emotional change", feature="expression/emotion transition", prior="medium"),
    Hypothesis(id="H05", mechanism="Social conflict", feature="disagreement/confrontation", prior="test"),
    Hypothesis(id="H06", mechanism="Prestige", feature="high-status/domain-authority cue", prior="contextual"),
    Hypothesis(id="H07", mechanism="Success cues", feature="demonstrated achievement", prior="test"),
    Hypothesis(id="H08", mechanism="Conformity", feature="social proof / everyone-is cue", prior="test"),
    Hypothesis(id="H09", mechanism="Novelty", feature="unusual/new stimulus", prior="attention-high; completion-unknown"),
    Hypothesis(id="H10", mechanism="Utility", feature="useful information", prior="high candidate"),
    Hypothesis(id="H11", mechanism="Humour", feature="incongruity/laughter", prior="context dependent"),
    Hypothesis(id="H12", mechanism="Narrative progress", feature="unresolved to resolution", prior="high"),
    Hypothesis(id="H13", mechanism="Arousal", feature="emotional intensity", prior="mixed"),
    Hypothesis(id="H14", mechanism="Identity", feature="people-like-me relevance", prior="test"),
    Hypothesis(id="H15", mechanism="Relationship relevance", feature="send-this-to relevance", prior="test"),
    Hypothesis(id="H16", mechanism="Social reaction", feature="other people reacting", prior="test"),
    Hypothesis(id="H17", mechanism="Competence demonstration", feature="skill/performance", prior="test"),
    Hypothesis(id="H18", mechanism="Loss/threat", feature="potential negative outcome", prior="test"),
    Hypothesis(id="H19", mechanism="Reward anticipation", feature="promised payoff", prior="high candidate"),
    Hypothesis(id="H20", mechanism="Visual novelty", feature="unexpected visual", prior="high candidate"),
]
