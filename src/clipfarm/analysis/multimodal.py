from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path
from statistics import mean
from typing import Iterable

from clipfarm.core.models import ClipCandidate, MultimodalSignals, SignalPoint, Transcript


def _run_capture(cmd: list[str]) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return result.stdout


def _probe_duration(path: Path) -> float:
    out = _run_capture([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path),
    ]).strip()
    return float(out)


def extract_audio_rms(source: Path, sample_seconds: float = 0.5) -> list[SignalPoint]:
    """Return normalized RMS energy samples using FFmpeg astats metadata.

    This is intentionally CPU-friendly: audio is downmixed and sampled without loading the
    full video into Python. Values are normalized to 0..1 using a conservative -60..0 dB map.
    """
    cmd = [
        "ffmpeg", "-hide_banner", "-nostats", "-i", str(source),
        "-vn", "-af",
        f"asetnsamples=n={max(256, int(48000 * sample_seconds))}:p=1,astats=metadata=1:reset=1,ametadata=print:key=lavfi.astats.Overall.RMS_level:file=-",
        "-f", "null", "-",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    text = proc.stdout + "\n" + proc.stderr
    points: list[SignalPoint] = []
    t = 0.0
    for line in text.splitlines():
        if "lavfi.astats.Overall.RMS_level=" not in line:
            continue
        raw = line.rsplit("=", 1)[-1].strip()
        try:
            db = float(raw)
        except ValueError:
            continue
        if math.isinf(db):
            value = 0.0
        else:
            value = min(1.0, max(0.0, (db + 60.0) / 60.0))
        points.append(SignalPoint(t=round(t, 3), value=round(value, 4)))
        t += sample_seconds
    return points


def detect_scene_changes(source: Path, threshold: float = 0.32) -> list[SignalPoint]:
    """Detect scene cuts using FFmpeg's scene score, returning cut timestamps and scores."""
    filt = f"select='gt(scene,{threshold})',metadata=print:file=-"
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(source), "-vf", filt, "-an", "-f", "null", "-"],
        capture_output=True,
        text=True,
    )
    text = proc.stdout + "\n" + proc.stderr
    pts_time: float | None = None
    out: list[SignalPoint] = []
    for line in text.splitlines():
        line = line.strip()
        if "pts_time:" in line:
            try:
                pts_time = float(line.split("pts_time:", 1)[1].split()[0])
            except ValueError:
                pts_time = None
        elif "lavfi.scene_score=" in line and pts_time is not None:
            try:
                score = float(line.rsplit("=", 1)[-1])
            except ValueError:
                continue
            out.append(SignalPoint(t=round(pts_time, 3), value=round(score, 4)))
            pts_time = None
    return out


def extract_motion(source: Path, fps: float = 2.0, width: int = 320) -> list[SignalPoint]:
    """Estimate visual motion from consecutive low-res grayscale frames using OpenCV.

    This is deliberately lightweight enough for CPU-only laptops. The value is mean absolute
    frame difference normalized to 0..1.
    """
    try:
        import cv2
    except ImportError as exc:  # pragma: no cover - optional dependency path
        raise RuntimeError("OpenCV is required for visual signal analysis; install clipfarm[render]") from exc

    sample = source.parent / "_clipfarm_motion_sample.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(source),
            "-vf", f"fps={fps},scale={width}:-2", "-an", str(sample),
        ],
        check=True,
    )
    cap = cv2.VideoCapture(str(sample))
    previous = None
    points: list[SignalPoint] = []
    index = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        value = 0.0
        if previous is not None:
            diff = cv2.absdiff(gray, previous)
            value = float(diff.mean() / 255.0)
        points.append(SignalPoint(t=round(index / fps, 3), value=round(min(1.0, value * 4.0), 4)))
        previous = gray
        index += 1
    cap.release()
    try:
        sample.unlink()
    except OSError:
        pass
    return points


