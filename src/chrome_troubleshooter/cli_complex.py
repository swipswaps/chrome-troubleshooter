#!/usr/bin/env python3
"""
🔧 CHROME TROUBLESHOOTER - COMMAND LINE INTERFACE
Professional CLI for Chrome crash diagnosis and auto-remediation
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from .config import Config, load_config, save_config
from .diagnostics import DiagnosticsCollector
from .launcher import ChromeLauncher
from .logger import StructuredLogger

# Initialize Rich console
console = Console()
app = typer.Typer(
    name="chrome-troubleshooter",
    help="🔧 Advanced Chrome crash diagnosis and auto-remediation tool",
    add_completion=False,
    rich_markup_mode="rich"
)


@app.command()
def launch(
    timeout: Optional[int] = typer.Option(None, "--timeout", help="Launch timeout in seconds"),
    max_attempts: Optional[int] = typer.Option(None, "--max-attempts", help="Maximum launch attempts"),
    extra_flags: Optional[list[str]] = typer.Option(None, "--extra-flags", help="Additional Chrome flags"),
    no_selinux_fix: bool = typer.Option(False, "--no-selinux-fix", help="Disable automatic SELinux fixes"),
    no_flatpak_fallback: bool = typer.Option(False, "--no-flatpak-fallback", help="Disable Flatpak fallback"),
    config_file: Optional[Path] = typer.Option(None, "--config-file", help="Path to configuration file"),
    verbose: int = typer.Option(0, "-v", "--verbose", count=True, help="Increase verbosity")
):
    """Launch Chrome with troubleshooting and progressive fallbacks."""
    return handle_launch_typer(timeout, max_attempts, extra_flags, no_selinux_fix, no_flatpak_fallback, config_file, verbose)


@app.command()
def diagnose(
    journal_lines: Optional[int] = typer.Option(None, "--journal-lines", help="Number of journal lines to collect"),
    output: Optional[Path] = typer.Option(None, "--output", help="Save diagnostics to file"),
    config_file: Optional[Path] = typer.Option(None, "--config-file", help="Path to configuration file"),
    verbose: int = typer.Option(0, "-v", "--verbose", count=True, help="Increase verbosity")
):
    """Run comprehensive diagnostics without launching Chrome."""
    return handle_diagnose_typer(journal_lines, output, config_file, verbose)


@app.command()
def status(
    check_deps: bool = typer.Option(False, "--check-deps", help="Check system dependencies"),
    config_file: Optional[Path] = typer.Option(None, "--config-file", help="Path to configuration file"),
    verbose: int = typer.Option(0, "-v", "--verbose", count=True, help="Increase verbosity")
):
    """Show system status and configuration."""
    return handle_status_typer(check_deps, config_file, verbose)


def handle_launch_typer(timeout, max_attempts, extra_flags, no_selinux_fix, no_flatpak_fallback, config_file, verbose) -> int:
    """Handle launch command with enhanced Rich output."""
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
        return 130
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        return 1

    parser.add_argument("--version", action="version", version="%(prog)s 1.0.0")

    parser.add_argument("--config-file", type=Path, help="Path to configuration file")

    parser.add_argument(
        "--verbose",
        "-v",
        action="count",
        default=0,
        help="Increase verbosity (use -vv for debug)",
    )

    # Create subparsers
    subparsers = parser.add_subparsers(
        dest="command", help="Available commands", metavar="COMMAND"
    )

    # Launch command
    launch_parser = subparsers.add_parser(
        "launch",
        help="Launch Chrome with troubleshooting",
        description="Launch Chrome with progressive fallbacks and diagnostics",
    )
    launch_parser.add_argument("--timeout", type=int, help="Launch timeout in seconds")
    launch_parser.add_argument(
        "--max-attempts", type=int, help="Maximum launch attempts"
    )
    launch_parser.add_argument(
        "--extra-flags", nargs="*", help="Additional Chrome flags"
    )
    launch_parser.add_argument(
        "--no-selinux-fix", action="store_true", help="Disable automatic SELinux fixes"
    )
    launch_parser.add_argument(
        "--no-flatpak-fallback", action="store_true", help="Disable Flatpak fallback"
    )

    # Diagnose command
    diagnose_parser = subparsers.add_parser(
        "diagnose",
        help="Run diagnostics without launching Chrome",
        description="Collect comprehensive system diagnostics",
    )
    diagnose_parser.add_argument(
        "--journal-lines", type=int, help="Number of journal lines to collect"
    )
    diagnose_parser.add_argument("--output", type=Path, help="Save diagnostics to file")

    # Status command
    status_parser = subparsers.add_parser(
        "status",
        help="Show system status and configuration",
        description="Display system information and troubleshooter status",
    )
    status_parser.add_argument(
        "--check-deps", action="store_true", help="Check system dependencies"
    )

    # Config command
    config_parser = subparsers.add_parser(
        "config",
        help="Configure troubleshooter settings",
        description="View or modify configuration settings",
    )
    config_parser.add_argument(
        "--show", action="store_true", help="Show current configuration"
    )
    config_parser.add_argument("--timeout", type=int, help="Set launch timeout")
    config_parser.add_argument("--max-attempts", type=int, help="Set maximum attempts")
    config_parser.add_argument(
        "--journal-lines", type=int, help="Set journal lines to collect"
    )
    config_parser.add_argument("--rotate-days", type=int, help="Set log rotation days")
    config_parser.add_argument(
        "--enable-colors", action="store_true", help="Enable colored output"
    )
    config_parser.add_argument(
        "--disable-colors", action="store_true", help="Disable colored output"
    )

    # Logs command
    logs_parser = subparsers.add_parser(
        "logs",
        help="View troubleshooter logs",
        description="View logs from troubleshooting sessions",
    )
    logs_parser.add_argument(
        "--latest", action="store_true", help="Show latest session logs"
    )
    logs_parser.add_argument(
        "--list", action="store_true", help="List available sessions"
    )
    logs_parser.add_argument("--session", type=str, help="Show specific session logs")
    logs_parser.add_argument(
        "--format", choices=["text", "json"], default="text", help="Output format"
    )

    # Clean command
    clean_parser = subparsers.add_parser(
        "clean",
        help="Clean old logs and temporary files",
        description="Remove old session data and temporary files",
    )
    clean_parser.add_argument(
        "--days", type=int, default=7, help="Remove sessions older than N days"
    )
    clean_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be removed without actually removing",
    )

    return parser


def handle_launch(args, config: Config) -> int:
    """Handle launch command"""
    # Override config with command line arguments
    if args.timeout is not None:
        config.launch_timeout = args.timeout
    if args.max_attempts is not None:
        config.max_attempts = args.max_attempts
    if args.extra_flags is not None:
        config.extra_flags.extend(args.extra_flags)
    if args.no_selinux_fix:
        config.enable_selinux_fix = False
    if args.no_flatpak_fallback:
        config.enable_flatpak_fallback = False

    # Check dependencies
    missing_deps = config.get_missing_dependencies()
    if missing_deps:
        print(f"❌ Missing critical dependencies: {', '.join(missing_deps)}")
        print("Please install missing dependencies and try again.")
        return 1

    # Create session directory
    session_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir = config.base_dir / f"session_{session_ts}"

    try:
        with StructuredLogger(
            session_dir, config.enable_colors, config.enable_sqlite, config.enable_json
        ) as logger:
            logger.info("cli", f"Chrome Troubleshooter v1.0.0 - Session: {session_ts}")

            with ChromeLauncher(config, logger) as launcher:
                success = launcher.run_troubleshooting_session()
                return 0 if success else 1

    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user")
        return 130
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1


def handle_diagnose(args, config: Config) -> int:
    """Handle diagnose command"""
    if args.journal_lines is not None:
        config.journal_lines = args.journal_lines

    # Create session directory
    session_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir = config.base_dir / f"diagnose_{session_ts}"

    try:
        with StructuredLogger(
            session_dir, config.enable_colors, config.enable_sqlite, config.enable_json
        ) as logger:
            logger.info("cli", "Running comprehensive diagnostics...")

            diagnostics = DiagnosticsCollector(logger)
            results = diagnostics.full_diagnostic_sweep(config.journal_lines)

            # Save results if requested
            if args.output:
                import json

                with open(args.output, "w") as f:
                    json.dump(results, f, indent=2, default=str)
                logger.success("cli", f"Diagnostics saved to: {args.output}")

            # Print summary
            print("\n🔍 DIAGNOSTIC SUMMARY:")
            print(f"System Info: {len(results.get('system_info', {}))}")
            print(f"GPU Info: {len(results.get('gpu_info', {}))}")
            print(f"Chrome Debug Logs: {len(results.get('chrome_debug_logs', []))}")
            print(f"Crashpad Dumps: {len(results.get('crashpad_dumps', []))}")
            print(
                f"Journal Entries: {len(results.get('journal_logs', {}).get('user_journal', []))}"
            )
            print(f"dmesg Entries: {len(results.get('dmesg_delta', []))}")
            print(f"Coredumps: {len(results.get('coredump_info', []))}")

            # Show crash analysis
            crash_analysis = results.get("crash_analysis", {})
            if crash_analysis.get("patterns_found"):
                print("\n⚠️ DETECTED ISSUES:")
                for pattern in crash_analysis["patterns_found"]:
                    print(f"  • {pattern}")
            else:
                print("\n✅ No obvious crash patterns detected")

            return 0

    except Exception as e:
        print(f"❌ Diagnostic error: {e}")
        return 1


def handle_status(args, config: Config) -> int:
    """Handle status command"""
    print("🔧 Chrome Troubleshooter Status")
    print("=" * 50)

    if args.check_deps:
        deps = config.validate_dependencies()
        print("\n📋 SYSTEM DEPENDENCIES:")
        for dep, available in deps.items():
            status = "✅" if available else "❌"
            print(f"  {status} {dep}")

        missing = [k for k, v in deps.items() if not v]
        if missing:
            print(f"\n⚠️ Missing: {', '.join(missing)}")

    config.print_status()

    # Show recent sessions
    if config.base_dir.exists():
        sessions = list(config.base_dir.glob("session_*"))
        sessions.sort(key=lambda x: x.stat().st_mtime, reverse=True)

        print(f"\n📁 RECENT SESSIONS ({len(sessions)} total):")
        for session in sessions[:5]:  # Show last 5
            mtime = datetime.fromtimestamp(session.stat().st_mtime)
            print(f"  • {session.name} - {mtime.strftime('%Y-%m-%d %H:%M:%S')}")

    return 0


def handle_config(args, config: Config) -> int:
    """Handle config command"""
    config_path = (
        args.config_file
        or Path.home() / ".config" / "chrome-troubleshooter" / "config.json"
    )

    if args.show:
        config.print_status()
        return 0

    # Update configuration
    changed = False

    if args.timeout is not None:
        config.launch_timeout = args.timeout
        changed = True
    if args.max_attempts is not None:
        config.max_attempts = args.max_attempts
        changed = True
    if args.journal_lines is not None:
        config.journal_lines = args.journal_lines
        changed = True
    if args.rotate_days is not None:
        config.rotate_days = args.rotate_days
        changed = True
    if args.enable_colors:
        config.enable_colors = True
        changed = True
    if args.disable_colors:
        config.enable_colors = False
        changed = True

    if changed:
        save_config(config, config_path)
        print(f"✅ Configuration saved to: {config_path}")
    else:
        print(
            "No configuration changes specified. Use --show to view current settings."
        )

    return 0


def handle_logs(args, config: Config) -> int:
    """Handle logs command"""
    if not config.base_dir.exists():
        print("No log directory found.")
        return 1

    sessions = list(config.base_dir.glob("session_*"))
    sessions.sort(key=lambda x: x.stat().st_mtime, reverse=True)

    if args.list:
        print("📁 Available Sessions:")
        for session in sessions:
            mtime = datetime.fromtimestamp(session.stat().st_mtime)
            size = sum(f.stat().st_size for f in session.rglob("*") if f.is_file())
            print(
                f"  • {session.name} - {mtime.strftime('%Y-%m-%d %H:%M:%S')} ({size:,} bytes)"
            )
        return 0

    # Determine which session to show
    target_session = None
    if args.session:
        target_session = config.base_dir / f"session_{args.session}"
        if not target_session.exists():
            print(f"Session not found: {args.session}")
            return 1
    elif args.latest and sessions:
        target_session = sessions[0]
    else:
        print("No session specified. Use --latest or --session <name>")
        return 1

    if not target_session:
        print("No sessions available.")
        return 1

    # Display logs
    if args.format == "json":
        json_file = target_session / "logs.jsonl"
        if json_file.exists():
            with open(json_file) as f:
                print(f.read())
        else:
            print("No JSON logs found.")
    else:
        log_file = target_session / "launcher.log"
        if log_file.exists():
            with open(log_file) as f:
                print(f.read())
        else:
            print("No text logs found.")

    return 0


def handle_clean(args, config: Config) -> int:
    """Handle clean command"""
    if not config.base_dir.exists():
        print("No log directory found.")
        return 0

    from datetime import timedelta

    cutoff = datetime.now() - timedelta(days=args.days)

    sessions = []
    for session_dir in config.base_dir.iterdir():
        if session_dir.is_dir() and session_dir.name.startswith(
            ("session_", "diagnose_")
        ):
            mtime = datetime.fromtimestamp(session_dir.stat().st_mtime)
            if mtime < cutoff:
                sessions.append((session_dir, mtime))

    if not sessions:
        print(f"No sessions older than {args.days} days found.")
        return 0

    total_size = 0
    for session_dir, mtime in sessions:
        size = sum(f.stat().st_size for f in session_dir.rglob("*") if f.is_file())
        total_size += size

        if args.dry_run:
            print(
                f"Would remove: {session_dir.name} ({mtime.strftime('%Y-%m-%d %H:%M:%S')}, {size:,} bytes)"
            )
        else:
            import shutil

            shutil.rmtree(session_dir)
            print(
                f"Removed: {session_dir.name} ({mtime.strftime('%Y-%m-%d %H:%M:%S')}, {size:,} bytes)"
            )

    action = "Would remove" if args.dry_run else "Removed"
    print(f"\n{action} {len(sessions)} sessions, {total_size:,} bytes total")

    return 0


def create_parser():
    """Create the main argument parser"""
    parser = argparse.ArgumentParser(
        prog="chrome-troubleshooter",
        description="🔧 Advanced Chrome crash diagnosis and auto-remediation tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Global options
    parser.add_argument(
        "--config-file",
        type=Path,
        help="Path to configuration file"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="count",
        default=0,
        help="Increase verbosity (-v, -vv)"
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Launch command
    launch_parser = subparsers.add_parser("launch", help="Launch Chrome with troubleshooting")
    launch_parser.add_argument("--timeout", type=int, help="Launch timeout in seconds")
    launch_parser.add_argument("--max-attempts", type=int, help="Maximum launch attempts")

    # Status command
    status_parser = subparsers.add_parser("status", help="Show system status")
    status_parser.add_argument("--check-deps", action="store_true", help="Check dependencies")

    # Diagnose command
    diag_parser = subparsers.add_parser("diagnose", help="Run diagnostics")
    diag_parser.add_argument("--output", type=Path, help="Save diagnostics to file")

    return parser


def main() -> int:
    """Main CLI entry point"""

    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Load configuration
    try:
        config = load_config(args.config_file)
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return 1

    # Set log level based on verbosity
    if args.verbose >= 2:
        config.log_level = "DEBUG"
    elif args.verbose >= 1:
        config.log_level = "INFO"

    # Route to appropriate handler
    try:
        if args.command == "launch":
            return handle_launch(args, config)
        elif args.command == "diagnose":
            return handle_diagnose(args, config)
        elif args.command == "status":
            return handle_status(args, config)
        elif args.command == "config":
            return handle_config(args, config)
        elif args.command == "logs":
            return handle_logs(args, config)
        elif args.command == "clean":
            return handle_clean(args, config)
        else:
            print(f"❌ Unknown command: {args.command}")
            return 1
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user")
        return 130
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        if args.verbose >= 2:
            import traceback

            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
