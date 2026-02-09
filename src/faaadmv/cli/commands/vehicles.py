"""Vehicles management command implementation."""

import logging

import typer
from pydantic import ValidationError
from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.table import Table

from faaadmv.cli.ui import error_panel, success_panel
from faaadmv.core.config import ConfigManager
from faaadmv.models import VehicleInfo

logger = logging.getLogger(__name__)
console = Console()


def run_vehicles(
    add: bool = False,
    remove: str | None = None,
    default: str | None = None,
) -> None:
    """Run the vehicles management command."""
    console.print()

    manager = ConfigManager()
    if not manager.exists:
        console.print(
            error_panel(
                "No configuration found.",
                "Run 'faaadmv register' to set up your first vehicle.",
            )
        )
        raise typer.Exit(1)

    config = manager.load()

    if add:
        _handle_add(manager, config)
    elif remove:
        _handle_remove(manager, config, remove)
    elif default:
        _handle_default(manager, config, default)
    else:
        _handle_list(config)


def _handle_list(config) -> None:
    """Display list of registered vehicles."""
    table = Table(title="Registered Vehicles", show_lines=False)
    table.add_column("#", style="dim", width=3)
    table.add_column("Plate", style="bold")
    table.add_column("VIN", style="dim")
    table.add_column("Nickname")
    table.add_column("Default", justify="center")

    for i, entry in enumerate(config.vehicles, 1):
        default_marker = "[green]\u2713[/green]" if entry.is_default else ""
        table.add_row(
            str(i),
            entry.vehicle.plate,
            entry.vehicle.masked_vin,
            entry.nickname or "[dim]-[/dim]",
            default_marker,
        )

    console.print()
    console.print(table)
    console.print()
    console.print(f"[dim]  {len(config.vehicles)} vehicle(s) registered.[/dim]")


def _handle_add(manager, config) -> None:
    """Add a new vehicle interactively."""
    console.print()
    console.print("[bold cyan]--- Add Vehicle ---[/bold cyan]")
    console.print()

    while True:
        plate = Prompt.ask("  License plate number")
        vin = Prompt.ask("  Last 5 digits of VIN")

        try:
            vehicle = VehicleInfo(plate=plate, vin_last5=vin)
            break
        except ValidationError as e:
            for error in e.errors():
                field = error["loc"][-1]
                msg = error["msg"]
                console.print(f"  [red]Invalid {field}: {msg}[/red]")
            console.print("  [dim]Please try again.[/dim]")
            console.print()

    # Check for duplicate plate
    if config.get_vehicle(vehicle.plate):
        console.print()
        console.print(
            error_panel(
                f"Vehicle {vehicle.plate} already registered.",
                "Use 'faaadmv register --vehicle' to update it.",
            )
        )
        raise typer.Exit(1)

    nickname = Prompt.ask("  Nickname (optional)", default="")
    nickname = nickname.strip() or None

    make_default = False
    if len(config.vehicles) > 0:
        make_default = Confirm.ask("  Set as default vehicle?", default=False)

    updated = config.add_vehicle(vehicle, nickname=nickname, is_default=make_default)
    manager.save(updated)

    console.print()
    console.print(success_panel(f"Vehicle {vehicle.plate} added."))


def _handle_remove(manager, config, plate: str) -> None:
    """Remove a vehicle by plate."""
    entry = config.get_vehicle(plate)
    if not entry:
        console.print()
        console.print(
            error_panel(
                f"Vehicle '{plate}' not found.",
                f"Registered plates: {', '.join(v.plate for v in config.vehicles)}",
            )
        )
        raise typer.Exit(1)

    if len(config.vehicles) == 1:
        console.print()
        console.print(
            error_panel(
                "Cannot remove the last vehicle.",
                "Use 'faaadmv register --reset' to delete all configuration.",
            )
        )
        raise typer.Exit(1)

    console.print()
    if not Confirm.ask(
        f"  Remove vehicle [bold]{entry.vehicle.plate}[/bold]"
        f" ({entry.nickname or entry.vehicle.masked_vin})?",
        default=False,
    ):
        console.print("[dim]  Cancelled.[/dim]")
        return

    updated = config.remove_vehicle(plate)
    manager.save(updated)

    console.print()
    console.print(success_panel(f"Vehicle {entry.vehicle.plate} removed."))

    if entry.is_default:
        new_default = updated.default_vehicle
        console.print(f"[dim]  New default: {new_default.vehicle.plate}[/dim]")


def _handle_default(manager, config, plate: str) -> None:
    """Set a vehicle as default."""
    entry = config.get_vehicle(plate)
    if not entry:
        console.print()
        console.print(
            error_panel(
                f"Vehicle '{plate}' not found.",
                f"Registered plates: {', '.join(v.plate for v in config.vehicles)}",
            )
        )
        raise typer.Exit(1)

    if entry.is_default:
        console.print()
        console.print(f"[dim]  {entry.vehicle.plate} is already the default.[/dim]")
        return

    updated = config.set_default(plate)
    manager.save(updated)

    console.print()
    console.print(success_panel(f"{entry.vehicle.plate} set as default vehicle."))
