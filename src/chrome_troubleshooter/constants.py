#!/usr/bin/env python3
"""
🔧 CHROME TROUBLESHOOTER - CONSTANTS
Application constants and configuration defaults
"""

from pathlib import Path

# Application metadata
APP_NAME = "chrome-troubleshooter"
APP_VERSION = "1.0.0-beta"

# Directory paths
CACHE_DIR = Path.home() / ".cache" / APP_NAME
CONFIG_DIR = Path.home() / ".config" / APP_NAME
LOG_DIR = CACHE_DIR / "logs"

# Ensure directories exist
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Session naming (ISO format for better sorting)
SESSION_FMT = "session_%Y-%m-%d_%H-%M-%S"

# Lock file location
LOCK_FILE = "/tmp/.chrome_troubleshooter.lock"

# Chrome binary names to search for
CHROME_BINARIES = [
    "google-chrome",
    "google-chrome-stable", 
    "google-chrome-beta",
    "google-chrome-dev",
    "chromium",
    "chromium-browser",
]

# Chrome binary paths to check
CHROME_PATHS = [
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/opt/google/chrome/chrome",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
]

# Safe Chrome flags for initial launch
SAFE_CHROME_FLAGS = [
    "--enable-logging=stderr",
    "--v=1",
    "--disable-background-timer-throttling",
    "--disable-renderer-backgrounding",
]

# Progressive fallback flags
FALLBACK_FLAGS = {
    "no_gpu": ["--disable-gpu"],
    "no_vaapi": ["--disable-gpu", "--disable-features=VaapiVideoDecoder"],
    "safe_mode": ["--disable-gpu", "--no-sandbox", "--incognito"],
    "minimal": ["--disable-gpu", "--no-sandbox", "--disable-extensions", "--disable-plugins"],
}

# Environment variables
ENV_VARS = {
    "CT_COLOR": "Enable colored output (1/0)",
    "CT_LOG_LEVEL": "Set log level (DEBUG/INFO/WARNING/ERROR)",
    "CT_LAUNCH_TIMEOUT": "Chrome launch timeout in seconds",
    "CT_MAX_ATTEMPTS": "Maximum launch attempts",
    "CT_SELINUX_FIX": "Enable SELinux fixes (1/0)",
    "CT_FLATPAK_FALLBACK": "Enable Flatpak fallback (1/0)",
    "CT_JOURNAL_LINES": "Number of journal lines to collect",
    "CT_EXTRA_FLAGS": "Additional Chrome flags (space-separated)",
}

# Default configuration values
DEFAULT_CONFIG = {
    "launch_timeout": 15,
    "max_attempts": 4,
    "log_level": "INFO",
    "enable_colors": True,
    "enable_selinux_fix": True,
    "enable_flatpak_fallback": True,
    "journal_lines": 100,
    "extra_flags": [],
}

# Log patterns to watch for
LOG_PATTERNS = {
    "seccomp_issues": [r"seccomp.*chrome", r"SECCOMP.*chrome"],
    "gpu_hangs": [r"i915.*hang", r"amdgpu.*hang", r"gpu.*hang"],
    "oom_kills": [r"oom-killer.*chrome", r"chrome.*killed.*memory"],
    "segfaults": [r"chrome.*segfault", r"chrome.*SIGSEGV"],
    "vaapi_errors": [r"vaapi.*error", r"va-api.*fail"],
    "wayland_issues": [r"wayland.*chrome.*error"],
}

# File extensions and paths
LOG_EXTENSIONS = [".log", ".jsonl", ".sqlite"]
CHROME_LOG_PATHS = [
    "~/.config/google-chrome/chrome_debug.log",
    "~/.cache/google-chrome/chrome_debug.log",
    "/tmp/chrome_debug.log",
]

# System dependencies to check
SYSTEM_DEPS = {
    "chrome": "Chrome browser executable",
    "journalctl": "Systemd journal access",
    "dmesg": "Kernel message access", 
    "flock": "File locking utility",
    "flatpak": "Flatpak package manager",
    "coredumpctl": "Systemd coredump analysis",
}

# Timeout values (seconds)
TIMEOUTS = {
    "chrome_launch": 15,
    "diagnostics_collection": 30,
    "log_collection": 10,
    "process_wait": 5,
}

# File size limits (bytes)
SIZE_LIMITS = {
    "max_log_file": 10 * 1024 * 1024,  # 10MB
    "max_session_size": 100 * 1024 * 1024,  # 100MB
    "max_total_cache": 1024 * 1024 * 1024,  # 1GB
}

# Colors for terminal output
COLORS = {
    "success": "green",
    "error": "red", 
    "warning": "yellow",
    "info": "blue",
    "debug": "cyan",
    "progress": "magenta",
}

# Exit codes
EXIT_CODES = {
    "success": 0,
    "general_error": 1,
    "chrome_not_found": 2,
    "launch_failed": 3,
    "config_error": 4,
    "permission_error": 5,
    "interrupted": 130,
}
