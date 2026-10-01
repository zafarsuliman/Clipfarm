from __future__ import annotations

import json
import math
import os
import subprocess
import urllib.request
from pathlib import Path

from clipfarm.core.models import ClipCandidate, Transcript

TARGETS = {
    "9:16": (1080, 1920, 96, 300),
    "1:1": (1080, 1080, 82, 120),
    "16:9": (1920, 1080, 72, 95),
}
PREVIEW_TARGETS = {
    "9:16": (480, 854),
    "1:1": (480, 480),
    "16:9": (854, 480),
}
CAPTION_STYLES = {
    "default": {"font": "Arial Black", "highlight": "&H00FFFF&", "weight": -1},
    "hormozi": {"font": "Arial Black", "highlight": "&H0000FF&", "weight": -1},
    "mrbeast": {"font": "Arial Black", "highlight": "&H00FF00&", "weight": -1},
    "podcast": {"font": "Arial", "highlight": "&H00FFFF&", "weight": 0},
}
DET_FPS = 4
DET_W = 640
EMA_ALPHA = 0.20
MARGIN_FRAC = 0.18
YUNET_URL = (
    "https://github.com/opencv/opencv_zoo/raw/main/models/"
    "face_detection_yunet/face_detection_yunet_2023mar.onnx"
)


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def ffprobe_dims(path: Path) -> tuple[int, int]:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x", str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    width, height = result.stdout.strip().split("x")[:2]
    return int(width), int(height)


