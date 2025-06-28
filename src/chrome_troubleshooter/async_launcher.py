#!/usr/bin/env python3
"""
🚀 ASYNC CHROME LAUNCHER - NON-BLOCKING OPERATIONS
Enhanced launcher with concurrent diagnostics collection
"""

import asyncio
import subprocess
import shutil
import time
import psutil
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

import aiofiles

from .config import Config
from .logger import StructuredLogger


@dataclass
class LaunchAttempt:
    """Data class for tracking launch attempts."""
    attempt_number: int
    flags: List[str]
    strategy: str
    start_time: float
    end_time: Optional[float] = None
    success: bool = False
    error: Optional[str] = None
    process_id: Optional[int] = None


class AsyncChromeLauncher:
    """Async Chrome launcher with concurrent diagnostics."""
    
    def __init__(self, config: Config, logger: StructuredLogger):
        self.config = config
        self.logger = logger
        self.chrome_paths = self._find_chrome_paths()
        self.attempts: List[LaunchAttempt] = []
        
    def _find_chrome_paths(self) -> List[str]:
        """Find available Chrome executables."""
        possible_paths = [
            "google-chrome",
            "google-chrome-stable", 
            "google-chrome-beta",
            "google-chrome-dev",
            "chromium",
            "chromium-browser",
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable",
            "/opt/google/chrome/chrome",
        ]
        
        found_paths = []
        for path in possible_paths:
            if shutil.which(path):
                found_paths.append(path)
                
        return found_paths
    
    async def launch_with_concurrent_diagnostics(self) -> bool:
        """Launch Chrome with concurrent diagnostics collection."""
        if not self.chrome_paths:
            self.logger.error("launcher", "No Chrome executable found")
            return False
            
        # Start concurrent diagnostics collection
        diagnostics_task = asyncio.create_task(self._collect_concurrent_diagnostics())
        
        try:
            # Try progressive launch strategies
            strategies = [
                ("vanilla", []),
                ("no_gpu", ["--disable-gpu"]),
                ("no_vaapi", ["--disable-gpu", "--disable-features=VaapiVideoDecoder"]),
                ("safe_mode", ["--disable-gpu", "--no-sandbox", "--incognito"]),
            ]
            
            for attempt_num, (strategy, base_flags) in enumerate(strategies, 1):
                if attempt_num > self.config.max_attempts:
                    break
                    
                # Prepare flags
                flags = base_flags + self.config.extra_flags
                
                # Apply environment-specific fixes
                flags = await self._apply_environment_fixes(flags)
                
                # Create launch attempt
                attempt = LaunchAttempt(
                    attempt_number=attempt_num,
                    flags=flags,
                    strategy=strategy,
                    start_time=time.time()
                )
                
                self.logger.info("launcher", f"Attempt {attempt_num}: {strategy} strategy")
                
                # Try to launch
                success = await self._launch_chrome_async(self.chrome_paths[0], flags, attempt)
                
                attempt.end_time = time.time()
                attempt.success = success
                self.attempts.append(attempt)
                
                if success:
                    self.logger.info("launcher", f"Chrome launched successfully with {strategy} strategy")
                    return True
                    
                # Wait before next attempt
                if attempt_num < len(strategies):
                    await asyncio.sleep(2)
                    
            # If all attempts failed, try Flatpak fallback
            if self.config.enable_flatpak_fallback:
                return await self._try_flatpak_fallback()
                
            return False
            
        finally:
            # Cancel diagnostics collection
            diagnostics_task.cancel()
            try:
                await diagnostics_task
            except asyncio.CancelledError:
                pass
    
    async def _launch_chrome_async(self, chrome_path: str, flags: List[str], attempt: LaunchAttempt) -> bool:
        """Launch Chrome asynchronously."""
        try:
            # Build command
            cmd = [chrome_path] + flags
            
            # Log the command
            self.logger.debug("launcher", f"Executing: {' '.join(cmd)}")
            
            # Launch process
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                start_new_session=True
            )
            
            attempt.process_id = process.pid
            
            # Wait for process to start or fail
            try:
                await asyncio.wait_for(process.wait(), timeout=self.config.launch_timeout)
                # If we get here, the process exited (probably failed)
                stdout, stderr = await process.communicate()
                attempt.error = stderr.decode() if stderr else "Process exited unexpectedly"
                return False
                
            except asyncio.TimeoutError:
                # Process is still running after timeout - this is good!
                # Check if Chrome is actually responding
                if await self._verify_chrome_running(process.pid):
                    return True
                else:
                    # Kill the process if it's not responding
                    try:
                        process.terminate()
                        await asyncio.wait_for(process.wait(), timeout=5)
                    except asyncio.TimeoutError:
                        process.kill()
                    return False
                    
        except Exception as e:
            attempt.error = str(e)
            self.logger.error("launcher", f"Launch failed: {e}")
            return False
    
    async def _verify_chrome_running(self, pid: int) -> bool:
        """Verify Chrome process is running and responsive."""
        try:
            # Check if process exists
            if not psutil.pid_exists(pid):
                return False
                
            process = psutil.Process(pid)
            
            # Check if it's actually Chrome
            if "chrome" not in process.name().lower():
                return False
                
            # Check if process is responsive (not zombie)
            if process.status() == psutil.STATUS_ZOMBIE:
                return False
                
            # Give Chrome a moment to fully initialize
            await asyncio.sleep(2)
            
            # Check if still running after initialization
            return psutil.pid_exists(pid) and process.status() != psutil.STATUS_ZOMBIE
            
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False
    
    async def _apply_environment_fixes(self, flags: List[str]) -> List[str]:
        """Apply environment-specific fixes."""
        import os
        
        # Wayland compatibility
        session_type = os.environ.get('XDG_SESSION_TYPE')
        if session_type == 'wayland':
            flags.extend(['--ozone-platform=x11', '--disable-features=UseOzonePlatform'])
            
        # SELinux fixes
        if self.config.enable_selinux_fix:
            await self._apply_selinux_fix()
            
        return flags
    
    async def _apply_selinux_fix(self):
        """Apply SELinux permissive rule for Chrome."""
        try:
            # Check if SELinux is enforcing
            result = await asyncio.create_subprocess_exec(
                'getenforce',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await result.communicate()
            
            if stdout.decode().strip() == 'Enforcing':
                # Apply permissive rule
                self.logger.info("selinux", "Applying SELinux permissive rule for chrome_sandbox_t")
                await asyncio.create_subprocess_exec(
                    'sudo', 'semanage', 'permissive', '-a', 'chrome_sandbox_t',
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
        except Exception as e:
            self.logger.warning("selinux", f"Could not apply SELinux fix: {e}")
    
    async def _try_flatpak_fallback(self) -> bool:
        """Try launching Chromium via Flatpak as fallback."""
        try:
            self.logger.info("launcher", "Trying Flatpak Chromium fallback")
            
            # Check if Flatpak is available
            if not shutil.which("flatpak"):
                self.logger.warning("launcher", "Flatpak not available")
                return False
                
            # Try to launch Flatpak Chromium
            process = await asyncio.create_subprocess_exec(
                'flatpak', 'run', 'org.chromium.Chromium',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Wait briefly to see if it starts
            try:
                await asyncio.wait_for(process.wait(), timeout=5)
                return False  # Exited too quickly
            except asyncio.TimeoutError:
                # Still running - good!
                return await self._verify_chrome_running(process.pid)
                
        except Exception as e:
            self.logger.error("launcher", f"Flatpak fallback failed: {e}")
            return False
    
    async def _collect_concurrent_diagnostics(self):
        """Collect diagnostics concurrently while Chrome is launching."""
        try:
            # Collect system info
            await self._collect_system_info()
            
            # Monitor dmesg for issues
            await self._monitor_dmesg()
            
            # Collect journal logs
            await self._collect_journal_logs()
            
        except asyncio.CancelledError:
            self.logger.debug("diagnostics", "Concurrent diagnostics collection cancelled")
            raise
        except Exception as e:
            self.logger.error("diagnostics", f"Error in concurrent diagnostics: {e}")
    
    async def _collect_system_info(self):
        """Collect system information asynchronously."""
        import platform
        
        info = {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "cpu_count": psutil.cpu_count(),
            "memory_total": psutil.virtual_memory().total,
            "disk_usage": psutil.disk_usage('/').percent,
        }
        
        self.logger.info("system", f"System info collected: {info}")
    
    async def _monitor_dmesg(self):
        """Monitor dmesg for Chrome-related messages."""
        try:
            process = await asyncio.create_subprocess_exec(
                'dmesg', '-T', '--follow',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Read dmesg output for a limited time
            start_time = time.time()
            while time.time() - start_time < 30:  # Monitor for 30 seconds
                try:
                    line = await asyncio.wait_for(process.stdout.readline(), timeout=1)
                    if not line:
                        break
                        
                    line_str = line.decode().strip()
                    if 'chrome' in line_str.lower():
                        self.logger.info("dmesg", line_str)
                        
                except asyncio.TimeoutError:
                    continue
                    
        except Exception as e:
            self.logger.debug("dmesg", f"Could not monitor dmesg: {e}")
    
    async def _collect_journal_logs(self):
        """Collect systemd journal logs asynchronously."""
        try:
            process = await asyncio.create_subprocess_exec(
                'journalctl', '-f', '--lines=50', '--grep=chrome',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Read journal output for a limited time
            start_time = time.time()
            while time.time() - start_time < 30:  # Monitor for 30 seconds
                try:
                    line = await asyncio.wait_for(process.stdout.readline(), timeout=1)
                    if not line:
                        break
                        
                    line_str = line.decode().strip()
                    self.logger.info("journal", line_str)
                    
                except asyncio.TimeoutError:
                    continue
                    
        except Exception as e:
            self.logger.debug("journal", f"Could not collect journal logs: {e}")
    
    def get_launch_summary(self) -> Dict[str, Any]:
        """Get summary of all launch attempts."""
        return {
            "total_attempts": len(self.attempts),
            "successful": any(attempt.success for attempt in self.attempts),
            "attempts": [
                {
                    "number": attempt.attempt_number,
                    "strategy": attempt.strategy,
                    "success": attempt.success,
                    "duration": attempt.end_time - attempt.start_time if attempt.end_time else None,
                    "error": attempt.error,
                    "flags": attempt.flags,
                }
                for attempt in self.attempts
            ]
        }
