#!/usr/bin/env python3
"""
🔧 CHROME TROUBLESHOOTER - CHROME LAUNCHER
Advanced Chrome launcher with progressive fallbacks and auto-remediation
"""

import os
import signal
import subprocess
import time
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import fcntl

from .logger import StructuredLogger
from .diagnostics import DiagnosticsCollector
from .config import Config


class ChromeLauncher:
    """Advanced Chrome launcher with progressive fallbacks and diagnostics"""

    def __init__(self, config: Config, logger: StructuredLogger):
        self.config = config
        self.logger = logger
        self.diagnostics = DiagnosticsCollector(logger)

        # Launch stages with progressive fallbacks (enhanced)
        self.launch_stages = self._build_launch_stages()

        # Lock file for single instance (enhanced with fcntl)
        self.lock_file = Path("/tmp/.chrome_troubleshooter.lock")
        self._lock_fd = None
        self.lock_fd = None

        # Process tracking
        self.chrome_process = None
        self.current_stage = None

    def _build_launch_stages(self) -> List[Dict[str, Any]]:
        """Build launch stages based on system environment"""
        stages = [
            {"name": "vanilla", "description": "Standard launch", "flags": []},
        ]

        # Get system info for intelligent fallbacks
        system_info = self.diagnostics.get_system_info()

        # GPU-specific fallbacks
        gpu_vendor = system_info.get("gpu_vendor", "unknown")
        if gpu_vendor == "nvidia":
            stages.append({
                "name": "no_nvidia_vaapi",
                "description": "Disable NVIDIA VA-API",
                "flags": ["--disable-features=VaapiVideoDecoder,VaapiVideoEncoder"]
            })
        elif gpu_vendor == "amd":
            stages.append({
                "name": "no_amd_vaapi",
                "description": "Disable AMD VA-API",
                "flags": ["--disable-features=VaapiVideoDecoder", "--disable-gpu-sandbox"]
            })

        # Standard GPU fallback
        stages.append({
            "name": "no_gpu",
            "description": "Disable GPU acceleration",
            "flags": ["--disable-gpu", "--disable-gpu-sandbox"]
        })

        # Wayland-specific fallbacks
        if system_info.get("session_type") == "wayland":
            stages.append({
                "name": "wayland_fallback",
                "description": "Wayland compatibility mode",
                "flags": ["--disable-gpu", "--enable-features=UseOzonePlatform", "--ozone-platform=wayland"]
            })

        # SELinux-specific fallbacks
        selinux_status = system_info.get("selinux_status", "unknown")
        if selinux_status == "enforcing":
            stages.append({
                "name": "selinux_compat",
                "description": "SELinux compatibility mode",
                "flags": ["--disable-gpu", "--no-sandbox", "--disable-seccomp-filter-sandbox"]
            })

        # Container-specific fallbacks
        container_type = system_info.get("container_type", "none")
        if container_type != "none":
            stages.append({
                "name": "container_mode",
                "description": f"Container mode ({container_type})",
                "flags": ["--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage", "--disable-setuid-sandbox"]
            })

        # Flatpak-specific fallbacks
        if system_info.get("running_in_flatpak", False):
            stages.append({
                "name": "flatpak_mode",
                "description": "Flatpak sandbox mode",
                "flags": ["--disable-gpu", "--no-sandbox", "--disable-seccomp-filter-sandbox"]
            })

        # Final safe mode fallback
        stages.append({
            "name": "safe_mode",
            "description": "Maximum compatibility mode",
            "flags": [
                "--disable-gpu", "--no-sandbox", "--disable-seccomp-filter-sandbox",
                "--disable-dev-shm-usage", "--disable-setuid-sandbox",
                "--disable-extensions", "--incognito"
            ]
        })

        return stages

    def acquire_lock(self) -> bool:
        """Acquire single-instance lock with enhanced error handling"""
        try:
            # Create lock file if it doesn't exist
            self.lock_file.touch(exist_ok=True)

            # Open with proper flags for cross-platform compatibility
            self.lock_fd = os.open(
                str(self.lock_file), os.O_CREAT | os.O_WRONLY | os.O_TRUNC
            )

            # Try to acquire exclusive lock (non-blocking)
            fcntl.flock(self.lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

            # Write PID and timestamp to lock file for debugging
            lock_info = f"{os.getpid()}:{int(time.time())}\n"
            os.write(self.lock_fd, lock_info.encode())
            os.fsync(self.lock_fd)  # Ensure data is written

            self.logger.debug("launcher", f"Acquired single-instance lock (PID: {os.getpid()})")
            return True

        except BlockingIOError:
            # Another instance is running
            self.logger.error("launcher", "Another Chrome troubleshooter instance is already running")
            if self.lock_fd is not None:
                try:
                    os.close(self.lock_fd)
                except OSError:
                    pass
                self.lock_fd = None
            return False
        except (OSError, IOError) as e:
            self.logger.error("launcher", f"Failed to acquire lock: {e}")
            if self.lock_fd is not None:
                try:
                    os.close(self.lock_fd)
                except OSError:
                    pass
                self.lock_fd = None
            return False

    def release_lock(self) -> None:
        """Release single-instance lock"""
        if self.lock_fd is not None:
            try:
                fcntl.flock(self.lock_fd, fcntl.LOCK_UN)
                os.close(self.lock_fd)
                self.lock_file.unlink(missing_ok=True)
                self.logger.debug("launcher", "Released single-instance lock")
            except (OSError, IOError):
                pass
            finally:
                self.lock_fd = None

    def detect_environment(self) -> Dict[str, Any]:
        """Detect system environment and return configuration adjustments"""
        env_info = self.diagnostics.get_system_info()
        gpu_info = self.diagnostics.get_gpu_info()

        adjustments = {
            "base_flags": ["--enable-logging=stderr", "--v=1"],
            "environment_flags": [],
            "warnings": [],
        }

        # Add user-specified extra flags
        if self.config.extra_flags:
            adjustments["base_flags"].extend(self.config.extra_flags)

        # Wayland/X11 handling
        session_type = env_info.get("session_type", "unknown")
        if session_type == "wayland":
            adjustments["environment_flags"].extend(
                ["--ozone-platform=x11", "--disable-features=UseOzonePlatform"]
            )
            self.logger.info("launcher", "Wayland detected: forcing X11 via Ozone")

        # GPU-specific adjustments
        gpu_vendor = gpu_info.get("primary_gpu_vendor", "unknown")
        if gpu_vendor == "nvidia":
            if not gpu_info.get("nvidia_vaapi_available", False):
                adjustments["environment_flags"].extend(
                    ["--disable-gpu", "--disable-features=VaapiVideoDecoder"]
                )
                self.logger.warn(
                    "launcher", "NVIDIA VA-API driver not found - disabling GPU"
                )
                adjustments["warnings"].append("NVIDIA VA-API driver missing")

        # glibc version check
        glibc_version = env_info.get("glibc_version", "")
        if glibc_version and not glibc_version.startswith("2.4"):
            adjustments["warnings"].append(
                f"Potentially problematic glibc version: {glibc_version}"
            )

        return adjustments

    def apply_selinux_fix(self) -> bool:
        """Apply SELinux permissive rule for chrome_sandbox_t if needed"""
        if not self.config.enable_selinux_fix:
            return True

        try:
            # Check if SELinux is enforcing
            result = subprocess.run(
                ["getenforce"], capture_output=True, text=True, timeout=5
            )
            if result.returncode != 0 or result.stdout.strip() != "Enforcing":
                return True

            # Check if chrome_sandbox_t is already permissive
            result = subprocess.run(
                ["semanage", "permissive", "-l"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0 and "chrome_sandbox_t" in result.stdout:
                self.logger.debug("launcher", "chrome_sandbox_t already permissive")
                return True

            # Add permissive rule
            self.logger.info(
                "launcher", "Adding SELinux permissive rule for chrome_sandbox_t"
            )
            result = subprocess.run(
                ["sudo", "semanage", "permissive", "-a", "chrome_sandbox_t"],
                timeout=30,
                check=False,
            )

            if result.returncode == 0:
                self.logger.success(
                    "launcher", "SELinux permissive rule added successfully"
                )
                return True
            else:
                self.logger.warn("launcher", "Failed to add SELinux permissive rule")
                return False

        except (
            subprocess.TimeoutExpired,
            subprocess.CalledProcessError,
            FileNotFoundError,
        ) as e:
            self.logger.debug("launcher", f"SELinux fix not applicable or failed: {e}")
            return True  # Don't fail the entire process

    def launch_chrome_stage(
        self, stage: Dict[str, Any], env_adjustments: Dict[str, Any]
    ) -> Tuple[bool, Optional[subprocess.Popen]]:
        """Launch Chrome with specific stage configuration"""
        chrome_exe = self.config.get_chrome_executable()
        if not chrome_exe:
            self.logger.error("launcher", "No Chrome executable found")
            return False, None

        # Build command line
        cmd = [chrome_exe]
        cmd.extend(env_adjustments["base_flags"])
        cmd.extend(env_adjustments["environment_flags"])
        cmd.extend(stage["flags"])

        self.logger.info(
            "launcher",
            f"Launching Chrome - Stage: {stage['name']} ({stage['description']})",
        )
        self.logger.debug("launcher", f"Command: {' '.join(cmd)}")

        try:
            # Set dmesg marker before launch
            self.diagnostics.set_dmesg_marker()

            # Launch Chrome
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid,  # Create new process group
            )

            self.chrome_process = process
            self.current_stage = stage

            # Wait for stability check
            self.logger.info(
                "launcher",
                f"Waiting {self.config.launch_timeout}s for stability check...",
            )
            time.sleep(self.config.launch_timeout)

            # Check if process is still running
            if process.poll() is None:
                self.logger.success(
                    "launcher",
                    f"Chrome stable after {self.config.launch_timeout}s - SUCCESS!",
                )
                return True, process
            else:
                exit_code = process.poll()
                self.logger.error(
                    "launcher", f"Chrome crashed (exit code: {exit_code})"
                )
                return False, None

        except Exception as e:
            self.logger.error("launcher", f"Failed to launch Chrome: {e}")
            return False, None

    def cleanup_chrome_process(self) -> None:
        """Clean up Chrome process if running"""
        if self.chrome_process and self.chrome_process.poll() is None:
            try:
                # Try graceful termination first
                self.chrome_process.terminate()
                try:
                    self.chrome_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # Force kill if needed
                    self.chrome_process.kill()
                    self.chrome_process.wait()

                self.logger.debug("launcher", "Chrome process cleaned up")
            except Exception as e:
                self.logger.error("launcher", f"Error cleaning up Chrome process: {e}")

        self.chrome_process = None
        self.current_stage = None

    def launch_flatpak_fallback(self) -> bool:
        """Launch Flatpak Chromium as fallback"""
        if not self.config.enable_flatpak_fallback:
            self.logger.info("launcher", "Flatpak fallback disabled")
            return False

        self.logger.info("launcher", "Attempting Flatpak Chromium fallback")

        # Check if flatpak is available
        if not shutil.which("flatpak"):
            self.logger.error(
                "launcher", "Flatpak not installed - install with: dnf install flatpak"
            )
            return False

        try:
            # Check if Chromium is available
            result = subprocess.run(
                ["flatpak", "remote-info", "flathub", "org.chromium.Chromium"],
                capture_output=True,
                timeout=10,
                check=False,
            )

            if result.returncode != 0:
                self.logger.error(
                    "launcher", "Flathub unreachable or Chromium not available"
                )
                return False

            # Install/update Chromium
            self.logger.info("launcher", "Installing/updating Flatpak Chromium...")
            result = subprocess.run(
                [
                    "flatpak",
                    "install",
                    "-y",
                    "--or-update",
                    "--noninteractive",
                    "flathub",
                    "org.chromium.Chromium",
                ],
                timeout=300,
                check=False,
            )

            if result.returncode != 0:
                self.logger.error("launcher", "Failed to install Flatpak Chromium")
                return False

            # Launch Flatpak Chromium
            self.logger.success("launcher", "Launching Flatpak Chromium")
            os.execvp("flatpak", ["flatpak", "run", "org.chromium.Chromium"])

        except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as e:
            self.logger.error("launcher", f"Flatpak fallback failed: {e}")
            return False

        return True

    def run_troubleshooting_session(self) -> bool:
        """Run complete troubleshooting session with progressive fallbacks"""
        if not self.acquire_lock():
            return False

        try:
            self.logger.info(
                "launcher", "=== Chrome Troubleshooting Session Started ==="
            )

            # Detect environment and apply fixes
            env_adjustments = self.detect_environment()
            if env_adjustments["warnings"]:
                for warning in env_adjustments["warnings"]:
                    self.logger.warn("launcher", warning)

            # Apply SELinux fix if needed
            self.apply_selinux_fix()

            # Try each launch stage
            for i, stage in enumerate(self.launch_stages):
                if i >= self.config.max_attempts:
                    self.logger.warn(
                        "launcher",
                        f"Maximum attempts ({self.config.max_attempts}) reached",
                    )
                    break

                self.logger.info(
                    "launcher", f"=== Attempt {i+1}/{self.config.max_attempts} ==="
                )

                success, process = self.launch_chrome_stage(stage, env_adjustments)

                if success:
                    self.logger.success("launcher", "Chrome launched successfully!")
                    # Wait for Chrome to exit normally
                    if process:
                        try:
                            process.wait()
                        except KeyboardInterrupt:
                            self.logger.info("launcher", "Interrupted by user")
                            self.cleanup_chrome_process()
                    return True
                else:
                    # Collect diagnostics after failure
                    self.logger.info("launcher", "Collecting post-crash diagnostics...")
                    diagnostics = self.diagnostics.full_diagnostic_sweep(
                        self.config.journal_lines
                    )

                    # Log crash analysis
                    crash_analysis = diagnostics.get("crash_analysis", {})
                    if crash_analysis.get("patterns_found"):
                        for pattern in crash_analysis["patterns_found"]:
                            self.logger.warn("launcher", f"Detected: {pattern}")

                    # Clean up before next attempt
                    self.cleanup_chrome_process()

                    if i < len(self.launch_stages) - 1:
                        self.logger.info(
                            "launcher", "Proceeding to next fallback stage..."
                        )

            # All stages failed, try Flatpak fallback
            self.logger.warn("launcher", "All Chrome launch stages failed")
            if self.launch_flatpak_fallback():
                return True

            self.logger.error("launcher", "All troubleshooting attempts failed")
            return False

        except KeyboardInterrupt:
            self.logger.info("launcher", "Session interrupted by user")
            return False
        except Exception as e:
            self.logger.error(
                "launcher", f"Unexpected error in troubleshooting session: {e}"
            )
            return False
        finally:
            self.cleanup_chrome_process()
            self.release_lock()
            self.logger.info("launcher", "=== Chrome Troubleshooting Session Ended ===")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup_chrome_process()
        self.release_lock()