def crop_for(width: int, height: int, target_w: int, target_h: int) -> tuple[int, int, int, int]:
    target_aspect = target_w / float(target_h)
    source_aspect = width / float(height)
    if abs(source_aspect - target_aspect) < 1e-3:
        crop_w, crop_h = width, height
    elif source_aspect > target_aspect:
        crop_h = height
        crop_w = int(round(height * target_aspect))
    else:
        crop_w = width
        crop_h = int(round(width / target_aspect))
    crop_w -= crop_w % 2
    crop_h -= crop_h % 2
    x = max(0, (width - crop_w) // 2)
    y = max(0, (height - crop_h) // 2)
    return crop_w, crop_h, x, y


def _make_detector(cache_dir: Path):
    import cv2

    cache_dir.mkdir(parents=True, exist_ok=True)
    model_path = cache_dir / "face_detection_yunet_2023mar.onnx"
    if not model_path.exists():
        try:
            urllib.request.urlretrieve(YUNET_URL, model_path)
        except Exception:
            model_path = Path()

    if model_path.exists():
        try:
            detector = cv2.FaceDetectorYN.create(
                str(model_path), "", (DET_W, 360), 0.6, 0.3, 5000
            )
            return "yunet", detector
        except Exception:
            pass

    return "haar", cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )


def detect_face_track(
    source: Path,
    start: float,
    duration: float,
    source_width: int,
    temp_dir: Path,
) -> list[tuple[float, float | None]]:
    import cv2

    temp_dir.mkdir(parents=True, exist_ok=True)
    sample = temp_dir / "_detect.mp4"
    _run([
        "ffmpeg", "-y", "-ss", f"{start:.3f}", "-i", str(source),
        "-t", f"{duration:.3f}", "-vf", f"fps={DET_FPS},scale={DET_W}:-2",
        "-an", str(sample),
    ])

    kind, detector = _make_detector(temp_dir / "models")
    cap = cv2.VideoCapture(str(sample))
    frame_w = cap.get(cv2.CAP_PROP_FRAME_WIDTH) or DET_W
    frame_h = cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 360
    x_scale = source_width / float(frame_w)
    if kind == "yunet":
        detector.setInputSize((int(frame_w), int(frame_h)))

    track: list[tuple[float, float | None]] = []
    index = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        t = index / float(DET_FPS)
        cx = None
        if kind == "yunet":
            _, faces = detector.detect(frame)
            if faces is not None and len(faces):
                best = max(faces, key=lambda f: f[2] * f[3] * float(f[14]))
                cx = (float(best[0]) + float(best[2]) / 2.0) * x_scale
        else:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = detector.detectMultiScale(gray, 1.1, 5, minSize=(36, 36))
            if len(faces):
                x, _, w, _ = max(faces, key=lambda f: f[2] * f[3])
                cx = (x + w / 2.0) * x_scale
        track.append((t, cx))
        index += 1

    cap.release()
    try:
        sample.unlink()
    except OSError:
        pass
    return track


def smooth_track(
    track: list[tuple[float, float | None]],
    source_width: int,
    crop_width: int,
) -> list[tuple[float, float]]:
    half = crop_width / 2.0
    max_offset = half - crop_width * MARGIN_FRAC
    known = [x for _, x in track if x is not None]
    base = sorted(known)[len(known) // 2] if known else source_width / 2.0

    filled: list[tuple[float, float]] = []
    last = base
    for t, x in track:
        if x is None:
            x = last
        last = x
        filled.append((t, x))

    if not filled:
        return [(0.0, min(max(base, half), source_width - half))]

    output: list[tuple[float, float]] = []
    center = filled[0][1]
    for t, face in filled:
        center += EMA_ALPHA * (face - center)
        if face - center > max_offset:
            center = face - max_offset
        elif center - face > max_offset:
            center = face + max_offset
        center = min(max(center, half), source_width - half)
        output.append((t, center))
    return output


def build_sendcmd(track: list[tuple[float, float]], crop_width: int, path: Path) -> None:
    lines: list[str] = []
    last_x: int | None = None
    for t, center_x in track:
        x = int(round(center_x - crop_width / 2.0))
        if last_x is None or abs(x - last_x) >= 2:
            lines.append(f"{t:.2f} crop x {x};")
            last_x = x
    if not lines:
        lines = ["0.00 crop x 0;"]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _ass_time(value: float) -> str:
    value = max(0.0, value)
    hours = int(value // 3600)
    minutes = int((value % 3600) // 60)
    seconds = value % 60
    return f"{hours}:{minutes:02d}:{seconds:05.2f}"


def _ass_escape(text: str) -> str:
    return text.replace("\\", "").replace("{", "(").replace("}", ")")


def build_ass(
    transcript: Transcript,
    clip_start: float,
    clip_end: float,
    path: Path,
    target_w: int,
    target_h: int,
    font_size: int,
    margin_v: int,
    style_name: str,
    words_per_line: int = 3,
) -> None:
    style = CAPTION_STYLES.get(style_name, CAPTION_STYLES["default"])
    words = [w for w in transcript.words if w.end > clip_start and w.start < clip_end]
    header = (
        "[Script Info]\nScriptType: v4.00+\n"
        f"PlayResX: {target_w}\nPlayResY: {target_h}\nWrapStyle: 2\nScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
        "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Cap,{style['font']},{font_size},&H00FFFFFF,&H000000FF,&H00000000,"
        f"&H64000000,{style['weight']},0,0,0,100,100,0,0,1,5,2,2,80,80,{margin_v},1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )

    groups = [words[i:i + words_per_line] for i in range(0, len(words), words_per_line)]
    highlight = r"{\c" + style["highlight"] + "}"
    white = r"{\c&HFFFFFF&}"
    events: list[str] = []
    for group in groups:
        for i, word in enumerate(group):
            start = max(word.start, clip_start) - clip_start
            end = (
                group[i + 1].start - clip_start
                if i + 1 < len(group)
                else min(word.end, clip_end) - clip_start
            )
            if end <= start:
                end = start + 0.12
            parts: list[str] = []
            for j, other in enumerate(group):
                token = _ass_escape(other.text.strip())
                parts.append((highlight + token + white) if i == j else (white + token))
            events.append(
                f"Dialogue: 0,{_ass_time(start)},{_ass_time(end)},Cap,,0,0,0,,{' '.join(parts)}"
            )

    path.write_text(header + "\n".join(events) + "\n", encoding="utf-8")


def _sanitize(text: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in "-_ " else "" for ch in text.lower())
    safe = "-".join(safe.split())
    return safe[:70] or "clip"


def render_candidate(
    source: Path,
    transcript: Transcript,
    candidate: ClipCandidate,
    output_dir: Path,
    index: int,
    aspect: str = "9:16",
    caption_style: str = "default",
    preview: bool = False,
    loudnorm: bool = True,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    work_dir = output_dir / ".work"
    work_dir.mkdir(exist_ok=True)

    full_w, full_h, font_size, margin_v = TARGETS[aspect]
    if preview:
        target_w, target_h = PREVIEW_TARGETS[aspect]
        scale = target_h / float(full_h)
        font_size = max(12, round(font_size * scale))
        margin_v = max(10, round(margin_v * scale))
    else:
        target_w, target_h = full_w, full_h

    source_w, source_h = ffprobe_dims(source)
    crop_w, crop_h, x0, y0 = crop_for(source_w, source_h, target_w, target_h)
    start = float(candidate.start)
    end = float(candidate.end)
    duration = max(0.1, end - start)

    ass_path = work_dir / f"clip_{index:02d}.ass"
    build_ass(
        transcript,
        start,
        end,
        ass_path,
        target_w,
        target_h,
        font_size,
        margin_v,
        caption_style,
    )

    needs_tracking = aspect == "9:16" and crop_w < source_w * 0.95
    if needs_tracking:
        raw_track = detect_face_track(source, start, duration, source_w, work_dir)
        track = smooth_track(raw_track, source_w, crop_w)
        cmd_path = work_dir / f"clip_{index:02d}_crop.cmd"
        build_sendcmd(track, crop_w, cmd_path)
        initial_x = max(0, min(int(round(track[0][1] - crop_w / 2.0)), source_w - crop_w))
        video_filter = (
            f"sendcmd=f={cmd_path.as_posix()},crop={crop_w}:{crop_h}:{initial_x}:{y0},"
            f"scale={target_w}:{target_h},subtitles={ass_path.as_posix()}"
        )
        tracking_mode = "face_tracked"
    else:
        video_filter = (
            f"crop={crop_w}:{crop_h}:{x0}:{y0},scale={target_w}:{target_h},"
            f"subtitles={ass_path.as_posix()}"
        )
        tracking_mode = "center_crop"

    slug = _sanitize(candidate.hook)
    output_path = output_dir / f"{index:02d}-{slug}.mp4"
    cmd = [
        "ffmpeg", "-y", "-ss", f"{start:.3f}", "-i", str(source),
        "-t", f"{duration:.3f}", "-vf", video_filter,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k",
    ]
    if loudnorm:
        cmd.extend(["-af", "loudnorm=I=-14:TP=-1.5:LRA=11"])
    cmd.extend(["-movflags", "+faststart", str(output_path)])
    _run(cmd)

    meta = {
        "candidate_index": index,
        "start": candidate.start,
        "end": candidate.end,
        "score": candidate.overall,
        "hook": candidate.hook,
        "reasons": candidate.reasons,
        "aspect": aspect,
        "caption_style": caption_style,
        "tracking_mode": tracking_mode,
        "preview": preview,
        "output": str(output_path.resolve()),
    }
    output_path.with_suffix(".meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return output_path


def render_candidates(
    source: Path,
    transcript: Transcript,
    candidates: list[ClipCandidate],
    output_dir: Path,
    aspect: str = "9:16",
    caption_style: str = "default",
    preview: bool = False,
    loudnorm: bool = True,
    indexes: set[int] | None = None,
) -> list[Path]:
    rendered: list[Path] = []
    for index, candidate in enumerate(candidates, 1):
        if indexes and index not in indexes:
            continue
        rendered.append(
            render_candidate(
                source=source,
                transcript=transcript,
                candidate=candidate,
                output_dir=output_dir,
                index=index,
                aspect=aspect,
                caption_style=caption_style,
                preview=preview,
                loudnorm=loudnorm,
            )
        )
    return rendered
