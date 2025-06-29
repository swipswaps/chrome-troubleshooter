"""
Utility helpers that must stay std-lib–only to keep wheels pure-python.

This module implements the exact specification from the ChatGPT audit.
All functions use only standard library to ensure the package remains
pure Python without native dependencies.

Key design decisions from the audit:
1. Standard library only - no external dependencies
2. Chrome detection with environment variable override
3. Enhanced subprocess error reporting with stderr capture
4. Textwrap for clean error formatting
5. Type hints for modern Python practices
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import textwrap


def which_chrome() -> str | None:
    """
    Return a Chrome/Chromium executable path or None.

    This function implements the exact search strategy specified in the
    ChatGPT audit:
    1. Check CHROME_PATH environment variable first (user override)
    2. Search standard Chrome binary names in PATH
    3. Return first found executable or None

    The environment variable override allows users to specify custom
    Chrome installations without modifying the code.

    Returns:
        str: Full path to Chrome executable if found
        None: If no Chrome executable is found

    Example:
        # With environment variable
        export CHROME_PATH=/opt/custom/chrome
        chrome_path = which_chrome()  # Returns /opt/custom/chrome

        # Standard PATH search
        chrome_path = which_chrome()  # Returns /usr/bin/google-chrome
    """
    # Priority 1: Check user-specified environment variable
    # This allows users to override detection for custom installations
    env_path = os.getenv("CHROME_PATH")
    if env_path and shutil.which(env_path):
        return env_path

    # Priority 2: Search standard Chrome binary names in PATH
    # Order matters: prefer stable over beta/dev versions
    # Include both Google Chrome and Chromium variants
    chrome_binaries = [
        "google-chrome",  # Most common on Ubuntu/Debian
        "google-chrome-stable",  # Explicit stable channel
        "chromium",  # Open source variant
    ]

    for binary_name in chrome_binaries:
        found_path = shutil.which(binary_name)
        if found_path:
            return found_path

    # No Chrome executable found in PATH or environment
    return None


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    """
    subprocess.run wrapper that prints stderr on failure.

    This function implements enhanced error reporting as specified in the
    ChatGPT audit. When a subprocess fails, it formats and displays the
    error information in a user-friendly way.

    Key features:
    1. Automatic stderr capture and display on failure
    2. Clean formatting with textwrap for readability
    3. Preserves original exception for proper error handling
    4. Passes through all subprocess.run arguments

    Args:
        cmd: Command and arguments as list of strings
        **kwargs: Additional arguments passed to subprocess.run

    Returns:
        subprocess.CompletedProcess: Result of the subprocess execution

    Raises:
        subprocess.CalledProcessError: If command fails (check=True)

    Example:
        # Successful command
        result = run(["echo", "hello"])
        print(result.stdout)  # "hello\n"

        # Failed command with enhanced error reporting
        try:
            run(["false"], check=True)
        except subprocess.CalledProcessError:
            # Error details automatically printed to stderr
            pass
    """
    try:
        # Execute subprocess with enhanced defaults
        # check=True: Raise exception on non-zero exit
        # text=True: Handle strings instead of bytes
        # capture_output=True: Capture stdout/stderr for analysis
        return subprocess.run(cmd, check=True, text=True, capture_output=True, **kwargs)
    except subprocess.CalledProcessError as exc:
        # Format and display detailed error information
        # Using textwrap.dedent for clean multi-line formatting
        error_report = textwrap.dedent(
            f"""
        ── subprocess failed ──
        CMD : {' '.join(exc.cmd)}
        CODE: {exc.returncode}
        ---- stderr ----
        {exc.stderr}
        -----------------
        """
        )

        # Write to stderr for proper error stream handling
        # This ensures error output doesn't interfere with stdout
        sys.stderr.write(error_report)

        # Re-raise the original exception to preserve error handling
        # Calling code can still catch and handle the exception appropriately
        raise
