from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from clipfarm.analysis.multimodal import analyze_multimodal, write_signals
from clipfarm.batch_engine import run_batch
from clipfarm.core.io import read_json
from clipfarm.core.models import ClipCandidate, Transcript
from clipfarm.pipeline import run_pipeline
from clipfarm.production import execute_run

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


@app.command()
def run(
    source: str = typer.Argument(..., help="Authorized video URL or local file path"),
    output_dir: Path = typer.Option(Path("runs"), "--output-dir"),
    model: str = typer.Option("small", "--model"),
    device: str = typer.Option("cpu", "--device"),
    compute_type: str = typer.Option("int8", "--compute-type"),
    clips: int = typer.Option(8, "--clips", min=1, max=30),
) -> None:
    manifest = run_pipeline(
        source=source,
        output_root=output_dir,
        model=model,
        device=device,
        compute_type=compute_type,
        clips=clips,
    )
    candidates = read_json(Path(manifest.candidates_path))
    _print_candidates(candidates)
    console.print(f"Run manifest: [bold]{manifest.path}[/bold]")
    console.print(f"Produce finished clips with: [bold]clipfarm produce {manifest.path}[/bold]")


@app.command()
def produce(
    manifest: Path = typer.Argument(..., exists=True),
    top_n: int = typer.Option(8, "--top", min=1, max=30),
    variants: str = typer.Option("balanced,tight,punchy", "--variants"),
    preview: bool = typer.Option(False, "--preview"),
    out: Path | None = typer.Option(None, "--out"),
) -> None:
    selected = tuple(v.strip() for v in variants.split(",") if v.strip())
    allowed = {"balanced", "tight", "punchy"}
    bad = [v for v in selected if v not in allowed]
    if bad:
        raise typer.BadParameter(f"Unknown variant(s): {bad}. Choose from {sorted(allowed)}")
    report = execute_run(manifest, top_n=top_n, variants=selected, output_dir=out, preview=preview)
    console.print(
        f"Finished: [bold]{report['summary']['rendered']}[/bold] | "
        f"Rejected: [bold]{report['summary']['rejected']}[/bold]"
    )


@app.command()
def batch(
    sources: Path = typer.Argument(..., exists=True, help="Text file with one source per line"),
    output_dir: Path = typer.Option(Path("runs"), "--output-dir"),
    workers: int = typer.Option(1, "--workers", min=1, max=4),
    attempts: int = typer.Option(2, "--attempts", min=1, max=5),
    clips: int = typer.Option(8, "--clips", min=1, max=30),
) -> None:
    items = [
        line.strip() for line in sources.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    results = run_batch(
        items,
        output_root=output_dir,
        workers=workers,
        attempts=attempts,
        clips=clips,
    )
    console.print(
        f"Batch complete: {sum(r.ok for r in results)} succeeded, "
        f"{sum(not r.ok for r in results)} failed."
    )


@app.command()
def analyze(
    video: Path = typer.Argument(..., exists=True),
    out: Path = typer.Option(Path("signals.json"), "--out"),
) -> None:
    signals = analyze_multimodal(video)
    write_signals(signals, out)
    console.print(f"Signals written to [bold]{out}[/bold]")


if __name__ == "__main__":
    app()
