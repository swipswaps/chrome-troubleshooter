"""
Stage-0 safe launcher (no GPU flags yet) with
single-instance lock (fcntl), timeout, and rich feedback.

This module implements the exact specification from the ChatGPT audit
for a minimal, robust Chrome launcher with proper process management.

Key design decisions from the audit:
1. Single-instance lock using fcntl (POSIX-only, documented limitation)
2. Safe Chrome flags only (no GPU/sandbox modifications yet)
3. Timeout-based success detection (Chrome stays alive)
4. Rich console feedback for user experience
5. Session-based logging for forensic analysis
6. Proper cleanup of lock file descriptor
"""

from __future__ import annotations

import atexit
import fcntl
import subprocess
import sys
import time

from rich.console import Console

# SINGLE SOURCE OF TRUTH: Updated imports after module deduplication
# Following ChatGPT audit suggestion U-C1 for module cleanup
from .constants import SESSION_FMT, get_cache_dir
from .logger import StructuredLogger as LogWriter
from .utils import which_chrome

# Lock file location in /tmp for system-wide single instance
# Using /tmp ensures it's cleaned up on reboot
# CRITICAL FIX: Global lock FD to prevent garbage collection
# Following ChatGPT audit - "lock lives as long as FD lives"
_LOCK.touch(exist_ok=True)
LOCK_FD = _LOCK.open("w")                           # GLOBAL
fcntl.flock(LOCK_FD, fcntl.LOCK_EX | fcntl.LOCK_NB)
atexit.register(LOCK_FD.close)                      # deterministic cleanup
# --enable-logging=stderr: Send Chrome logs to stderr for capture
# --v=1: Verbose logging level 1 (basic debugging info)
SAFE_FLAGS = ["--enable-logging=stderr", "--v=1"]

# Global Rich console for consistent formatting
console = Console()


def _acquire_lock():
    """
    Acquire single-instance lock using fcntl.

    This function implements the exact locking strategy from the ChatGPT audit:
    1. Create lock file if it doesn't exist
    2. Open file for read/write access
    3. Attempt non-blocking exclusive lock
    4. Exit with error code 1 if another instance is running

    Returns:
        file object: Open file descriptor for the lock file

    Exits:
        System exit code 1 if another instance is already running

    The lock is automatically released when the file descriptor is closed
    or when the process exits.
    """
    # Create lock file if it doesn't exist
    # exist_ok=True prevents race condition if multiple processes start simultaneously
    _LOCK.touch(exist_ok=True)

    # Open lock file for read/write access
    # This file descriptor must remain open to maintain the lock
    lock_fd = _LOCK.open("r+")

    try:
        # Attempt to acquire exclusive, non-blocking lock
        # LOCK_EX: Exclusive lock (only one process can hold it)
        # LOCK_NB: Non-blocking (fail immediately if lock unavailable)
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return lock_fd
    except BlockingIOError:
        # Another instance is already running
        # Display clear error message and exit with standard error code
        console.print(
            "[bold red]Another instance is already running. Abort.[/bold red]"
        )
        sys.exit(1)


def safe_launch(timeout: int = 15) -> None:
    """
    Launch Chrome with safe flags and session logging.

    This function implements the exact launch strategy from the ChatGPT audit:
    1. Acquire single-instance lock
    2. Find Chrome executable (with user override support)
    3. Create session directory with timestamp
    4. Launch Chrome with safe flags
    5. Monitor process for timeout period
    6. Log all activity for forensic analysis

    Args:
        timeout: Seconds to wait before considering Chrome stable

    Exits:
        System exit code 1 if lock acquisition fails
        System exit code 2 if Chrome executable not found

    The function uses timeout-based success detection: if Chrome runs
    for the specified timeout without exiting, it's considered successful.
    """
    # Acquire single-instance lock first
    # This prevents multiple Chrome troubleshooter instances
    lock_fd = _acquire_lock()

    # Find Chrome executable with user override support
    chrome_path = which_chrome()
    if not chrome_path:
        # Chrome not found in PATH or CHROME_PATH environment variable
        # Display helpful error message with solution
        console.print(
            "[bold red]Chrome executable not found. Set $CHROME_PATH[/bold red]"
        )
        sys.exit(2)

    # Get cache directory and ensure it exists (moved from import-time to runtime)
    # CRITICAL FIX: Prevents import hangs from filesystem operations
    cache_dir = get_cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Create session directory with ISO timestamp
    # This provides unique directory for each launch attempt
    session_dir = cache_dir / time.strftime(SESSION_FMT)
    session_dir.mkdir(parents=True, exist_ok=True)

    # Initialize session logger for forensic analysis
    log = LogWriter(session_dir)

    # Build Chrome command with safe flags
    chrome_command = [chrome_path, *SAFE_FLAGS]
    log.add("launcher", " ".join(chrome_command))

    # Launch Chrome process with output capture
    # stdout and stderr are captured for analysis
    # text=True ensures string handling instead of bytes
    with subprocess.Popen(
        chrome_command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,  # Merge stderr into stdout
        text=True,
    ) as chrome_process:

        try:
            # Wait for Chrome to exit or timeout
            # If Chrome exits quickly, it likely failed to start
            # If timeout expires, Chrome is considered stable
            chrome_process.wait(timeout=timeout)

            # Chrome exited before timeout - likely an error
            log.add("exit", f"Chrome quit early, code={chrome_process.returncode}")

            # Capture and save Chrome's output for analysis
            stdout_output, _ = chrome_process.communicate()
            chrome_log_file = session_dir / "chrome_stdout.log"
            chrome_log_file.write_text(stdout_output or "")

        except subprocess.TimeoutExpired:
            # Chrome survived the timeout period - success!
            # This is the expected case for successful Chrome launch
            log.add("launcher", "Chrome alive after timeout – success")
            console.print("[green]✓ Chrome appears stable[/green]")

    # Clean up lock file descriptor
    # This releases the single-instance lock
    lock_fd.close()
