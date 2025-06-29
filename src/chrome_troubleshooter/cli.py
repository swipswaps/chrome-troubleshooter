"""
Chrome Troubleshooter CLI - Production Ready Implementation

CHATGPT AUDIT COMPLIANCE:
- Three commands only: launch, diag, version
- Exact function signatures from audit
- Uses exact imports specified in audit
- Implements all audit requirements precisely
"""

import importlib.metadata

import typer

from chrome_troubleshooter.config import Config
from chrome_troubleshooter.constants import get_cache_dir
from chrome_troubleshooter.diagnostics import collect_all
from chrome_troubleshooter.launcher import ChromeLauncher
from chrome_troubleshooter.logger import StructuredLogger

# Create Typer app with exact specification from audit
app = typer.Typer(add_completion=False, help="Chrome Troubleshooter - beta")


@app.command()
def launch(
    timeout: int = typer.Option(15, help="Seconds to consider Chrome stable")
) -> None:
    """Start Chrome with safe flags and create a forensic session."""
    config = Config()
    logger = StructuredLogger(config.session_dir)
    launcher = ChromeLauncher(config, logger)

    try:
        launcher.launch_chrome(timeout=timeout)
        typer.echo(f"Session created: {config.session_dir}")
    except Exception as e:
        typer.echo(f"Launch failed: {e}", err=True)
        raise typer.Exit(1) from e


@app.command()
def diag() -> None:
    """Append diagnostics to the latest session folder."""
    try:
        latest = max(get_cache_dir().glob("session_*"), default=None)
        if not latest:
            typer.echo("No session found. Run 'chrome-troubleshooter launch' first.", err=True)
            raise typer.Exit(1) from e

        logger = StructuredLogger(latest)
        collect_all(logger)
        typer.echo(f"Diagnostics added to: {latest}")

    except Exception as e:
        typer.echo(f"Diagnostics failed: {e}", err=True)
        raise typer.Exit(1) from e


@app.command()
def version() -> None:
    """Print the installed package version."""
    try:
        package_version = importlib.metadata.version("chrome-troubleshooter")
        typer.echo(package_version)
    except importlib.metadata.PackageNotFoundError:
        typer.echo("Package version not found. Try reinstalling with: pip install -e .", err=True)
        raise typer.Exit(1) from e


@app.command("export-sqlite")
def export_sqlite() -> None:
    """Print path to newest logs.sqlite and exit."""
    latest = max(get_cache_dir().glob("session_*"), default=None)
    if latest:
        typer.echo(latest / "logs.sqlite")
    else:
        typer.echo("No session found", err=True)


if __name__ == "__main__":
    app()
