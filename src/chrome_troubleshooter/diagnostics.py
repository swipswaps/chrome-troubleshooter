"""
Collect light-weight diagnostics (last minute of dmesg, last 50 Chrome journal lines).

This module implements the exact specification from the ChatGPT audit
for minimal, fast diagnostic data collection.

Key design decisions from the audit:
1. Lightweight collection only - no heavy system analysis
2. Recent data focus - last minute of dmesg, last 50 journal entries
3. Chrome-specific filtering for journal entries
4. Graceful handling of missing system tools
5. Error suppression for non-critical failures
6. Integration with session logging system
"""

from __future__ import annotations

import shutil
import subprocess

# SINGLE SOURCE OF TRUTH: Updated import after module deduplication
# Following ChatGPT audit suggestion U-C1 for module cleanup
from .logger import StructuredLogger as LogWriter


def collect_all(log: LogWriter) -> None:
    """
    Collect lightweight diagnostic information and log it.

    This function implements the exact diagnostic collection strategy
    from the ChatGPT audit:
    1. Recent kernel messages (dmesg) from last minute
    2. Recent Chrome-related journal entries (last 50)
    3. Graceful handling of missing tools
    4. Error suppression for non-critical failures

    Args:
        log: LogWriter instance for the current session

    The function checks for tool availability before attempting collection
    and suppresses errors to prevent diagnostic collection from failing
    the entire troubleshooting session.
    """

    # Collect recent kernel messages (dmesg)
    # Focus on last minute to capture recent Chrome-related kernel events
    if shutil.which("dmesg"):
        try:
            # dmesg arguments explained:
            # --since -1min: Only messages from last minute (recent events)
            # --time-format iso: ISO timestamp format for consistency
            dmesg_output = subprocess.check_output(
                ["dmesg", "--since", "-1min", "--time-format", "iso"],
                text=True,
                errors="ignore",  # Ignore encoding errors in kernel messages
            )
            # Log the output, stripping whitespace for clean formatting
            log.add("dmesg", dmesg_output.strip())
        except subprocess.CalledProcessError:
            # dmesg failed (permissions, missing, etc.)
            # Log the failure but don't crash the diagnostic collection
            log.add(
                "dmesg",
                "dmesg collection failed - insufficient permissions or tool missing",
            )
        except Exception as e:
            # Unexpected error during dmesg collection
            # Log the error but continue with other diagnostics
            log.add("dmesg", f"dmesg collection error: {e!s}")
    else:
        # dmesg tool not available on this system
        # This is common in containers or minimal distributions
        log.add("dmesg", "dmesg tool not available on this system")

    # Collect recent Chrome-related journal entries
    # Focus on Chrome process messages for targeted troubleshooting
    if shutil.which("journalctl"):
        try:
            # journalctl arguments explained:
            # -n 50: Last 50 entries (reasonable amount for analysis)
            # --no-pager: Disable pager for programmatic access
            # _COMM=chrome: Filter for Chrome process messages only
            journal_output = subprocess.check_output(
                ["journalctl", "-n", "50", "--no-pager", "_COMM=chrome"],
                text=True,
                errors="ignore",  # Ignore encoding errors in journal
            )
            # Log the output, stripping whitespace for clean formatting
            log.add("journal", journal_output.strip())
        except subprocess.CalledProcessError:
            # journalctl failed (permissions, systemd not available, etc.)
            # This is common in non-systemd systems or containers
            log.add(
                "journal",
                "journalctl collection failed - systemd not available or insufficient permissions",
            )
        except Exception as e:
            # Unexpected error during journal collection
            # Log the error but continue (don't fail entire diagnostic)
            log.add("journal", f"journalctl collection error: {e!s}")
    else:
        # journalctl tool not available on this system
        # This is expected on non-systemd systems (Alpine, older distributions)
        log.add("journal", "journalctl tool not available - non-systemd system")