def extract_face_presence(source: Path, fps: float = 1.0, width: int = 320) -> list[SignalPoint]:
    """Estimate face presence per sampled frame using OpenCV Haar cascade.

    We store the fraction of frame area occupied by the largest detected face, capped to 1.
    """
    try:
        import cv2
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("OpenCV is required for face analysis; install clipfarm[render]") from exc

    sample = source.parent / "_clipfarm_face_sample.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(source),
            "-vf", f"fps={fps},scale={width}:-2", "-an", str(sample),
        ],
        check=True,
    )
    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    cap = cv2.VideoCapture(str(sample))
    points: list[SignalPoint] = []
    index = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = cascade.detectMultiScale(gray, 1.1, 5, minSize=(24, 24))
        h, w = gray.shape[:2]
        frac = 0.0
        if len(faces):
            _, _, fw, fh = max(faces, key=lambda f: f[2] * f[3])
            frac = min(1.0, (fw * fh) / float(max(1, w * h)) * 8.0)
        points.append(SignalPoint(t=round(index / fps, 3), value=round(frac, 4)))
        index += 1
    cap.release()
    try:
        sample.unlink()
    except OSError:
        pass
    return points


def _window_values(points: Iterable[SignalPoint], start: float, end: float) -> list[float]:
    return [p.value for p in points if start <= p.t <= end]


def _scene_density(points: Iterable[SignalPoint], start: float, end: float) -> float:
    duration = max(1.0, end - start)
    count = sum(1 for p in points if start <= p.t <= end)
    return min(1.0, count / max(1.0, duration / 4.0))


def enrich_candidates(candidates: list[ClipCandidate], signals: MultimodalSignals) -> list[ClipCandidate]:
    """Fuse cheap multimodal features into candidate scores without replacing text scoring.

    The weights are intentionally modest. v0.3 records and uses the features; v0.4 will
    replace these provisional weights with research-driven virality/retention logic.
    """
    enriched: list[ClipCandidate] = []
    for candidate in candidates:
        audio = _window_values(signals.audio_rms, candidate.start, candidate.end)
        motion = _window_values(signals.motion, candidate.start, candidate.end)
        faces = _window_values(signals.face_presence, candidate.start, candidate.end)
        scene_density = _scene_density(signals.scene_changes, candidate.start, candidate.end)

        audio_energy = mean(audio) if audio else 0.0
        motion_energy = mean(motion) if motion else 0.0
        face_score = mean(faces) if faces else 0.0
        multimodal = min(
            1.0,
            0.34 * audio_energy + 0.30 * motion_energy + 0.20 * scene_density + 0.16 * face_score,
        )
        # Keep transcript scoring dominant in v0.3 while letting strong visual/audio evidence
        # reorder close candidates.
        fused = min(10.0, candidate.overall * 0.82 + multimodal * 10.0 * 0.18)
        candidate.multimodal_score = round(multimodal, 4)
        candidate.signal_summary = {
            "audio_energy": round(audio_energy, 4),
            "motion_energy": round(motion_energy, 4),
            "scene_density": round(scene_density, 4),
            "face_presence": round(face_score, 4),
        }
        candidate.overall = round(fused, 2)
        if multimodal >= 0.5 and "multimodal" not in candidate.reasons:
            candidate.reasons.append("multimodal")
        enriched.append(candidate)
    return sorted(enriched, key=lambda c: c.overall, reverse=True)


def analyze_multimodal(source: Path, transcript: Transcript | None = None) -> MultimodalSignals:
    duration = transcript.duration if transcript is not None else _probe_duration(source)
    return MultimodalSignals(
        duration=duration,
        audio_rms=extract_audio_rms(source),
        scene_changes=detect_scene_changes(source),
        motion=extract_motion(source),
        face_presence=extract_face_presence(source),
    )


def write_signals(signals: MultimodalSignals, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(signals.model_dump(mode="json"), indent=2), encoding="utf-8")
    return path
