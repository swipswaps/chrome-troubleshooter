"""
Typer-based CLI entry: launch, diagnostics, version.
Colour output uses Rich; exposed via console-script 'chrome-troubleshooter'.

This module implements the exact specification from the ChatGPT audit
for a clean, minimal CLI interface using Typer.

Key design decisions from the audit:
1. Typer for type-hint-driven CLI with autocompletion
2. Three core commands: launch, diag, version
3. Rich integration for colored output
4. Session-based diagnostic collection
5. Clean error handling and user feedback
6. Minimal dependencies (Typer includes Rich)
"""

from __future__ import annotations

import importlib.metadata

import typer

from .constants_audit import CACHE_DIR
from .diagnostics_audit import collect_all
from .launcher_audit import safe_launch
from .logger_audit import LogWriter

# Create Typer application with audit-specified configuration
# add_completion=False: Disable shell completion for simplicity
# help: Brief description matching the audit specification
app = typer.Typer(add_completion=False, help="Chrome Troubleshooter – beta")


@app.command()
def launch(
    timeout: int = typer.Option(15, help="Seconds to consider Chrome stable")
) -> None:
    """
    Start Chrome with safe flags and create a forensic session.

    This command implements the core Chrome launching functionality
    as specified in the ChatGPT audit:
    1. Single-instance lock to prevent conflicts
    2. Chrome executable detection with user override
    3. Safe flags that don't modify security behavior
    4. Timeout-based stability detection
    5. Session logging for forensic analysis

    Args:
        timeout: Number of seconds to wait before considering Chrome stable.
                If Chrome runs for this duration without exiting, it's
                considered successfully launched.

    The command creates a timestamped session directory in the cache
    and logs all activity for later analysis.
    """
    safe_launch(timeout)


@app.command()
def diag() -> None:
    """
    Append diagnostics to the latest session folder.

    This command implements diagnostic collection as specified in the
    ChatGPT audit:
    1. Find the most recent session directory
    2. Collect lightweight diagnostic data
    3. Append to existing session logs
    4. Handle missing session gracefully

    The diagnostic collection includes:
    - Recent kernel messages (dmesg from last minute)
    - Recent Chrome journal entries (last 50 entries)
    - Graceful handling of missing tools

    If no session exists, the command displays a helpful warning
    and exits cleanly.
    """
    # Find the most recent session directory
    # glob returns all matching directories, max() finds the newest
    # default=None handles the case where no sessions exist
    latest_session = max(CACHE_DIR.glob("session_*"), default=None)

    if latest_session:
        # Session found - collect diagnostics and append to logs
        # Create new LogWriter for the existing session
        session_logger = LogWriter(latest_session)
        collect_all(session_logger)

        # Provide user feedback about successful diagnostic collection
        typer.secho(
            f"Diagnostics collected and added to session: {latest_session.name}",
            fg=typer.colors.GREEN,
        )
    else:
        # No session found - display helpful warning
        # Use yellow color to indicate this is a warning, not an error
        typer.secho(
            "No session found! Run 'chrome-troubleshooter launch' first.",
            fg=typer.colors.YELLOW,
        )


@app.command()
def version() -> None:
    """
    Print the installed package version.

    This command implements version reporting as specified in the
    ChatGPT audit using importlib.metadata for accurate version
    detection from the installed package.

    The version is read from the package metadata, ensuring it
    matches the actual installed version rather than a hardcoded
    value that could become stale.
    """
    try:
        # Get version from installed package metadata
        # This ensures the version matches what's actually installed
        package_version = importlib.metadata.version("chrome_troubleshooter")
        typer.echo(package_version)
    except importlib.metadata.PackageNotFoundError:
        # Package not installed or metadata not available
        # This can happen during development or with broken installations
        typer.secho(
            "Version information not available (development installation?)",
            fg=typer.colors.YELLOW,
        )


# Entry point for console script
# This allows the module to be run directly: python -m chrome_troubleshooter.cli_audit
if __name__ == "__main__":
    app()
