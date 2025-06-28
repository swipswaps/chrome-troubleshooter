#!/usr/bin/env python3
"""
🔧 CHROME TROUBLESHOOTER - CONFIGURATION
Centralized configuration management with environment variable support
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field


@dataclass
class Config:
    """Configuration class with environment variable overrides and validation"""

    # Logging configuration
    enable_colors: bool = field(
        default_factory=lambda: os.getenv("CT_COLOR", "1") == "1"
    )
    log_level: str = field(default_factory=lambda: os.getenv("CT_LOG_LEVEL", "INFO"))
    journal_lines: int = field(
        default_factory=lambda: int(os.getenv("CT_JOURNAL_LINES", "200"))
    )
    rotate_days: int = field(
        default_factory=lambda: int(os.getenv("CT_ROTATE_DAYS", "7"))
    )

    # Chrome launch configuration
    extra_flags: List[str] = field(
        default_factory=lambda: (
            os.getenv("CT_EXTRA_FLAGS", "").split()
            if os.getenv("CT_EXTRA_FLAGS")
            else []
        )
    )
    launch_timeout: int = field(
        default_factory=lambda: int(os.getenv("CT_LAUNCH_TIMEOUT", "10"))
    )
    max_attempts: int = field(
        default_factory=lambda: int(os.getenv("CT_MAX_ATTEMPTS", "4"))
    )

    # System configuration
    enable_selinux_fix: bool = field(
        default_factory=lambda: os.getenv("CT_SELINUX_FIX", "1") == "1"
    )
    enable_flatpak_fallback: bool = field(
        default_factory=lambda: os.getenv("CT_FLATPAK_FALLBACK", "1") == "1"
    )

    # Storage configuration
    base_dir: Path = field(
        default_factory=lambda: Path(
            os.getenv("CT_BASE_DIR", Path.home() / ".cache" / "chrome_troubleshooter")
        )
    )
    enable_sqlite: bool = field(
        default_factory=lambda: os.getenv("CT_ENABLE_SQLITE", "1") == "1"
    )
    enable_json: bool = field(
        default_factory=lambda: os.getenv("CT_ENABLE_JSON", "1") == "1"
    )

    # Chrome executable paths (auto-detected if not specified)
    chrome_paths: List[str] = field(
        default_factory=lambda: [
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable",
            "/usr/bin/chromium",
            "/usr/bin/chromium-browser",
            "/opt/google/chrome/chrome",
            "/snap/bin/chromium",
        ]
    )

    def __post_init__(self):
        """Validate configuration after initialization"""
        self.base_dir = Path(self.base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        # Validate numeric ranges
        if self.journal_lines < 10:
            self.journal_lines = 10
        elif self.journal_lines > 10000:
            self.journal_lines = 10000

        if self.rotate_days < 1:
            self.rotate_days = 1
        elif self.rotate_days > 365:
            self.rotate_days = 365

        if self.launch_timeout < 5:
            self.launch_timeout = 5
        elif self.launch_timeout > 300:
            self.launch_timeout = 300

        if self.max_attempts < 1:
            self.max_attempts = 1
        elif self.max_attempts > 10:
            self.max_attempts = 10

    @classmethod
    def from_file(cls, config_path: Path) -> "Config":
        """Load configuration from JSON file with environment variable overrides"""
        config_data = {}

        if config_path.exists():
            try:
                with open(config_path, "r") as f:
                    config_data = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load config from {config_path}: {e}")

        # Environment variables override file settings
        return cls(**config_data)

    def to_file(self, config_path: Path) -> None:
        """Save current configuration to JSON file"""
        config_data = {
            "enable_colors": self.enable_colors,
            "log_level": self.log_level,
            "journal_lines": self.journal_lines,
            "rotate_days": self.rotate_days,
            "extra_flags": self.extra_flags,
            "launch_timeout": self.launch_timeout,
            "max_attempts": self.max_attempts,
            "enable_selinux_fix": self.enable_selinux_fix,
            "enable_flatpak_fallback": self.enable_flatpak_fallback,
            "base_dir": str(self.base_dir),
            "enable_sqlite": self.enable_sqlite,
            "enable_json": self.enable_json,
            "chrome_paths": self.chrome_paths,
        }

        try:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(config_path, "w") as f:
                json.dump(config_data, f, indent=2)
        except IOError as e:
            print(f"Warning: Could not save config to {config_path}: {e}")

    def get_chrome_executable(self) -> Optional[str]:
        """Find the first available Chrome executable"""
        for path in self.chrome_paths:
            if Path(path).is_file() and os.access(path, os.X_OK):
                return path
        return None

    def validate_dependencies(self) -> Dict[str, bool]:
        """Check if required system dependencies are available"""
        dependencies = {
            "python3": True,  # We're running in Python
            "sqlite3": False,
            "flock": False,
            "journalctl": False,
            "dmesg": False,
            "lspci": False,
            "rpm": False,
            "flatpak": False,
            "semanage": False,
            "chrome": False,
        }

        # Check command availability
        import shutil

        for cmd in [
            "sqlite3",
            "flock",
            "journalctl",
            "dmesg",
            "lspci",
            "rpm",
            "flatpak",
            "semanage",
        ]:
            dependencies[cmd] = shutil.which(cmd) is not None

        # Check Chrome availability
        dependencies["chrome"] = self.get_chrome_executable() is not None

        return dependencies

    def get_missing_dependencies(self) -> List[str]:
        """Get list of missing critical dependencies"""
        deps = self.validate_dependencies()
        critical = ["flock", "journalctl", "dmesg", "chrome"]

        missing = []
        for dep in critical:
            if not deps[dep]:
                missing.append(dep)

        return missing

    def print_status(self) -> None:
        """Print current configuration status"""
        print("🔧 Chrome Troubleshooter Configuration:")
        print(f"  Base Directory: {self.base_dir}")
        print(f"  Log Level: {self.log_level}")
        print(f"  Colors: {'Enabled' if self.enable_colors else 'Disabled'}")
        print(f"  SQLite: {'Enabled' if self.enable_sqlite else 'Disabled'}")
        print(f"  JSON: {'Enabled' if self.enable_json else 'Disabled'}")
        print(f"  Launch Timeout: {self.launch_timeout}s")
        print(f"  Max Attempts: {self.max_attempts}")
        print(f"  Journal Lines: {self.journal_lines}")
        print(f"  Rotation Days: {self.rotate_days}")

        if self.extra_flags:
            print(f"  Extra Flags: {' '.join(self.extra_flags)}")

        chrome_exe = self.get_chrome_executable()
        if chrome_exe:
            print(f"  Chrome Executable: {chrome_exe}")
        else:
            print("  Chrome Executable: NOT FOUND")

        deps = self.validate_dependencies()
        missing = [k for k, v in deps.items() if not v]
        if missing:
            print(f"  Missing Dependencies: {', '.join(missing)}")
        else:
            print("  Dependencies: All available")


# Global configuration instance
config = Config()


def load_config(config_path: Optional[Path] = None) -> Config:
    """Load configuration from file or create default"""
    if config_path is None:
        config_path = Path.home() / ".config" / "chrome-troubleshooter" / "config.json"

    return Config.from_file(config_path)


def save_config(cfg: Config, config_path: Optional[Path] = None) -> None:
    """Save configuration to file"""
    if config_path is None:
        config_path = Path.home() / ".config" / "chrome-troubleshooter" / "config.json"

    cfg.to_file(config_path)
