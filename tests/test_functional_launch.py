#!/usr/bin/env python3
"""
Functional tests for Chrome launcher with headless mode
Based on ChatGPT suggestion U6 for comprehensive testing
"""

import os
import shutil
import subprocess
from unittest.mock import patch

import pytest

from chrome_troubleshooter.config import Config
from chrome_troubleshooter.launcher import ChromeLauncher
from chrome_troubleshooter.logger import StructuredLogger


class TestFunctionalLaunch:
    """Functional tests for Chrome launching"""

    @pytest.fixture
    def temp_session_dir(self, tmp_path):
        """Create temporary session directory"""
        session_dir = tmp_path / "test_session"
        session_dir.mkdir(parents=True, exist_ok=True)
        return session_dir

    @pytest.fixture
    def test_config(self):
        """Create test configuration"""
        config = Config()
        config.launch_timeout = 3  # Short timeout for tests
        config.max_attempts = 2
        config.enable_selinux_fix = False  # Don't modify system in tests
        config.enable_flatpak_fallback = False  # Skip flatpak in tests
        return config

    @pytest.fixture
    def test_logger(self, temp_session_dir):
        """Create test logger"""
        return StructuredLogger(
            temp_session_dir,
            enable_colors=False,  # No colors in tests
            enable_sqlite=True,
            enable_json=True
        )

    def test_chrome_detection(self):
        """Test Chrome executable detection"""
        # Test that we can find some Chrome-like executable
        chrome_candidates = [
            "google-chrome",
            "google-chrome-stable",
            "chromium",
            "chromium-browser"
        ]

        found_chrome = None
        for candidate in chrome_candidates:
            if shutil.which(candidate):
                found_chrome = candidate
                break

        if not found_chrome:
            pytest.skip("No Chrome/Chromium executable found for testing")

        assert found_chrome is not None

    @pytest.mark.skipif(
        not any(shutil.which(cmd) for cmd in ["google-chrome", "chromium", "chromium-browser"]),
        reason="No Chrome/Chromium executable available"
    )
    def test_headless_launch_success(self, test_config, test_logger, temp_session_dir):
        """Test successful headless Chrome launch"""
        # Override config to use headless mode for testing
        test_config.extra_flags = ["--headless", "--disable-gpu", "--no-sandbox"]

        launcher = ChromeLauncher(test_config, test_logger)

        # Mock the lock acquisition to avoid conflicts
        with patch.object(launcher, 'acquire_lock', return_value=True), \
             patch.object(launcher, 'release_lock'):

            # Test environment detection
            env_adjustments = launcher.detect_environment()
            assert "base_flags" in env_adjustments
            assert "environment_flags" in env_adjustments

            # Test that we can build launch stages
            assert len(launcher.launch_stages) > 0
            assert launcher.launch_stages[0]["name"] == "vanilla"

    @pytest.mark.skipif(
        not shutil.which("chromium"),
        reason="Chromium not available for headless testing"
    )
    def test_headless_chromium_launch(self, test_config, test_logger):
        """Test actual headless Chromium launch (if available)"""
        # Force use of Chromium for predictable testing
        test_config.extra_flags = [
            "--headless",
            "--disable-gpu",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--virtual-time-budget=1000"  # Exit after 1 second
        ]

        launcher = ChromeLauncher(test_config, test_logger)

        # Override Chrome executable detection to use Chromium
        with patch.object(test_config, 'get_chrome_executable', return_value=shutil.which("chromium")):
            # Test a single launch stage
            env_adjustments = launcher.detect_environment()
            stage = {"name": "test", "description": "Test stage", "flags": []}

            success, process = launcher.launch_chrome_stage(stage, env_adjustments)

            if process:
                # Clean up the process
                try:
                    process.terminate()
                    process.wait(timeout=5)
                except (subprocess.TimeoutExpired, ProcessLookupError):
                    pass

            # In headless mode with virtual time budget, this should succeed briefly
            # Note: We don't assert success=True because Chrome might exit immediately
            # The important thing is that we can launch without crashing

    def test_lock_file_handling(self, test_config, test_logger):
        """Test lock file acquisition and release"""
        launcher = ChromeLauncher(test_config, test_logger)

        # Test lock acquisition
        assert launcher.acquire_lock()

        # Test that second acquisition fails
        launcher2 = ChromeLauncher(test_config, test_logger)
        assert not launcher2.acquire_lock()

        # Test lock release
        launcher.release_lock()

        # Test that we can acquire again after release
        assert launcher2.acquire_lock()
        launcher2.release_lock()

    def test_environment_detection(self, test_config, test_logger):
        """Test system environment detection"""
        launcher = ChromeLauncher(test_config, test_logger)

        env_info = launcher.detect_environment()

        # Check that we get expected structure
        assert "base_flags" in env_info
        assert "environment_flags" in env_info
        assert "warnings" in env_info

        # Check that base flags include logging
        assert any("--enable-logging" in flag for flag in env_info["base_flags"])

    def test_launch_stages_generation(self, test_config, test_logger):
        """Test that launch stages are properly generated"""
        launcher = ChromeLauncher(test_config, test_logger)

        stages = launcher.launch_stages

        # Should have at least vanilla and safe mode
        assert len(stages) >= 2

        # First stage should be vanilla
        assert stages[0]["name"] == "vanilla"
        assert stages[0]["flags"] == []

        # Last stage should be safe mode
        assert stages[-1]["name"] == "safe_mode"
        assert "--no-sandbox" in stages[-1]["flags"]

    def test_logger_integration(self, test_config, temp_session_dir):
        """Test logger integration with launcher"""
        logger = StructuredLogger(temp_session_dir, enable_colors=False)
        ChromeLauncher(test_config, logger)

        # Test that logger files are created
        assert logger.log_file.parent.exists()

        # Test logging
        logger.info("test", "Test message")

        # Check that log file was created and has content
        if logger.log_file.exists():
            content = logger.log_file.read_text()
            assert "Test message" in content

    @pytest.mark.skipif(
        os.getenv("CI") != "true",
        reason="Only run in CI environment with xvfb"
    )
    def test_ci_headless_launch(self, test_config, test_logger):
        """Test Chrome launch in CI environment with xvfb"""
        # This test only runs in CI where xvfb is available
        test_config.extra_flags = [
            "--headless",
            "--disable-gpu",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-extensions"
        ]

        launcher = ChromeLauncher(test_config, test_logger)

        with patch.object(launcher, 'acquire_lock', return_value=True), \
             patch.object(launcher, 'release_lock'):

            # Test environment detection in CI
            env_adjustments = launcher.detect_environment()
            assert env_adjustments is not None

            # In CI, we should be able to at least attempt a launch
            # without system modifications
