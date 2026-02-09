"""Rich console UI helpers."""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def success_panel(message: str) -> Panel:
    """Create a success message panel."""
    return Panel(
        f"[green]\u2713[/green] {message}",
        border_style="green",
        padding=(0, 1),
    )


def error_panel(message: str, details: str | None = None) -> Panel:
    """Create an error message panel."""
    content = f"[red]\u2717[/red] {message}"
    if details:
        content += f"\n\n[dim]{details}[/dim]"
    return Panel(
        content,
        title="Error",
        border_style="red",
        padding=(0, 1),
    )
