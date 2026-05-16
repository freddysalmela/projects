from rich.console import Console
from rich.text import Text

console = Console()


def print_banner():
    console.print()
    console.print("[bold cyan]╔══════════════════════════════════════╗[/]")
    console.print("[bold cyan]║       BOOSTER  —  GARAGE AI          ║[/]")
    console.print("[bold cyan]╚══════════════════════════════════════╝[/]")
    console.print()


def print_user(text: str):
    console.print(f"[bold yellow]YOU:[/] {text}")


def print_booster(text: str):
    console.print(f"[bold cyan]BOOSTER:[/] {text}")


def print_status(text: str):
    console.print(f"[dim]  {text}[/]")


def print_tool_use(tool_name: str, inputs: dict):
    args = ", ".join(f"{k}={repr(v)}" for k, v in inputs.items())
    console.print(f"[bold magenta]  ⚙ {tool_name}({args})[/]")


def print_error(text: str):
    console.print(f"[bold red]ERROR:[/] {text}")
