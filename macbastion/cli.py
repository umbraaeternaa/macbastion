"""Command-line interface for macbastion."""

import click
from rich.console import Console
from rich.table import Table

from macbastion.scanners.ports import scan_listening_ports
from macbastion.scanners import stealth as stealth_mod

console = Console()


@click.group()
def cli() -> None:
    """macbastion — defensive security audit tool for macOS."""


# ──────────────────────────────────────────────────────────
# scan group
# ──────────────────────────────────────────────────────────
@cli.group()
def scan() -> None:
    """Run individual audit scanners."""


@scan.command("ports")
def scan_ports() -> None:
    """List all listening TCP ports with exposure classification."""
    console.print("[bold cyan]Scanning listening ports...[/bold cyan]")
    console.print("[dim]You may be prompted for your password (sudo).[/dim]\n")

    try:
        ports = scan_listening_ports()
    except RuntimeError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise SystemExit(1)

    table = Table(title="Listening Ports", show_lines=False)
    table.add_column("Port", style="cyan", justify="right")
    table.add_column("Process", style="green")
    table.add_column("PID", justify="right")
    table.add_column("User")
    table.add_column("Address")
    table.add_column("Exposure")

    exposure_order = {"all_interfaces": 0, "specific": 1, "localhost": 2}
    ports.sort(key=lambda p: (exposure_order[p.exposure], p.port))

    for p in ports:
        if p.exposure == "all_interfaces":
            exposure_str = "[bold red]ALL INTERFACES[/bold red]"
        elif p.exposure == "specific":
            exposure_str = "[yellow]specific[/yellow]"
        else:
            exposure_str = "[green]localhost[/green]"

        table.add_row(
            str(p.port), p.command, str(p.pid), p.user, p.address, exposure_str,
        )

    console.print(table)
    console.print(f"\n[dim]Total: {len(ports)} listening sockets.[/dim]")


# ──────────────────────────────────────────────────────────
# stealth group
# ──────────────────────────────────────────────────────────
@cli.group()
def stealth() -> None:
    """Toggle stealth mode (AirDrop ⇄ random hostname)."""


@stealth.command("status")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON (for SwiftBar).")
def stealth_status(as_json: bool) -> None:
    """Show current stealth state."""
    raise SystemExit(stealth_mod.cmd_status(json_output=as_json))


@stealth.command("on")
@click.option("--hard", is_flag=True, help="Hard mode: also kill Bluetooth + prompt for reboot.")
def stealth_on(hard: bool) -> None:
    """Enable stealth (needs sudo)."""
    raise SystemExit(stealth_mod.cmd_on(hard=hard))


@stealth.command("off")
def stealth_off() -> None:
    """Disable stealth, restore AirDrop mode (needs sudo)."""
    raise SystemExit(stealth_mod.cmd_off())


if __name__ == "__main__":
    cli()
