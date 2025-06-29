#!/usr/bin/env python3
"""
🔧 CHROME TROUBLESHOOTER - SIMPLIFIED CLI
Clean, working CLI based on ChatGPT audit suggestions
"""

import importlib.metadata
import sys
import time
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from .config import Config, load_config
from .diagnostics import DiagnosticsCollector
from .launcher import ChromeLauncher
from .logger import StructuredLogger

# Initialize Rich console and Typer app
console = Console()
app = typer.Typer(
    name="chrome-troubleshooter",
    help="🔧 Advanced Chrome crash diagnosis and auto-remediation tool",
    add_completion=False,
    rich_markup_mode="rich",
    no_args_is_help=True
)

def create_session_directory(config: Config) -> Path:
    """Create a session directory for logs."""
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    session_dir = config.base_dir / f"session_{timestamp}"
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir

@app.command()
def launch(
    timeout: Optional[int] = typer.Option(None, "--timeout", help="Launch timeout in seconds"),
    max_attempts: Optional[int] = typer.Option(None, "--max-attempts", help="Maximum launch attempts"),
    config_file: Optional[Path] = typer.Option(None, "--config-file", help="Path to configuration file"),
    verbose: int = typer.Option(0, "-v", "--verbose", count=True, help="Increase verbosity")
):
    """🚀 Launch Chrome with troubleshooting and progressive fallbacks"""

    try:
        # Load configuration
        config = load_config(config_file)

        # Override with command line arguments
        if timeout is not None:
            config.launch_timeout = timeout
        if max_attempts is not None:
            config.max_attempts = max_attempts

        # Set verbosity
        if verbose >= 2:
            config.log_level = "DEBUG"
        elif verbose >= 1:
            config.log_level = "INFO"

        # Create session directory
        session_dir = create_session_directory(config)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Initializing Chrome troubleshooter...", total=None)

            # Initialize logger
            with StructuredLogger(session_dir, config) as logger:
                progress.update(task, description="Starting Chrome launcher...")

                # Initialize launcher
                launcher = ChromeLauncher(config, logger)

                progress.update(task, description="Launching Chrome with troubleshooting...")

                # Launch Chrome
                success = launcher.launch()

                if success:
                    progress.update(task, description="✅ Chrome launched successfully!")
                    console.print(Panel.fit(
                        "[green]✅ Chrome launched successfully![/green]\n"
                        f"Session logs: {session_dir}",
                        title="Success",
                        border_style="green"
                    ))
                    return 0
                else:
                    progress.update(task, description="❌ Chrome launch failed")
                    console.print(Panel.fit(
                        "[red]❌ Chrome launch failed after all attempts[/red]\n"
                        f"Check logs: {session_dir}",
                        title="Failure",
                        border_style="red"
                    ))
                    return 1

    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️ Operation cancelled by user[/yellow]")
        raise typer.Exit(130)
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        if verbose >= 2:
            import traceback
            console.print(traceback.format_exc())
        raise typer.Exit(1)

@app.command()
def diagnose(
    output: Optional[Path] = typer.Option(None, "--output", help="Save diagnostics to file"),
    config_file: Optional[Path] = typer.Option(None, "--config-file", help="Path to configuration file"),
    verbose: int = typer.Option(0, "-v", "--verbose", count=True, help="Increase verbosity")
):
    """🔍 Run comprehensive diagnostics without launching Chrome"""

    try:
        # Load configuration
        config = load_config(config_file)

        # Set verbosity
        if verbose >= 2:
            config.log_level = "DEBUG"
        elif verbose >= 1:
            config.log_level = "INFO"

        # Create session directory
        session_dir = create_session_directory(config)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Running diagnostics...", total=None)

            # Initialize logger
            with StructuredLogger(session_dir, config) as logger:
                progress.update(task, description="Collecting system information...")

                # Initialize diagnostics collector
                collector = DiagnosticsCollector(config, logger)

                progress.update(task, description="Analyzing system environment...")

                # Collect diagnostics
                diagnostics = collector.collect_all()

                progress.update(task, description="Generating report...")

                # Display results
                console.print("🔍 Diagnostics completed!")
                console.print(f"Results: {len(diagnostics)} categories analyzed")

                # Save to file if requested
                if output:
                    import json
                    with open(output, 'w') as f:
                        json.dump(diagnostics, f, indent=2, default=str)
                    console.print(f"[green]✅ Diagnostics saved to: {output}[/green]")

                console.print(f"[blue]📁 Session logs: {session_dir}[/blue]")
                return 0

    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️ Operation cancelled by user[/yellow]")
        raise typer.Exit(130)
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        if verbose >= 2:
            import traceback
            console.print(traceback.format_exc())
        raise typer.Exit(1)

@app.command()
def status(
    check_deps: bool = typer.Option(False, "--check-deps", help="Check system dependencies"),
    config_file: Optional[Path] = typer.Option(None, "--config-file", help="Path to configuration file"),
    verbose: int = typer.Option(0, "-v", "--verbose", count=True, help="Increase verbosity")
):
    """📊 Show system status and configuration"""

    try:
        # Load configuration
        config = load_config(config_file)

        # Set verbosity
        if verbose >= 2:
            config.log_level = "DEBUG"
        elif verbose >= 1:
            config.log_level = "INFO"

        # Display basic status
        console.print("🔧 Chrome Troubleshooter Status")
        console.print("Configuration loaded: ✅")
        console.print(f"Launch timeout: {config.launch_timeout}s")
        console.print(f"Max attempts: {config.max_attempts}")
        console.print(f"Log level: {config.log_level}")

        if check_deps:
            import shutil
            console.print("\n📋 Dependencies:")
            deps = {
                "chrome": bool(shutil.which("google-chrome") or shutil.which("google-chrome-stable")),
                "journalctl": bool(shutil.which("journalctl")),
                "dmesg": bool(shutil.which("dmesg")),
            }
            for dep, available in deps.items():
                status = "✅ Available" if available else "❌ Missing"
                console.print(f"  {dep}: {status}")

        return 0

    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        if verbose >= 2:
            import traceback
            console.print(traceback.format_exc())
        raise typer.Exit(1)

@app.command()
def version():
    """📋 Show version information"""
    try:
        version = importlib.metadata.version("chrome_troubleshooter")
        console.print(f"Chrome Troubleshooter v{version}")
    except importlib.metadata.PackageNotFoundError:
        console.print("Chrome Troubleshooter (development version)")

def main():
    """Entry point for the simplified CLI."""
    try:
        # Handle lock file to prevent multiple instances
        lock_file = Path("/tmp/.chrome_troubleshooter.lock")
        if lock_file.exists():
            console.print("[red]❌ Another instance is already running[/red]")
            sys.exit(1)

        try:
            lock_file.touch()
            app()
        finally:
            # Clean up lock file
            if lock_file.exists():
                lock_file.unlink()

    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️ Operation cancelled by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        sys.exit(1)

if __name__ == "__main__":
    main()
