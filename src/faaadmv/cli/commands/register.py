"""Register command implementation."""

from typing import Optional

import typer
from pydantic import ValidationError
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from faaadmv.cli.ui import error_panel, success_panel
from faaadmv.core.config import ConfigManager
from faaadmv.core.keychain import PaymentKeychain
from faaadmv.exceptions import ConfigDecryptionError, ConfigNotFoundError
from faaadmv.models import UserConfig, VehicleEntry, VehicleInfo
from faaadmv.models.owner import Address, OwnerInfo
from faaadmv.models.payment import PaymentInfo

console = Console()


def run_register(
    vehicle_only: bool = False,
    payment_only: bool = False,
    verify_only: bool = False,
    reset_config: bool = False,
) -> None:
    """Run the register command."""
    if reset_config:
        _handle_reset()
        return

    if verify_only:
        _handle_verify()
        return

    manager = ConfigManager()
    existing_config: Optional[UserConfig] = None
    existing_passphrase: Optional[str] = None

    # For partial updates, load existing config first
    if (vehicle_only or payment_only) and manager.exists:
        console.print()
        existing_passphrase = Prompt.ask("  Enter your passphrase", password=True)
        try:
            existing_config = manager.load(existing_passphrase)
        except ConfigDecryptionError:
            console.print()
            console.print(error_panel("Wrong passphrase.", "Check your passphrase and try again."))
            raise typer.Exit(1)
    elif vehicle_only or payment_only:
        console.print()
        console.print(error_panel(
            "No existing configuration found.",
            "Run 'faaadmv register' first to set up all your information.",
        ))
        raise typer.Exit(1)

    # Interactive setup
    console.print()
    if not (vehicle_only or payment_only):
        console.print(
            Panel.fit(
                "[bold]Welcome to faaadmv![/bold]\n\nLet's set up your vehicle registration.",
                border_style="blue",
            )
        )
    else:
        section = "vehicle" if vehicle_only else "payment"
        console.print(
            Panel.fit(
                f"[bold]Updating {section} information[/bold]",
                border_style="blue",
            )
        )
    console.print()

    try:
        vehicle_data = None
        owner_data = None
        payment_data = None

        if not payment_only:
            vehicle_data = _collect_vehicle_info()
            if not vehicle_only:
                owner_data = _collect_owner_info()

        if payment_only:
            payment_data = _collect_payment_info()
        elif not vehicle_only:
            # Payment is optional during full registration
            console.print("[bold cyan]--- Payment (Optional) ---[/bold cyan]")
            console.print()
            console.print("[dim]  Payment info is only needed for renewals.[/dim]")
            console.print("[dim]  You can add it later with 'faaadmv register --payment'.[/dim]")
            console.print()
            if Confirm.ask("  Add payment information now?", default=False):
                console.print()
                payment_data = _collect_payment_info()
            else:
                console.print()

        # Build and validate models
        vehicle = _build_vehicle(vehicle_data, existing_config)
        owner = _build_owner(owner_data, existing_config)
        payment = _build_payment(payment_data)

        if vehicle is None or owner is None:
            console.print(error_panel("Missing required information."))
            raise typer.Exit(1)

        if vehicle_only and existing_config:
            # Add/update vehicle in existing config
            existing_entry = existing_config.get_vehicle(vehicle.plate)
            if existing_entry:
                # Update existing vehicle (replace VehicleInfo)
                new_vehicles = []
                for v in existing_config.vehicles:
                    if v.vehicle.plate == vehicle.plate:
                        new_vehicles.append(v.model_copy(update={"vehicle": vehicle}))
                    else:
                        new_vehicles.append(v)
                config = existing_config.model_copy(update={"vehicles": new_vehicles})
            else:
                # Add as new vehicle
                nickname = Prompt.ask("  Nickname (optional)", default="")
                nickname = nickname.strip() or None
                make_default = Confirm.ask("  Set as default?", default=False)
                config = existing_config.add_vehicle(vehicle, nickname=nickname, is_default=make_default)
        elif existing_config and payment_only:
            config = existing_config
        else:
            # Fresh registration
            config = UserConfig(
                vehicles=[VehicleEntry(vehicle=vehicle, is_default=True)],
                owner=owner,
            )

        # Get passphrase
        if existing_passphrase:
            passphrase = existing_passphrase
        else:
            passphrase = _prompt_passphrase()

        # Save config
        manager.save(config, passphrase)

        # Save payment to keychain
        if payment:
            PaymentKeychain.store(payment)

        console.print()
        console.print(success_panel("Configuration saved securely."))
        console.print()
        console.print("[dim]Run 'faaadmv status' to check your registration.[/dim]")

    except KeyboardInterrupt:
        console.print()
        console.print("[yellow]Setup cancelled.[/yellow]")
        raise typer.Exit(1)


