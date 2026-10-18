"""Command line interface."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from .export import write_csv, write_xlsx
from .extract import extract_file
from .llm import LLMSettings, refine

app = typer.Typer(add_completion=False, help="Turn receipt photos into CSV or Excel, offline.")
console = Console()

ALLOWED = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".pdf"}


def _table(receipts) -> Table:
    table = Table(title=f"snap2sheet · {len(receipts)} receipt(s)")
    table.add_column("File", no_wrap=True)
    table.add_column("Merchant")
    table.add_column("Date")
    table.add_column("Total", justify="right")
    table.add_column("Tax", justify="right")
    table.add_column("Cur")
    table.add_column("Conf", justify="right")
    for receipt in receipts:
        table.add_row(
            receipt.source,
            receipt.merchant or "-",
            receipt.date or "-",
            f"{receipt.total:.2f}" if receipt.total is not None else "-",
            f"{receipt.tax:.2f}" if receipt.tax is not None else "-",
            receipt.currency or "-",
            f"{receipt.confidence:.2f}",
        )
    return table


def _scan(path: Path, order: str, use_llm: bool):
    receipt = extract_file(path, order=order)
    if use_llm:
        settings = LLMSettings.from_env()
        if not settings.ready:
            console.print("[yellow]--llm requested but SNAP2SHEET_LLM_API_KEY is not set; using heuristics.[/yellow]")
        else:
            receipt = refine(receipt, settings)
    return receipt


@app.command()
def scan(
    file: Path = typer.Argument(..., exists=True, readable=True),
    order: str = typer.Option("mdy", help="Date order: mdy or dmy."),
    llm: bool = typer.Option(False, "--llm", help="Refine fields with an OpenAI-compatible LLM."),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Extract one receipt and print the fields."""
    receipt = _scan(file, order, llm)
    if json_out:
        typer.echo(json.dumps(receipt.to_dict(), indent=2, ensure_ascii=False))
        return
    console.print(_table([receipt]))
    if receipt.items:
        console.print(f"[dim]line items: {len(receipt.items)}[/dim]")
    for warning in receipt.warnings:
        console.print(f"[yellow]! {warning}[/yellow]")


@app.command()
def batch(
    folder: Path = typer.Argument(..., exists=True, file_okay=False),
    output: Path = typer.Option(Path("expenses.csv"), "--output", "-o"),
    xlsx: Path | None = typer.Option(None, "--xlsx"),
    order: str = typer.Option("mdy"),
    llm: bool = typer.Option(False, "--llm"),
    recursive: bool = typer.Option(False, "--recursive", "-r"),
) -> None:
    """Scan a folder of receipts and write CSV (and optionally Excel)."""
    files = sorted(folder.rglob("*") if recursive else folder.iterdir())
    files = [path for path in files if path.suffix.lower() in ALLOWED and path.is_file()]
    if not files:
        console.print("[red]No receipt images or PDFs found.[/red]")
        raise typer.Exit(code=1)

    receipts = []
    seen: dict[str, str] = {}
    for path in files:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest in seen:
            console.print(f"[yellow]skip duplicate:[/yellow] {path.name} (same as {seen[digest]})")
            continue
        seen[digest] = path.name
        receipts.append(_scan(path, order, llm))

    write_csv(receipts, output)
    console.print(_table(receipts))
    console.print(f"[green]CSV:[/green] {output}")
    if xlsx:
        write_xlsx(receipts, xlsx)
        console.print(f"[green]XLSX:[/green] {xlsx}")


@app.command()
def serve(host: str = typer.Option("127.0.0.1"), port: int = typer.Option(8789)) -> None:
    """Start the local upload/review UI."""
    import uvicorn

    uvicorn.run("snap2sheet.server:app", host=host, port=port, log_level="info")


@app.command()
def doctor() -> None:
    """Check OCR and export readiness."""
    import openpyxl
    import pymupdf

    console.print(f"pymupdf: [bold]{pymupdf.__version__}[/bold]")
    console.print(f"openpyxl: [bold]{openpyxl.__version__}[/bold]")
    console.print("[green]ready[/green]")
