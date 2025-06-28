#!/usr/bin/env python3
"""
Tests for chrome_troubleshooter.config module
"""

import os
import json
import tempfile
from pathlib import Path
import pytest

from chrome_troubleshooter.config import Config, load_config, save_config


class TestConfig:
    """Test configuration management"""

    def test_default_config(self):
        """Test default configuration values"""
        config = Config()

        assert config.enable_colors is True
        assert config.log_level == "INFO"
        assert config.journal_lines == 200
        assert config.rotate_days == 7
        assert config.launch_timeout == 10
        assert config.max_attempts == 4
        assert config.enable_selinux_fix is True
        assert config.enable_flatpak_fallback is True
        assert config.enable_sqlite is True
        assert config.enable_json is True
        assert isinstance(config.base_dir, Path)
        assert isinstance(config.chrome_paths, list)
        assert len(config.chrome_paths) > 0

    def test_environment_variable_overrides(self):
        """Test environment variable configuration overrides"""
        # Set environment variables
        env_vars = {
            "CT_COLOR": "0",
            "CT_LOG_LEVEL": "DEBUG",
            "CT_JOURNAL_LINES": "500",
            "CT_ROTATE_DAYS": "14",
            "CT_LAUNCH_TIMEOUT": "20",
            "CT_MAX_ATTEMPTS": "6",
            "CT_SELINUX_FIX": "0",
            "CT_FLATPAK_FALLBACK": "0",
            "CT_ENABLE_SQLITE": "0",
            "CT_ENABLE_JSON": "0",
            "CT_EXTRA_FLAGS": "--disable-gpu --no-sandbox",
        }

        # Temporarily set environment variables
        old_env = {}
        for key, value in env_vars.items():
            old_env[key] = os.environ.get(key)
            os.environ[key] = value

        try:
            config = Config()

            assert config.enable_colors is False
            assert config.log_level == "DEBUG"
            assert config.journal_lines == 500
            assert config.rotate_days == 14
            assert config.launch_timeout == 20
            assert config.max_attempts == 6
            assert config.enable_selinux_fix is False
            assert config.enable_flatpak_fallback is False
            assert config.enable_sqlite is False
            assert config.enable_json is False
            assert config.extra_flags == ["--disable-gpu", "--no-sandbox"]

        finally:
            # Restore environment
            for key, old_value in old_env.items():
                if old_value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = old_value

    def test_validation_ranges(self):
        """Test configuration validation and range limits"""
        # Test journal_lines limits
        os.environ["CT_JOURNAL_LINES"] = "5"  # Below minimum
        config = Config()
        assert config.journal_lines == 10  # Should be clamped to minimum

        os.environ["CT_JOURNAL_LINES"] = "20000"  # Above maximum
        config = Config()
        assert config.journal_lines == 10000  # Should be clamped to maximum

        # Test rotate_days limits
        os.environ["CT_ROTATE_DAYS"] = "0"  # Below minimum
        config = Config()
        assert config.rotate_days == 1  # Should be clamped to minimum

        os.environ["CT_ROTATE_DAYS"] = "500"  # Above maximum
        config = Config()
        assert config.rotate_days == 365  # Should be clamped to maximum

        # Clean up
        os.environ.pop("CT_JOURNAL_LINES", None)
        os.environ.pop("CT_ROTATE_DAYS", None)

    def test_file_loading_and_saving(self):
        """Test configuration file loading and saving"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_config.json"

            # Create initial config
            config = Config()
            config.launch_timeout = 25
            config.max_attempts = 8
            config.enable_colors = False

            # Save to file
            save_config(config, config_path)
            assert config_path.exists()

            # Load from file
            loaded_config = load_config(config_path)
            assert loaded_config.launch_timeout == 25
            assert loaded_config.max_attempts == 8
            assert loaded_config.enable_colors is False

    def test_chrome_executable_detection(self):
        """Test Chrome executable detection"""
        config = Config()

        # Test with mock paths
        config.chrome_paths = [
            "/nonexistent/chrome",
            "/usr/bin/python3",
        ]  # python3 should exist
        chrome_exe = config.get_chrome_executable()

        # Should find python3 (which exists and is executable)
        assert chrome_exe == "/usr/bin/python3"

        # Test with no valid paths
        config.chrome_paths = ["/nonexistent/chrome1", "/nonexistent/chrome2"]
        chrome_exe = config.get_chrome_executable()
        assert chrome_exe is None

    def test_dependency_validation(self):
        """Test system dependency validation"""
        config = Config()
        deps = config.validate_dependencies()

        # Check that we get a dictionary with expected keys
        expected_deps = [
            "python3",
            "sqlite3",
            "flock",
            "journalctl",
            "dmesg",
            "lspci",
            "rpm",
            "flatpak",
            "semanage",
            "chrome",
        ]

        for dep in expected_deps:
            assert dep in deps
            assert isinstance(deps[dep], bool)

        # Python3 should always be available (we're running in Python)
        assert deps["python3"] is True

    def test_missing_dependencies(self):
        """Test missing dependencies detection"""
        config = Config()

        # Mock chrome_paths to ensure Chrome is "missing"
        config.chrome_paths = ["/nonexistent/chrome"]

        missing = config.get_missing_dependencies()
        assert isinstance(missing, list)
        assert "chrome" in missing  # Chrome should be missing with our mock paths

    def test_print_status(self, capsys):
        """Test configuration status printing"""
        config = Config()
        config.print_status()

        captured = capsys.readouterr()
        assert "Chrome Troubleshooter Configuration:" in captured.out
        assert "Base Directory:" in captured.out
        assert "Log Level:" in captured.out

    def test_invalid_json_file(self):
        """Test handling of invalid JSON configuration file"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "invalid_config.json"

            # Write invalid JSON
            with open(config_path, "w") as f:
                f.write("{ invalid json }")

            # Should not raise exception, should use defaults
            config = load_config(config_path)
            assert config.launch_timeout == 10  # Default value

    def test_nonexistent_config_file(self):
        """Test handling of nonexistent configuration file"""
        nonexistent_path = Path("/nonexistent/config.json")

        # Should not raise exception, should use defaults
        config = load_config(nonexistent_path)
        assert config.launch_timeout == 10  # Default value


if __name__ == "__main__":
    pytest.main([__file__])