def _handle_reset() -> None:
    """Handle config reset."""
    console.print()
    if Confirm.ask("[yellow]Delete all saved configuration?[/yellow]", default=False):
        manager = ConfigManager()
        deleted_config = manager.delete()
        PaymentKeychain.delete()

        if deleted_config:
            console.print(success_panel("Configuration and payment data deleted."))
        else:
            console.print("[dim]No configuration found to delete.[/dim]")
    else:
        console.print("[dim]Cancelled.[/dim]")


def _handle_verify() -> None:
    """Handle config verification."""
    console.print()

    manager = ConfigManager()
    if not manager.exists:
        console.print(error_panel(
            "No configuration found.",
            "Run 'faaadmv register' to set up your vehicle.",
        ))
        raise typer.Exit(1)

    passphrase = Prompt.ask("  Enter your passphrase", password=True)

    try:
        config = manager.load(passphrase)
    except ConfigDecryptionError:
        console.print()
        console.print(error_panel("Wrong passphrase.", "Check your passphrase and try again."))
        raise typer.Exit(1)

    payment = PaymentKeychain.retrieve()

    # Build display table
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Field", style="dim")
    table.add_column("Value")

    table.add_row("Vehicle", f"{config.vehicle.plate} / {config.vehicle.masked_vin}")
    table.add_row("Owner", config.owner.full_name)
    table.add_row("Phone", config.owner.formatted_phone)
    table.add_row("Email", config.owner.masked_email)
    table.add_row("Address", config.owner.address.formatted)

    if payment:
        table.add_row("Card", f"{payment.masked_number} (exp {payment.expiry_display})")
        table.add_row("Card Type", payment.card_type)
    else:
        table.add_row("Card", "[yellow]Not found in keychain[/yellow]")

    console.print()
    console.print(
        Panel(
            table,
            title="Saved Configuration",
            border_style="blue",
            padding=(1, 2),
        )
    )
    console.print()
    console.print(success_panel("All fields valid."))


def _collect_vehicle_info() -> dict:
    """Collect vehicle information interactively with validation."""
    console.print("[bold cyan]--- Vehicle Information ---[/bold cyan]")
    console.print()

    while True:
        plate = Prompt.ask("  License plate number")
        vin = Prompt.ask("  Last 5 digits of VIN")

        try:
            VehicleInfo(plate=plate, vin_last5=vin)
            break
        except ValidationError as e:
            for error in e.errors():
                field = error["loc"][-1]
                msg = error["msg"]
                console.print(f"  [red]Invalid {field}: {msg}[/red]")
            console.print("  [dim]Please try again.[/dim]")
            console.print()

    console.print()
    return {"plate": plate, "vin_last5": vin}


