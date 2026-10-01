from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from clipfarm.core.io import read_json
from clipfarm.analysis.multimodal import analyze_multimodal, write_signals
from clipfarm.core.models import ClipCandidate, Transcript
from clipfarm.intelligence import rank_candidates
from clipfarm.editing.renderer import CAPTION_STYLES, TARGETS, render_candidates
from clipfarm.pipeline import run_pipeline

app = typer.Typer(no_args_is_help=True)
console = Console()


def _print_candidates(candidates: list[dict]) -> None:
    table = Table(title="Clipfarm candidates")
    table.add_column("#", justify="right")
    table.add_column("Start")
    table.add_column("End")
    table.add_column("Score")
    table.add_column("Hook")
    table.add_column("Reasons")
    for idx, item in enumerate(candidates, 1):
        table.add_row(
            str(idx),
            f"{item['start']:.2f}",
            f"{item['end']:.2f}",
            f"{item['overall']:.2f}/10",
            item["hook"],
            ", ".join(item.get("reasons") or []),
        )
    console.print(table)


def _parse_indexes(spec: str | None) -> set[int] | None:
    if not spec:
        return None
    indexes: set[int] = set()
    for token in spec.replace(" ", "").split(","):
        if not token:
            continue
        if not token.isdigit() or int(token) < 1:
            raise typer.BadParameter("Use comma-separated positive indexes, e.g. 1,3,5")
        indexes.add(int(token))
    return indexes or None


@app.command()
def run(
    source: str = typer.Argument(..., help="Authorized video URL or local file path"),
    output_dir: Path = typer.Option(Path("runs"), "--output-dir"),
    model: str = typer.Option("small", "--model"),
    device: str = typer.Option("cpu", "--device"),
    compute_type: str = typer.Option("int8", "--compute-type"),
    language: str | None = typer.Option(None, "--language"),
    min_duration: float = typer.Option(18.0, "--min-duration"),
    max_duration: float = typer.Option(45.0, "--max-duration"),
    clips: int = typer.Option(8, "--clips", min=1, max=30),
) -> None:
    manifest = run_pipeline(
        source=source,
        output_root=output_dir,
        model=model,
        device=device,
        compute_type=compute_type,
        language=language,
        min_duration=min_duration,
        max_duration=max_duration,
        clips=clips,
    )
    candidates = read_json(Path(manifest.candidates_path))
    _print_candidates(candidates)
    console.print(f"Run manifest: [bold]{manifest.path}[/bold]")
    console.print(
        "Next: render previews with "
        f"[bold]clipfarm render {manifest.path} --preview[/bold]"
    )


@app.command()
def analyze(
    video: Path = typer.Argument(..., exists=True, help="Local video file to analyze"),
    out: Path = typer.Option(Path("signals.json"), "--out"),
) -> None:
    """Extract CPU-friendly audio/visual signals without clipping or rendering."""
    signals = analyze_multimodal(video)
    write_signals(signals, out)
    console.print(f"Signals written to [bold]{out}[/bold]")
    console.print(
        f"audio={len(signals.audio_rms)} scene_changes={len(signals.scene_changes)} "
        f"motion={len(signals.motion)} faces={len(signals.face_presence)}"
    )


@app.command()
def render(
    manifest: Path = typer.Argument(..., exists=True, help="Path to a run manifest.json"),
    out: Path | None = typer.Option(None, "--out", help="Output directory; defaults to <run>/clips"),
    aspect: str = typer.Option("9:16", "--aspect", help="9:16, 1:1, or 16:9"),
    style: str = typer.Option("default", "--style", help="Caption style"),
    preview: bool = typer.Option(False, "--preview", help="Render smaller, faster review copies"),
    clips: str | None = typer.Option(None, "--clips", help="Candidate indexes, e.g. 1,3,5"),
    loudnorm: bool = typer.Option(True, "--loudnorm/--no-loudnorm"),
) -> None:
    if aspect not in TARGETS:
        raise typer.BadParameter(f"Unknown aspect. Choose: {', '.join(TARGETS)}")
    if style not in CAPTION_STYLES:
        raise typer.BadParameter(f"Unknown style. Choose: {', '.join(CAPTION_STYLES)}")

    raw_manifest = read_json(manifest)
    source_path = Path(raw_manifest["source"]["local_path"])
    transcript_path = Path(raw_manifest["transcript_path"])
    candidates_path = Path(raw_manifest["candidates_path"])
    run_dir = Path(raw_manifest["run_dir"])
    output_dir = out or (run_dir / ("previews" if preview else "clips"))

    transcript = Transcript.model_validate(read_json(transcript_path))
    candidates = [ClipCandidate.model_validate(item) for item in read_json(candidates_path)]
    indexes = _parse_indexes(clips)
    if indexes:
        bad = sorted(i for i in indexes if i > len(candidates))
        if bad:
            raise typer.BadParameter(f"Candidate index out of range: {bad}; max is {len(candidates)}")

    rendered = render_candidates(
        source=source_path,
        transcript=transcript,
        candidates=candidates,
        output_dir=output_dir,
        aspect=aspect,
        caption_style=style,
        preview=preview,
        loudnorm=loudnorm,
        indexes=indexes,
    )
    console.print(f"Rendered [bold]{len(rendered)}[/bold] clip(s) to [bold]{output_dir}[/bold]")
    for path in rendered:
        console.print(f"  • {path}")


if __name__ == "__main__":
    app()
