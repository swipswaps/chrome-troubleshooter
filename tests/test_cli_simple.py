#!/usr/bin/env python3
"""
Tests for simplified CLI interface
"""

from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from chrome_troubleshooter.cli_simple import app, main
from chrome_troubleshooter.config import Config


@pytest.fixture
def runner():
    """Create a CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_config():
    """Create a mock configuration."""
    config = Config()
    config.launch_timeout = 15
    config.max_attempts = 3
    config.log_level = "INFO"
    config.base_dir = Path("/tmp/test_chrome_troubleshooter")
    return config


class TestSimplifiedCLI:
    """Test cases for the simplified CLI."""

    def test_help_command(self, runner):
        """Test help command displays correctly."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Chrome crash diagnosis" in result.stdout
        assert "launch" in result.stdout
        assert "diagnose" in result.stdout
        assert "status" in result.stdout
        assert "version" in result.stdout

    def test_version_command(self, runner):
        """Test version command."""
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "Chrome Troubleshooter" in result.stdout

    @patch('chrome_troubleshooter.cli_simple.load_config')
    def test_status_command_basic(self, mock_load_config, runner, mock_config):
        """Test basic status command."""
        mock_load_config.return_value = mock_config

        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "Chrome Troubleshooter Status" in result.stdout
        assert "Configuration loaded: ✅" in result.stdout
        assert "Launch timeout: 15s" in result.stdout

    @patch('chrome_troubleshooter.cli_simple.load_config')
    @patch('shutil.which')
    def test_status_command_with_deps(self, mock_which, mock_load_config, runner, mock_config):
        """Test status command with dependency checking."""
        mock_load_config.return_value = mock_config

        # Mock dependency availability
        def which_side_effect(cmd):
            return f"/usr/bin/{cmd}" if cmd in ["google-chrome", "journalctl", "dmesg"] else None

        mock_which.side_effect = which_side_effect

        result = runner.invoke(app, ["status", "--check-deps"])
        assert result.exit_code == 0
        assert "Dependencies:" in result.stdout
        assert "chrome: ✅ Available" in result.stdout
        assert "journalctl: ✅ Available" in result.stdout
        assert "dmesg: ✅ Available" in result.stdout

    @patch('chrome_troubleshooter.cli_simple.load_config')
    def test_config_error_handling(self, mock_load_config, runner):
        """Test configuration error handling."""
        mock_load_config.side_effect = Exception("Config file not found")

        result = runner.invoke(app, ["status"])
        assert result.exit_code == 1
        assert "Error: Config file not found" in result.stdout


class TestMainFunction:
    """Test cases for the main function."""

    @patch('chrome_troubleshooter.cli_simple.app')
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.touch')
    @patch('pathlib.Path.unlink')
    def test_main_function_success(self, mock_unlink, mock_touch, mock_exists, mock_app):
        """Test successful main function execution."""
        mock_exists.return_value = False  # No lock file exists
        mock_app.return_value = None

        # Should not raise any exception
        main()

        mock_touch.assert_called_once()
        mock_app.assert_called_once()
        mock_unlink.assert_called_once()

    @patch('pathlib.Path.exists')
    def test_main_function_lock_file_exists(self, mock_exists):
        """Test main function when lock file exists."""
        mock_exists.return_value = True  # Lock file exists

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