def _collect_owner_info() -> dict:
    """Collect owner information interactively with validation."""
    while True:
        console.print("[bold cyan]--- Owner Information ---[/bold cyan]")
        console.print()

        name = Prompt.ask("  Full name")
        phone = Prompt.ask("  Phone number")
        email = Prompt.ask("  Email address")

        console.print()
        console.print("[bold cyan]--- Address ---[/bold cyan]")
        console.print()

        street = Prompt.ask("  Street address")
        city = Prompt.ask("  City")
        state = Prompt.ask("  State", default="CA")
        zip_code = Prompt.ask("  ZIP code")

        try:
            OwnerInfo(
                full_name=name,
                phone=phone,
                email=email,
                address=Address(
                    street=street,
                    city=city,
                    state=state,
                    zip_code=zip_code,
                ),
            )
            break
        except ValidationError as e:
            for error in e.errors():
                field = ".".join(str(loc) for loc in error["loc"])
                msg = error["msg"]
                console.print(f"  [red]Invalid {field}: {msg}[/red]")
            console.print("  [dim]Please try again.[/dim]")
            console.print()

    console.print()
    return {
        "full_name": name,
        "phone": phone,
        "email": email,
        "address": {
            "street": street,
            "city": city,
            "state": state,
            "zip_code": zip_code,
        },
    }


def _collect_payment_info() -> dict:
    """Collect payment information interactively with validation."""
    console.print("[bold cyan]--- Payment Information ---[/bold cyan]")
    console.print()

    while True:
        card = Prompt.ask("  Card number", password=True)
        exp_month = Prompt.ask("  Expiration month (MM)")
        exp_year = Prompt.ask("  Expiration year (YY or YYYY)")
        cvv = Prompt.ask("  CVV", password=True)
        billing_zip = Prompt.ask("  Billing ZIP code")

        # Normalize year
        try:
            year_int = int(exp_year)
            if year_int < 100:
                year_int += 2000
            month_int = int(exp_month)
        except ValueError:
            console.print("  [red]Invalid expiration date format.[/red]")
            console.print("  [dim]Please try again.[/dim]")
            console.print()
            continue

        try:
            PaymentInfo(
                card_number=card,
                expiry_month=month_int,
                expiry_year=year_int,
                cvv=cvv,
                billing_zip=billing_zip,
            )
            break
        except ValidationError as e:
            for error in e.errors():
                field = error["loc"][-1]
                msg = error["msg"]
                console.print(f"  [red]Invalid {field}: {msg}[/red]")
            console.print("  [dim]Please try again.[/dim]")
            console.print()

    console.print()
    return {
        "card_number": card,
        "expiry_month": month_int,
        "expiry_year": year_int,
        "cvv": cvv,
        "billing_zip": billing_zip,
    }


def _build_vehicle(
    data: Optional[dict],
    existing: Optional[UserConfig],
) -> Optional[VehicleInfo]:
    """Build VehicleInfo from collected data or existing config."""
    if data:
        return VehicleInfo(**data)
    if existing:
        return existing.vehicle
    return None


def _build_owner(
    data: Optional[dict],
    existing: Optional[UserConfig],
) -> Optional[OwnerInfo]:
    """Build OwnerInfo from collected data or existing config."""
    if data:
        return OwnerInfo(**data)
    if existing:
        return existing.owner
    return None


def _build_payment(data: Optional[dict]) -> Optional[PaymentInfo]:
    """Build PaymentInfo from collected data."""
    if data:
        return PaymentInfo(**data)
    return None


def _prompt_passphrase() -> str:
    """Prompt for a new passphrase with confirmation."""
    console.print("[bold cyan]--- Security ---[/bold cyan]")
    console.print()
    console.print("[dim]  Choose a passphrase to encrypt your configuration.[/dim]")
    console.print("[dim]  You'll need this passphrase for status checks and renewals.[/dim]")
    console.print()

    while True:
        passphrase = Prompt.ask("  Passphrase", password=True)

        if len(passphrase) < 4:
            console.print("  [red]Passphrase must be at least 4 characters.[/red]")
            continue

        confirm = Prompt.ask("  Confirm passphrase", password=True)

        if passphrase != confirm:
            console.print("  [red]Passphrases don't match. Try again.[/red]")
            console.print()
            continue

        return passphrase
