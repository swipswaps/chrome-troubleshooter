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

    # Collect recent kernel messages with graceful permission handling
    # CRITICAL ENHANCEMENT: Multiple fallback strategies for permission issues
    # Following production script requirements for robust error handling
    _collect_dmesg_with_fallbacks(log)

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


def _collect_dmesg_with_fallbacks(log: LogWriter) -> None:
    """
    Collect dmesg with multiple fallback strategies for permission issues.

    CRITICAL FIX: Implements graceful degradation for permission errors.
    Following production script requirements for robust error handling.

    Strategies:
    1. Try dmesg without sudo (works if user has permissions)
    2. Try with sudo -n (non-interactive sudo)
    3. Try reading from /var/log/dmesg
    4. Provide helpful error message with solution
    """
    if not shutil.which("dmesg"):
        log.add("dmesg", "dmesg tool not available on this system")
        return

    # Strategy 1: Try dmesg without sudo (works if user has permissions)
    try:
        dmesg_output = subprocess.check_output(
            ["dmesg", "--since", "-1min", "--time-format", "iso"],
            text=True,
            errors="ignore",
            timeout=10
        )
        log.add("dmesg", dmesg_output.strip() or "No recent kernel messages")
        return
    except subprocess.CalledProcessError as e:
        if e.returncode == 1:  # Permission denied
            pass  # Try next strategy
        else:
            log.add("dmesg", f"dmesg failed with exit code {e.returncode}")
            return
    except subprocess.TimeoutExpired:
        log.add("dmesg", "dmesg command timed out")
        return
    except Exception as e:
        log.add("dmesg", f"dmesg collection error: {e!s}")
        return

    # Strategy 2: Try with sudo if available (non-interactive)
    if shutil.which("sudo"):
        try:
            dmesg_output = subprocess.check_output(
                ["sudo", "-n", "dmesg", "--since", "-1min", "--time-format", "iso"],
                text=True,
                errors="ignore",
                timeout=10
            )
            log.add("dmesg", f"[via sudo] {dmesg_output.strip()}")
            return
        except subprocess.CalledProcessError:
            pass  # Try next strategy
        except subprocess.TimeoutExpired:
            log.add("dmesg", "sudo dmesg command timed out")
            return
        except Exception:
            pass  # Try next strategy

    # Strategy 3: Try reading from /var/log/dmesg if available
    try:
        from pathlib import Path
        dmesg_file = Path("/var/log/dmesg")
        if dmesg_file.exists() and dmesg_file.is_file():
            content = dmesg_file.read_text(errors="ignore")[-2000:]  # Last 2KB
            log.add("dmesg", f"[from /var/log/dmesg] {content}")
            return
    except Exception:
        pass

    # All strategies failed - provide helpful error message
    log.add("dmesg", """dmesg unavailable: insufficient permissions

SOLUTION: Add your user to the 'adm' group:
  sudo usermod -a -G adm $USER
  # Then logout and login again

ALTERNATIVE: Run with sudo:
  sudo chrome-troubleshooter diag""")


def _check_system_access() -> dict:
    """
    Check what system information we can access.

    Returns diagnostic information about available tools and permissions.
    This helps users understand what functionality is available.
    """
    import grp
    import os

    access_info = {
        'dmesg_available': shutil.which('dmesg') is not None,
        'journalctl_available': shutil.which('journalctl') is not None,
        'sudo_available': shutil.which('sudo') is not None,
        'user_groups': [],
        'can_read_var_log': False,
    }

    # Get user groups for permission analysis
    try:
        access_info['user_groups'] = [grp.getgrgid(gid).gr_name for gid in os.getgroups()]
    except Exception:
        pass

    # Check if we can read /var/log
    try:
        from pathlib import Path
        var_log = Path("/var/log")
        access_info['can_read_var_log'] = var_log.exists() and os.access(var_log, os.R_OK)
    except Exception:
        pass

    return access_info
