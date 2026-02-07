"""Rich console UI helpers."""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

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


def warning_panel(message: str) -> Panel:
    """Create a warning message panel."""
    return Panel(
        f"[yellow]\u26a0[/yellow] {message}",
        border_style="yellow",
        padding=(0, 1),
    )


def info_panel(message: str, title: str | None = None) -> Panel:
    """Create an info message panel."""
    return Panel(
        message,
        title=title,
        border_style="blue",
        padding=(1, 2),
    )


def masked_value(value: str, visible_chars: int = 4) -> str:
    """Mask a value, showing only last N characters."""
    if len(value) <= visible_chars:
        return "*" * len(value)
    return "*" * (len(value) - visible_chars) + value[-visible_chars:]


def format_phone(digits: str) -> str:
    """Format phone number for display."""
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    return digits


def create_config_table(config: dict) -> Table:
    """Create a table displaying configuration."""
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Field", style="dim")
    table.add_column("Value")

    table.add_row("Vehicle", f"{config.get('plate', 'N/A')} / {config.get('vin', 'N/A')}")
    table.add_row("Owner", config.get("owner", "N/A"))
    table.add_row("Email", config.get("email", "N/A"))
    table.add_row("Card", config.get("card", "N/A"))

    return table


def create_fee_table(fees: list[tuple[str, float]]) -> Table:
    """Create a table displaying fees."""
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Description", style="white")
    table.add_column("Amount", style="white", justify="right")

    for desc, amount in fees:
        table.add_row(desc, f"${amount:.2f}")

    return table
