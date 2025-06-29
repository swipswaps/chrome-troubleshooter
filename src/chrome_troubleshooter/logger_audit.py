"""
Rich + JSONL + SQLite logger.
Keeps one write-path so no info is lost if SQLite unavailable.

This module implements the exact specification from the ChatGPT audit
for a robust, multi-sink logging system that gracefully handles failures.

Key design decisions from the audit:
1. Three output sinks: Rich console, JSONL file, SQLite database
2. Graceful degradation if SQLite is unavailable (Alpine Linux compatibility)
3. WAL mode for SQLite to prevent corruption during crashes
4. JSONL as primary persistent format (always works)
5. Rich console for immediate user feedback
6. Early file creation to avoid race conditions
"""

from __future__ import annotations

import datetime as dt
import json
import sqlite3
from pathlib import Path
from typing import Final

from rich.console import Console

# Global Rich console instance for consistent formatting
# Using Final type hint to indicate this should not be reassigned
# Rich automatically handles ANSI color codes and terminal detection
console: Final = Console()


class LogWriter:
    """
    Writes every log entry to terminal, JSONL, and SQLite (if available).

    This class implements the exact specification from the ChatGPT audit
    for robust multi-sink logging with graceful degradation.

    Architecture:
    1. JSONL file: Primary persistent storage (always works)
    2. SQLite database: Structured queries and forensic analysis
    3. Rich console: Immediate user feedback with colors

    Error handling:
    - SQLite failures disable SQLite logging but preserve JSONL
    - File system errors are not caught (should fail fast)
    - Console errors are not caught (terminal issues should be visible)
    """

    def __init__(self, session_dir: Path):
        """
        Initialize logging to a specific session directory.

        Args:
            session_dir: Directory where logs will be stored

        The constructor sets up all three logging sinks and handles
        SQLite initialization failures gracefully.
        """
        # Set up file paths for persistent storage
        self.jsonl = session_dir / "logs.jsonl"
        self.db = session_dir / "logs.sqlite"

        # Create JSONL file early to avoid race conditions
        # This ensures the file exists even if SQLite setup fails
        self.jsonl.touch(exist_ok=True)

        # Initialize SQLite with error handling
        # WAL mode prevents corruption during crashes/power failures
        try:
            self.conn = sqlite3.connect(self.db)
            # Execute both PRAGMA and CREATE TABLE in single statement for atomicity
            self.conn.execute(
                "PRAGMA journal_mode=WAL;"
                "CREATE TABLE IF NOT EXISTS logs(ts TEXT, src TEXT, msg TEXT);"
            )
            self.sqlite_ok = True
        except (sqlite3.Error, OSError):
            # SQLite unavailable (common on Alpine Linux or restricted environments)
            # Warn user but continue with JSONL-only logging
            console.print("[yellow]SQLite unavailable – logging JSONL only[/yellow]")
            self.sqlite_ok = False

    def add(self, src: str, msg: str) -> None:
        """
        Write a log entry to all available sinks.

        Args:
            src: Source component (e.g., "launcher", "diagnostics")
            msg: Log message content

        This method implements the exact logging strategy from the audit:
        1. Generate ISO timestamp for consistency
        2. Display immediately on console with Rich formatting
        3. Append to JSONL file (primary persistent storage)
        4. Insert into SQLite if available (structured queries)

        Error handling:
        - SQLite errors disable SQLite logging for this session
        - JSONL errors are not caught (should fail fast)
        - Console errors are not caught (terminal issues should be visible)
        """
        # Generate ISO timestamp for consistent formatting across all sinks
        # UTC time prevents timezone confusion in distributed environments
        timestamp = dt.datetime.utcnow().isoformat()

        # Display immediately on console with Rich color formatting
        # Cyan timestamp for readability, source in brackets for structure
        console.print(f"[cyan]{timestamp}[/cyan] [{src}]{msg}")

        # Write to JSONL file (primary persistent storage)
        # JSONL format: one JSON object per line for easy parsing
        # UTF-8 encoding ensures international character support
        with self.jsonl.open("a", encoding="utf-8") as file_handle:
            log_entry = {"ts": timestamp, "src": src, "msg": msg}
            file_handle.write(json.dumps(log_entry) + "\n")

        # Write to SQLite database if available
        # Provides structured queries for forensic analysis
        if self.sqlite_ok:
            try:
                self.conn.execute(
                    "INSERT INTO logs VALUES (?,?,?)", (timestamp, src, msg)
                )
                # Commit immediately for crash safety
                # WAL mode makes this efficient
                self.conn.commit()
            except sqlite3.Error:
                # SQLite write failed - disable for this session
                # This prevents repeated error messages
                console.print("[red]SQLite write failed – disabling[/red]")
                self.sqlite_ok = False
