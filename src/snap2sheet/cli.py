"""Command line interface."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from . import __version__
from .dedupe import annotate_duplicates, count_duplicates
from .export import write_csv, write_xlsx
from .extract import extract_file
from .llm import LLMSettings, refine
from .ocr import backend_status

app = typer.Typer(add_completion=False, help="Turn receipt photos into CSV or Excel, offline.")
console = Console()


@app.callback(invoke_without_command=True)
def _root(
    version: bool = typer.Option(False, "--version", is_eager=True, help="Show the version and exit."),
) -> None:
    if version:
        console.print(__version__)
        raise typer.Exit()


ALLOWED = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".pdf"}


def _table(receipts) -> Table:
    duplicates = count_duplicates(receipts)
    title = f"snap2sheet · {len(receipts)} receipt(s)"
    if duplicates:
        title += f" · {duplicates} possible duplicate(s)"
    table = Table(title=title)
    table.add_column("File", no_wrap=True)
    table.add_column("Merchant")
    table.add_column("Date")
    table.add_column("Total", justify="right")
    table.add_column("Tax", justify="right")
    table.add_column("Cur")
    table.add_column("Conf", justify="right")
    table.add_column("Dup", justify="center")
    for receipt in receipts:
        table.add_row(
            receipt.source,
            receipt.merchant or "-",
            receipt.date or "-",
            f"{receipt.total:.2f}" if receipt.total is not None else "-",
            f"{receipt.tax:.2f}" if receipt.tax is not None else "-",
            receipt.currency or "-",
            f"{receipt.confidence:.2f}",
            "yes" if receipt.duplicate else "-",
        )
    return table


def _scan(path: Path, order: str, use_llm: bool, ocr: str = "auto"):
    receipt = extract_file(path, order=order, ocr_backend=ocr)
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
    ocr: str = typer.Option("auto", "--ocr", help="auto, rapidocr, or indra."),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Extract one receipt and print the fields."""
    receipt = _scan(file, order, llm, ocr)
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
    ocr: str = typer.Option("auto", "--ocr", help="auto, rapidocr, or indra."),
    recursive: bool = typer.Option(False, "--recursive", "-r"),
) -> None:
    """Scan a folder of receipts and write CSV (and optionally Excel)."""
    files = sorted(folder.rglob("*") if recursive else folder.iterdir())
    files = [path for path in files if path.suffix.lower() in ALLOWED and path.is_file()]
    if not files:
        console.print("[red]No receipt images or PDFs found.[/red]")
        raise typer.Exit(code=1)

    receipts = [_scan(path, order, llm, ocr) for path in files]
    annotate_duplicates(receipts)

    write_csv(receipts, output)
    console.print(_table(receipts))
    for receipt in receipts:
        if receipt.duplicate:
            console.print(
                f"[yellow]possible duplicate:[/yellow] {receipt.source} "
                f"matches {receipt.duplicate_of} (merchant, date, total)"
            )
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
    status = backend_status()
    console.print(f"OCR: [bold]{status['auto']}[/bold] (indra installed: {status['indra']})")
    console.print("[green]ready[/green]")
