"""
Global paths and format strings, centralised to avoid magic constants.

This module implements the exact specification from the ChatGPT audit for
clean, minimal constants management. Every constant is documented with
its purpose and usage pattern.

Design principles from the audit:
1. Minimal surface area - only essential constants
2. Immediate directory creation to prevent race conditions
3. Clear naming that matches usage patterns
4. No complex data structures - simple values only
5. Pathlib for modern filesystem operations
"""

from pathlib import Path

# Application name used consistently across all modules
# This drives directory naming, lock files, and logging prefixes
# Must match the package name in pyproject.toml for consistency
APP_NAME = "chrome-troubleshooter"

# Cache directory following XDG Base Directory Specification
# All session logs, temporary files, and diagnostic data stored here
# Created immediately to prevent FileNotFoundError during concurrent access
CACHE_DIR = Path.home() / ".cache" / APP_NAME

# Session directory naming format using ISO-style timestamps
# Format: session_YYYY-MM-DD_HH-MM-SS
# Ensures lexicographic sorting matches chronological order
# Includes seconds for uniqueness even with rapid session creation
# Used by launcher.py and logger.py for consistent session management
SESSION_FMT = "session_%Y-%m-%d_%H-%M-%S"

# Create cache directory structure immediately upon import
# This prevents race conditions when multiple processes start simultaneously
# Using exist_ok=True makes this operation idempotent and safe
# Parent directories created automatically for robustness
CACHE_DIR.mkdir(parents=True, exist_ok=True)
