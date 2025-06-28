#!/usr/bin/env python3
"""
🔧 CHROME TROUBLESHOOTER - ENHANCED TYPER CLI
Modern CLI with Rich formatting and improved UX
"""

import sys
import os
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, List

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich import print as rprint

from .config import Config, load_config, save_config
from .logger import StructuredLogger
from .launcher import ChromeLauncher
from .diagnostics import DiagnosticsCollector

# Initialize Rich console and Typer app
console = Console()
app = typer.Typer(
    name="chrome-troubleshooter",
    help="🔧 Advanced Chrome crash diagnosis and auto-remediation tool",
    add_completion=False,
    rich_markup_mode="rich",
    no_args_is_help=True
)

# Global options
def version_callback(value: bool):
    if value:
        console.print("Chrome Troubleshooter v1.0.0")
        raise typer.Exit()

@app.callback()
def main(
    version: Optional[bool] = typer.Option(None, "--version", callback=version_callback, help="Show version"),
    config_file: Optional[Path] = typer.Option(None, "--config-file", help="Path to configuration file"),
    verbose: int = typer.Option(0, "-v", "--verbose", count=True, help="Increase verbosity (-v, -vv)")
):
    """🔧 Advanced Chrome crash diagnosis and auto-remediation tool"""
    pass

@app.command()
def launch(
    timeout: Optional[int] = typer.Option(None, "--timeout", help="Launch timeout in seconds"),
    max_attempts: Optional[int] = typer.Option(None, "--max-attempts", help="Maximum launch attempts"),
    extra_flags: Optional[List[str]] = typer.Option(None, "--extra-flags", help="Additional Chrome flags"),
    no_selinux_fix: bool = typer.Option(False, "--no-selinux-fix", help="Disable automatic SELinux fixes"),
    no_flatpak_fallback: bool = typer.Option(False, "--no-flatpak-fallback", help="Disable Flatpak fallback"),
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
        if extra_flags:
            config.extra_flags.extend(extra_flags)
        if no_selinux_fix:
            config.enable_selinux_fix = False
        if no_flatpak_fallback:
            config.enable_flatpak_fallback = False
            
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
        raise typer.Exit(1)

@app.command()
def diagnose(
    journal_lines: Optional[int] = typer.Option(None, "--journal-lines", help="Number of journal lines to collect"),
    output: Optional[Path] = typer.Option(None, "--output", help="Save diagnostics to file"),
    config_file: Optional[Path] = typer.Option(None, "--config-file", help="Path to configuration file"),
    verbose: int = typer.Option(0, "-v", "--verbose", count=True, help="Increase verbosity")
):
    """🔍 Run comprehensive diagnostics without launching Chrome"""
    
    try:
        # Load configuration
        config = load_config(config_file)
        
        # Override with command line arguments
        if journal_lines is not None:
            config.journal_lines = journal_lines
            
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
                display_diagnostics_table(diagnostics)
                
                # Save to file if requested
                if output:
                    save_diagnostics_to_file(diagnostics, output)
                    console.print(f"[green]✅ Diagnostics saved to: {output}[/green]")
                
                console.print(f"[blue]📁 Session logs: {session_dir}[/blue]")
                return 0
                
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️ Operation cancelled by user[/yellow]")
        raise typer.Exit(130)
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
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
            
        # Display status table
        display_status_table(config, check_deps)
        
        return 0
        
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise typer.Exit(1)

def display_diagnostics_table(diagnostics: dict):
    """Display diagnostics in a Rich table."""
    table = Table(title="🔍 System Diagnostics")
    table.add_column("Category", style="cyan", no_wrap=True)
    table.add_column("Status", style="magenta")
    table.add_column("Details", style="green")
    
    for category, data in diagnostics.items():
        if isinstance(data, dict):
            status = "✅ OK" if data.get("status") == "ok" else "⚠️ Issues"
            details = str(data.get("details", ""))
        else:
            status = "✅ OK"
            details = str(data)
        
        table.add_row(category.replace("_", " ").title(), status, details)
    
    console.print(table)

def display_status_table(config: Config, check_deps: bool):
    """Display system status in a Rich table."""
    table = Table(title="🔧 Chrome Troubleshooter Status")
    table.add_column("Component", style="cyan", no_wrap=True)
    table.add_column("Status", style="magenta")
    table.add_column("Value", style="green")
    
    # Configuration status
    table.add_row("Configuration", "✅ Loaded", f"Timeout: {config.launch_timeout}s")
    table.add_row("Max Attempts", "✅ Set", str(config.max_attempts))
    table.add_row("Log Level", "✅ Set", config.log_level)
    table.add_row("SELinux Fix", "✅ Enabled" if config.enable_selinux_fix else "⚠️ Disabled", "")
    table.add_row("Flatpak Fallback", "✅ Enabled" if config.enable_flatpak_fallback else "⚠️ Disabled", "")
    
    if check_deps:
        # Check dependencies
        deps = check_system_dependencies()
        for dep, status in deps.items():
            table.add_row(f"Dependency: {dep}", "✅ Available" if status else "❌ Missing", "")
    
    console.print(table)

def save_diagnostics_to_file(diagnostics: dict, output_path: Path):
    """Save diagnostics to JSON file."""
    with open(output_path, 'w') as f:
        json.dump(diagnostics, f, indent=2, default=str)

def check_system_dependencies() -> dict:
    """Check if required system dependencies are available."""
    deps = {
        "chrome": bool(shutil.which("google-chrome") or shutil.which("google-chrome-stable")),
        "journalctl": bool(shutil.which("journalctl")),
        "dmesg": bool(shutil.which("dmesg")),
        "flock": bool(shutil.which("flock")),
        "flatpak": bool(shutil.which("flatpak")),
    }
    return deps

def create_session_directory(config: Config) -> Path:
    """Create a session directory for logs."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir = config.base_dir / f"session_{timestamp}"
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir

def cli_main():
    """Entry point for the enhanced CLI."""
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
    cli_main()
