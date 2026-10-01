from __future__ import annotations

import json
import subprocess
from pathlib import Path


def _ffprobe(path: Path) -> dict:
    result = subprocess.run(
        [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration,size:stream=index,codec_type,width,height",
            "-of", "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def technical_qa(path: Path, expected_aspect: str = "9:16") -> dict:
    out = {
        "path": str(path),
        "exists": path.exists(),
        "size_bytes": path.stat().st_size if path.exists() else 0,
        "duration": 0.0,
        "has_video": False,
        "has_audio": False,
        "width": None,
        "height": None,
        "aspect_ok": False,
        "duration_ok": False,
        "nonempty": False,
        "passed": False,
        "issues": [],
    }

    if not path.exists():
        out["issues"].append("missing_file")
        return out

    try:
        probe = _ffprobe(path)
    except Exception as exc:  # noqa: BLE001
        out["issues"].append(f"ffprobe_failed:{type(exc).__name__}")
        return out

    try:
        out["duration"] = float(probe.get("format", {}).get("duration") or 0.0)
    except ValueError:
        out["duration"] = 0.0

    for stream in probe.get("streams", []):
        if stream.get("codec_type") == "video":
            out["has_video"] = True
            out["width"] = stream.get("width")
            out["height"] = stream.get("height")
        elif stream.get("codec_type") == "audio":
            out["has_audio"] = True

    out["nonempty"] = out["size_bytes"] > 50_000
    out["duration_ok"] = 5.0 <= out["duration"] <= 90.0

    if out["width"] and out["height"]:
        ratio = out["width"] / float(out["height"])
        target = 9 / 16 if expected_aspect == "9:16" else 1.0
        out["aspect_ok"] = abs(ratio - target) < 0.03

    if not out["has_video"]:
        out["issues"].append("no_video")
    if not out["has_audio"]:
        out["issues"].append("no_audio")
    if not out["nonempty"]:
        out["issues"].append("too_small")
    if not out["duration_ok"]:
        out["issues"].append("duration_out_of_range")
    if not out["aspect_ok"]:
        out["issues"].append("wrong_aspect")

    out["passed"] = not out["issues"]
    return out
