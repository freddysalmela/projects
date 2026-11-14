import sys
import traceback
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.markup import escape

console = Console()


def print_banner():
    console.print()
    console.print("[bold cyan]╔══════════════════════════════════════╗[/]")
    console.print("[bold cyan]║         GAIA  —  GARAGE AI           ║[/]")
    console.print("[bold cyan]╚══════════════════════════════════════╝[/]")
    console.print()


def print_user(text: str):
    console.print(f"[bold yellow]YOU:[/] {escape(text)}")


def print_mycroft(text: str):
    console.print(f"[bold cyan]GAIA:[/] {escape(text)}")


def print_status(text: str):
    console.print(f"[dim]  {escape(text)}[/]")


def print_tool_use(tool_name: str, inputs: dict):
    args = ", ".join(f"{k}={repr(v)}" for k, v in inputs.items())
    console.print(f"[bold magenta]  ⚙ {tool_name}({escape(args)})[/]")


def print_error(text: str):
    console.print(f"[bold red]ERROR:[/] {escape(text)}", highlight=False)
    log_error(text)


_LOG_FILE = Path(__file__).parent.parent.parent / "gaia.log"


def log_error(text: str):
    """Append the error, and the traceback of the exception being handled if there is one,
    to gaia.log in the project folder, so it can be read after the console has scrolled or closed."""
    try:
        details = traceback.format_exc() if sys.exc_info()[0] else ""
        with open(_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"\n[{datetime.now():%Y-%m-%d %H:%M:%S}] {text}\n{details}")
    except Exception:
        pass
