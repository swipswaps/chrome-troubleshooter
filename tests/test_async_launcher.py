#!/usr/bin/env python3
"""
Tests for AsyncChromeLauncher
"""

import asyncio
import pytest
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path

from chrome_troubleshooter.config import Config
from chrome_troubleshooter.logger import StructuredLogger
from chrome_troubleshooter.async_launcher import AsyncChromeLauncher, LaunchAttempt


@pytest.fixture
def mock_config():
    """Create a mock configuration."""
    config = Config()
    config.launch_timeout = 10
    config.max_attempts = 3
    config.extra_flags = []
    config.enable_selinux_fix = True
    config.enable_flatpak_fallback = True
    return config


@pytest.fixture
def mock_logger():
    """Create a mock logger."""
    return Mock(spec=StructuredLogger)


@pytest.fixture
def launcher(mock_config, mock_logger):
    """Create an AsyncChromeLauncher instance."""
    return AsyncChromeLauncher(mock_config, mock_logger)


class TestAsyncChromeLauncher:
    """Test cases for AsyncChromeLauncher."""
    
    def test_init(self, launcher, mock_config, mock_logger):
        """Test launcher initialization."""
        assert launcher.config == mock_config
        assert launcher.logger == mock_logger
        assert isinstance(launcher.chrome_paths, list)
        assert isinstance(launcher.attempts, list)
        assert len(launcher.attempts) == 0
    
    @patch('shutil.which')
    def test_find_chrome_paths(self, mock_which, launcher):
        """Test Chrome path discovery."""
        # Mock shutil.which to return paths for some executables
        def which_side_effect(path):
            if path in ['google-chrome', 'chromium']:
                return f'/usr/bin/{path}'
            return None
        
        mock_which.side_effect = which_side_effect
        
        paths = launcher._find_chrome_paths()
        
        assert 'google-chrome' in paths
        assert 'chromium' in paths
        assert len(paths) >= 2
    
    @pytest.mark.asyncio
    async def test_verify_chrome_running_success(self, launcher):
        """Test Chrome process verification - success case."""
        with patch('psutil.pid_exists', return_value=True), \
             patch('psutil.Process') as mock_process_class:
            
            mock_process = Mock()
            mock_process.name.return_value = 'chrome'
            mock_process.status.return_value = 'running'
            mock_process_class.return_value = mock_process
            
            result = await launcher._verify_chrome_running(12345)
            assert result is True
    
    @pytest.mark.asyncio
    async def test_verify_chrome_running_not_exists(self, launcher):
        """Test Chrome process verification - process doesn't exist."""
        with patch('psutil.pid_exists', return_value=False):
            result = await launcher._verify_chrome_running(12345)
            assert result is False
    
    @pytest.mark.asyncio
    async def test_verify_chrome_running_zombie(self, launcher):
        """Test Chrome process verification - zombie process."""
        with patch('psutil.pid_exists', return_value=True), \
             patch('psutil.Process') as mock_process_class, \
             patch('psutil.STATUS_ZOMBIE', 'zombie'):
            
            mock_process = Mock()
            mock_process.name.return_value = 'chrome'
            mock_process.status.return_value = 'zombie'
            mock_process_class.return_value = mock_process
            
            result = await launcher._verify_chrome_running(12345)
            assert result is False
    
    @pytest.mark.asyncio
    async def test_apply_environment_fixes_wayland(self, launcher):
        """Test environment fixes for Wayland."""
        with patch.dict('os.environ', {'XDG_SESSION_TYPE': 'wayland'}):
            flags = await launcher._apply_environment_fixes(['--test-flag'])
            
            assert '--test-flag' in flags
            assert '--ozone-platform=x11' in flags
            assert '--disable-features=UseOzonePlatform' in flags
    
    @pytest.mark.asyncio
    async def test_apply_selinux_fix(self, launcher):
        """Test SELinux fix application."""
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            # Mock getenforce command
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (b'Enforcing\n', b'')
            mock_subprocess.return_value = mock_process
            
            await launcher._apply_selinux_fix()
            
            # Should call getenforce and semanage
            assert mock_subprocess.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_launch_chrome_async_success(self, launcher):
        """Test successful Chrome launch."""
        attempt = LaunchAttempt(
            attempt_number=1,
            flags=['--test'],
            strategy='test',
            start_time=0.0
        )
        
        with patch('asyncio.create_subprocess_exec') as mock_subprocess, \
             patch.object(launcher, '_verify_chrome_running', return_value=True):
            
            # Mock process that doesn't exit immediately (timeout)
            mock_process = AsyncMock()
            mock_process.pid = 12345
            mock_process.wait.side_effect = asyncio.TimeoutError()
            mock_subprocess.return_value = mock_process
            
            result = await launcher._launch_chrome_async('chrome', ['--test'], attempt)
            
            assert result is True
            assert attempt.process_id == 12345
    
    @pytest.mark.asyncio
    async def test_launch_chrome_async_failure(self, launcher):
        """Test failed Chrome launch."""
        attempt = LaunchAttempt(
            attempt_number=1,
            flags=['--test'],
            strategy='test',
            start_time=0.0
        )
        
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            # Mock process that exits immediately
            mock_process = AsyncMock()
            mock_process.pid = 12345
            mock_process.wait.return_value = 1  # Exit code 1
            mock_process.communicate.return_value = (b'', b'Error message')
            mock_subprocess.return_value = mock_process
            
            result = await launcher._launch_chrome_async('chrome', ['--test'], attempt)
            
            assert result is False
            assert attempt.error == 'Error message'
    
    @pytest.mark.asyncio
    async def test_collect_system_info(self, launcher):
        """Test system info collection."""
        with patch('psutil.cpu_count', return_value=4), \
             patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.disk_usage') as mock_disk:
            
            mock_memory.return_value.total = 8000000000
            mock_disk.return_value.percent = 50.0
            
            await launcher._collect_system_info()
            
            # Should log system info
            launcher.logger.info.assert_called()
    
    @pytest.mark.asyncio
    async def test_try_flatpak_fallback_success(self, launcher):
        """Test successful Flatpak fallback."""
        with patch('shutil.which', return_value='/usr/bin/flatpak'), \
             patch('asyncio.create_subprocess_exec') as mock_subprocess, \
             patch.object(launcher, '_verify_chrome_running', return_value=True):
            
            # Mock process that doesn't exit immediately
            mock_process = AsyncMock()
            mock_process.pid = 12345
            mock_process.wait.side_effect = asyncio.TimeoutError()
            mock_subprocess.return_value = mock_process
            
            result = await launcher._try_flatpak_fallback()
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_try_flatpak_fallback_no_flatpak(self, launcher):
        """Test Flatpak fallback when Flatpak is not available."""
        with patch('shutil.which', return_value=None):
            result = await launcher._try_flatpak_fallback()
            assert result is False
    
    def test_get_launch_summary(self, launcher):
        """Test launch summary generation."""
        # Add some mock attempts
        attempt1 = LaunchAttempt(1, ['--flag1'], 'vanilla', 0.0, 1.0, True)
        attempt2 = LaunchAttempt(2, ['--flag2'], 'no_gpu', 1.0, 2.0, False, 'Error')
        
        launcher.attempts = [attempt1, attempt2]
        
        summary = launcher.get_launch_summary()
        
        assert summary['total_attempts'] == 2
        assert summary['successful'] is True
        assert len(summary['attempts']) == 2
        assert summary['attempts'][0]['success'] is True
        assert summary['attempts'][1]['success'] is False
        assert summary['attempts'][1]['error'] == 'Error'


class TestLaunchAttempt:
    """Test cases for LaunchAttempt dataclass."""
    
    def test_launch_attempt_creation(self):
        """Test LaunchAttempt creation."""
        attempt = LaunchAttempt(
            attempt_number=1,
            flags=['--test'],
            strategy='vanilla',
            start_time=123.456
        )
        
        assert attempt.attempt_number == 1
        assert attempt.flags == ['--test']
        assert attempt.strategy == 'vanilla'
        assert attempt.start_time == 123.456
        assert attempt.end_time is None
        assert attempt.success is False
        assert attempt.error is None
        assert attempt.process_id is None
    
    def test_launch_attempt_completion(self):
        """Test LaunchAttempt after completion."""
        attempt = LaunchAttempt(
            attempt_number=1,
            flags=['--test'],
            strategy='vanilla',
            start_time=123.456
        )
        
        # Simulate completion
        attempt.end_time = 125.789
        attempt.success = True
        attempt.process_id = 12345
        
        assert attempt.end_time == 125.789
        assert attempt.success is True
        assert attempt.process_id == 12345
