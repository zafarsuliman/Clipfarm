from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path

from clipfarm.core.models import ClipCandidate, RenderPlan, Transcript
from clipfarm.editing.renderer import (
    TARGETS,
    PREVIEW_TARGETS,
    build_ass,
    crop_for,
    detect_face_track,
    ffprobe_dims,
    smooth_track,
    build_sendcmd,
)


def _merge_intervals(intervals: list[tuple[float, float]], start: float, end: float) -> list[tuple[float, float]]:
    cleaned = []
    for a, b in sorted(intervals):
        a, b = max(start, float(a)), min(end, float(b))
        if b <= a:
            continue
        if cleaned and a <= cleaned[-1][1] + 0.04:
            cleaned[-1] = (cleaned[-1][0], max(cleaned[-1][1], b))
        else:
            cleaned.append((a, b))
    return cleaned


def _keep_ranges(start: float, end: float, edits: list[dict]) -> list[tuple[float, float]]:
    cuts = _merge_intervals(
        [(e["start"], e["end"]) for e in edits if e.get("type") in {"trim_silence", "remove_filler"}],
        start,
        end,
    )
    if not cuts:
        return [(start, end)]

    keeps = []
    cursor = start
    for a, b in cuts:
        if a > cursor:
            keeps.append((cursor, a))
        cursor = max(cursor, b)
    if cursor < end:
        keeps.append((cursor, end))
    return [(a, b) for a, b in keeps if b - a >= 0.12]


def _render_tightened_source(source: Path, keeps: list[tuple[float, float]], out: Path) -> None:
    if len(keeps) == 1:
        a, b = keeps[0]
        subprocess.run(
            ["ffmpeg", "-y", "-ss", f"{a:.3f}", "-i", str(source), "-t", f"{b-a:.3f}",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
             "-c:a", "aac", "-b:a", "192k", str(out)],
            check=True,
        )
        return

    filters = []
    concat_inputs = []
    for i, (a, b) in enumerate(keeps):
        dur = b - a
        filters += [
            f"[0:v]trim=start={a}:duration={dur},setpts=PTS-STARTPTS[v{i}]",
            f"[0:a]atrim=start={a}:duration={dur},asetpts=PTS-STARTPTS[a{i}]",
        ]
        concat_inputs += [f"[v{i}][a{i}]"]
    filters.append("".join(concat_inputs) + f"concat=n={len(keeps)}:v=1:a=1[v][a]")

    subprocess.run(
        ["ffmpeg", "-y", "-i", str(source), "-filter_complex", ";".join(filters),
         "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "veryfast",
         "-crf", "20", "-c:a", "aac", "-b:a", "192k", str(out)],
        check=True,
    )


def _remap_time(t: float, keeps: list[tuple[float, float]]) -> float | None:
    out = 0.0
    for a, b in keeps:
        if a <= t <= b:
            return out + (t - a)
        out += b - a
    return None


def _remap_transcript(transcript: Transcript, keeps: list[tuple[float, float]]) -> Transcript:
    words = []
    for w in transcript.words:
        ns = _remap_time(w.start, keeps)
        ne = _remap_time(w.end, keeps)
        if ns is None or ne is None:
            continue
        words.append(type(w)(text=w.text, start=round(ns, 3), end=round(ne, 3)))
    duration = sum(b - a for a, b in keeps)
    return Transcript(
        video=transcript.video,
        language=transcript.language,
        duration=duration,
        model=transcript.model,
        segments=[],
        words=words,
    )


def _zoom_expression(events: list[dict], base: float = 1.0) -> str:
    if not events:
        return "1"
    parts = [f"between(t,{e['time']:.3f},{e['time']+e['duration']:.3f})*{float(e['scale']):.3f}" for e in events]
    return f"max({base}," + ",".join(parts) + ")"


def render_plan(
    source: Path,
    transcript: Transcript,
    candidate: ClipCandidate,
    plan: RenderPlan,
    output_dir: Path,
    index: int,
    preview: bool = False,
    loudnorm: bool = True,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    work = output_dir / ".work"
    work.mkdir(exist_ok=True)

    edit = plan.edit_plan or {}
    start = float(edit.get("start", plan.start))
    end = float(edit.get("end", plan.end))
    keeps = _keep_ranges(start, end, edit.get("tighten_edits", [])) if edit.get("tighten") else [(start, end)]

    render_src = source
    render_transcript = transcript
    render_start = start
    render_end = end

    if keeps != [(start, end)]:
        render_src = work / f"candidate_{index:02d}_{plan.variant}_tight.mp4"
        _render_tightened_source(source, keeps, render_src)
        render_transcript = _remap_transcript(transcript, keeps)
        render_start = 0.0
        render_end = render_transcript.duration

    full_w, full_h, font_size, margin_v = TARGETS["9:16"]
    if preview:
        target_w, target_h = PREVIEW_TARGETS["9:16"]
        scale = target_h / full_h
        font_size = max(12, round(font_size * scale))
        margin_v = max(10, round(margin_v * scale))
    else:
        target_w, target_h = full_w, full_h

    source_w, source_h = ffprobe_dims(render_src)
    crop_w, crop_h, x0, y0 = crop_for(source_w, source_h, target_w, target_h)
    duration = max(0.1, render_end - render_start)

    ass = work / f"candidate_{index:02d}_{plan.variant}.ass"
    build_ass(
        render_transcript,
        render_start,
        render_end,
        ass,
        target_w,
        target_h,
        font_size,
        margin_v,
        "default",
    )

    if crop_w < source_w * 0.95:
        raw_track = detect_face_track(render_src, render_start, duration, source_w, work)
        track = smooth_track(raw_track, source_w, crop_w)
        cmd_path = work / f"candidate_{index:02d}_{plan.variant}_crop.cmd"
        build_sendcmd(track, crop_w, cmd_path)
        initial_x = max(0, min(int(round(track[0][1] - crop_w / 2.0)), source_w - crop_w))
        base_filter = (
            f"sendcmd=f={cmd_path.as_posix()},crop={crop_w}:{crop_h}:{initial_x}:{y0},"
            f"scale={target_w}:{target_h}"
        )
    else:
        base_filter = f"crop={crop_w}:{crop_h}:{x0}:{y0},scale={target_w}:{target_h}"

    zooms = edit.get("zoom_events", [])
    zoom_expr = _zoom_expression(zooms)
    if zooms:
        # zoompan keeps output size stable while applying short attention-event zooms
        base_filter += (
            f",zoompan=z='{zoom_expr}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d=1:s={target_w}x{target_h}:fps=30"
        )

    video_filter = base_filter + f",subtitles={ass.as_posix()}"

    slug = "".join(ch if ch.isalnum() or ch in "-_ " else "" for ch in candidate.hook.lower())
    slug = "-".join(slug.split())[:60] or "clip"
    output = output_dir / f"{index:02d}-{plan.variant}-{slug}.mp4"

    cmd = [
        "ffmpeg", "-y", "-ss", f"{render_start:.3f}", "-i", str(render_src),
        "-t", f"{duration:.3f}", "-vf", video_filter,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k",
    ]
    if loudnorm:
        cmd += ["-af", "loudnorm=I=-14:TP=-1.5:LRA=11"]
    cmd += ["-movflags", "+faststart", str(output)]
    subprocess.run(cmd, check=True)

    meta = {
        "candidate_index": index,
        "variant": plan.variant,
        "edit_profile": plan.edit_profile,
        "start": start,
        "end": end,
        "source_score": candidate.overall,
        "edit_plan": edit,
        "output": str(output.resolve()),
    }
    output.with_suffix(".meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return output
