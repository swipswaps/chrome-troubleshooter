#!/usr/bin/env python3
"""
🔧 CHROME TROUBLESHOOTER - DIAGNOSTICS COLLECTOR
Comprehensive system diagnostics and log collection for Chrome troubleshooting
"""

import os
import re
import subprocess
import time
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import shutil
import glob

from .logger import StructuredLogger


class DiagnosticsCollector:
    """Collects comprehensive diagnostics for Chrome troubleshooting"""

    def __init__(self, logger: StructuredLogger):
        self.logger = logger
        self.dmesg_marker = None
        self.start_time = datetime.now()

        # Chrome-related paths
        self.chrome_config_dirs = [
            Path.home() / ".config" / "google-chrome",
            Path.home() / ".config" / "chromium",
            Path.home() / ".config" / "google-chrome-beta",
            Path.home() / ".config" / "google-chrome-unstable",
        ]

        # System info cache
        self._system_info = None
        self._gpu_info = None

    def set_dmesg_marker(self) -> None:
        """Set timestamp marker for dmesg delta collection"""
        self.dmesg_marker = int(time.time())
        self.logger.debug("diagnostics", f"dmesg marker set: {self.dmesg_marker}")

    def get_system_info(self) -> Dict[str, Any]:
        """Collect comprehensive system information"""
        if self._system_info is not None:
            return self._system_info

        info = {}

        try:
            # Session type
            info["session_type"] = os.environ.get("XDG_SESSION_TYPE", "unknown")
            info["desktop"] = os.environ.get("XDG_CURRENT_DESKTOP", "unknown")
            info["wayland_display"] = os.environ.get("WAYLAND_DISPLAY", "")
            info["display"] = os.environ.get("DISPLAY", "")

            # Distribution info
            if Path("/etc/os-release").exists():
                with open("/etc/os-release") as f:
                    for line in f:
                        if "=" in line:
                            key, value = line.strip().split("=", 1)
                            info[f"os_{key.lower()}"] = value.strip('"')

            # Kernel info
            info["kernel"] = self._run_command(["uname", "-r"], capture=True)
            info["architecture"] = self._run_command(["uname", "-m"], capture=True)

            # glibc version
            try:
                glibc_output = self._run_command(
                    ["rpm", "-q", "--qf", "%{VERSION}", "glibc"], capture=True
                )
                info["glibc_version"] = glibc_output.strip()
            except:
                info["glibc_version"] = "unknown"

            # Memory info
            if Path("/proc/meminfo").exists():
                with open("/proc/meminfo") as f:
                    for line in f:
                        if line.startswith(
                            ("MemTotal:", "MemAvailable:", "SwapTotal:")
                        ):
                            key, value = line.split(":", 1)
                            info[f"memory_{key.lower()}"] = value.strip()

            # SELinux status
            try:
                selinux_status = self._run_command(["getenforce"], capture=True)
                info["selinux_status"] = selinux_status.strip()
            except:
                info["selinux_status"] = "unknown"

        except Exception as e:
            self.logger.error("diagnostics", f"Error collecting system info: {e}")

        self._system_info = info
        return info

    def get_gpu_info(self) -> Dict[str, Any]:
        """Collect GPU and graphics information"""
        if self._gpu_info is not None:
            return self._gpu_info

        info = {}

        try:
            # PCI GPU devices
            lspci_output = self._run_command(["lspci", "-nn"], capture=True)
            gpu_lines = [
                line
                for line in lspci_output.split("\n")
                if re.search(r"VGA|3D|Display", line, re.IGNORECASE)
            ]
            info["gpu_devices"] = gpu_lines

            # Primary GPU vendor detection
            if gpu_lines:
                first_gpu = gpu_lines[0].lower()
                if "nvidia" in first_gpu:
                    info["primary_gpu_vendor"] = "nvidia"
                elif "amd" in first_gpu or "ati" in first_gpu:
                    info["primary_gpu_vendor"] = "amd"
                elif "intel" in first_gpu:
                    info["primary_gpu_vendor"] = "intel"
                else:
                    info["primary_gpu_vendor"] = "unknown"

            # VA-API info
            try:
                vainfo_output = self._run_command(["vainfo"], capture=True)
                info["vaapi_available"] = "VA-API version" in vainfo_output
                info["vaapi_output"] = vainfo_output
            except:
                info["vaapi_available"] = False
                info["vaapi_output"] = "vainfo command failed"

            # OpenGL info
            try:
                glxinfo_output = self._run_command(["glxinfo", "-B"], capture=True)
                info["opengl_available"] = True
                info["opengl_info"] = glxinfo_output
            except:
                info["opengl_available"] = False
                info["opengl_info"] = "glxinfo command failed"

            # NVIDIA-specific checks
            if info.get("primary_gpu_vendor") == "nvidia":
                try:
                    # Check for nvidia-vaapi driver
                    ldconfig_output = self._run_command(
                        ["ldconfig", "-p"], capture=True
                    )
                    info["nvidia_vaapi_available"] = (
                        "nvidia-vaapi" in ldconfig_output.lower()
                    )
                except:
                    info["nvidia_vaapi_available"] = False

                try:
                    # NVIDIA driver version
                    nvidia_smi = self._run_command(
                        [
                            "nvidia-smi",
                            "--query-gpu=driver_version",
                            "--format=csv,noheader",
                        ],
                        capture=True,
                    )
                    info["nvidia_driver_version"] = nvidia_smi.strip()
                except:
                    info["nvidia_driver_version"] = "unknown"

        except Exception as e:
            self.logger.error("diagnostics", f"Error collecting GPU info: {e}")

        self._gpu_info = info
        return info

    def collect_chrome_debug_logs(self) -> List[str]:
        """Collect Chrome debug logs from standard locations"""
        logs = []

        for config_dir in self.chrome_config_dirs:
            debug_log = config_dir / "chrome_debug.log"
            if debug_log.exists():
                try:
                    with open(debug_log, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        if content.strip():
                            logs.append(f"=== {debug_log} ===")
                            logs.extend(content.strip().split("\n"))
                            self.logger.info(
                                "diagnostics", f"Collected debug log: {debug_log}"
                            )
                except Exception as e:
                    self.logger.error("diagnostics", f"Error reading {debug_log}: {e}")

        return logs

    def collect_crashpad_dumps(self) -> List[Dict[str, Any]]:
        """Collect Crashpad dump information"""
        dumps = []

        for config_dir in self.chrome_config_dirs:
            # Look for crash reports in various subdirectories
            crash_dirs = [
                config_dir / "Crash Reports",
                config_dir / "Crashpad",
                config_dir / "crashes",
            ]

            for crash_dir in crash_dirs:
                if crash_dir.exists():
                    # Find .dmp files
                    for dmp_file in crash_dir.rglob("*.dmp"):
                        try:
                            stat = dmp_file.stat()
                            # Only include recent dumps (last 24 hours)
                            if datetime.fromtimestamp(
                                stat.st_mtime
                            ) > datetime.now() - timedelta(days=1):
                                dump_info = {
                                    "path": str(dmp_file),
                                    "size": stat.st_size,
                                    "mtime": datetime.fromtimestamp(
                                        stat.st_mtime
                                    ).isoformat(),
                                    "header": self._get_dump_header(dmp_file),
                                }
                                dumps.append(dump_info)
                                self.logger.info(
                                    "diagnostics", f"Found crash dump: {dmp_file}"
                                )
                        except Exception as e:
                            self.logger.error(
                                "diagnostics", f"Error processing dump {dmp_file}: {e}"
                            )

        return dumps

    def _get_dump_header(self, dump_file: Path) -> str:
        """Extract header information from crash dump"""
        try:
            with open(dump_file, "rb") as f:
                header = f.read(80)  # Read first 80 bytes
                # Convert to hex representation
                return header.hex()[:160]  # Limit to reasonable length
        except Exception:
            return "unable_to_read"

    def collect_journal_logs(self, lines: int = 200) -> Dict[str, List[str]]:
        """Collect systemd journal logs related to Chrome"""
        logs = {"user_journal": [], "system_journal": []}

        try:
            # User journal
            user_output = self._run_command(
                [
                    "journalctl",
                    "--user",
                    "-n",
                    str(lines),
                    "--no-pager",
                    "_COMM=chrome",
                ],
                capture=True,
            )
            if user_output.strip():
                logs["user_journal"] = user_output.strip().split("\n")
                self.logger.info(
                    "diagnostics",
                    f"Collected {len(logs['user_journal'])} user journal entries",
                )

            # System journal
            system_output = self._run_command(
                ["journalctl", "-n", str(lines), "--no-pager", "_COMM=chrome"],
                capture=True,
            )
            if system_output.strip():
                logs["system_journal"] = system_output.strip().split("\n")
                self.logger.info(
                    "diagnostics",
                    f"Collected {len(logs['system_journal'])} system journal entries",
                )

        except Exception as e:
            self.logger.error("diagnostics", f"Error collecting journal logs: {e}")

        return logs

    def collect_dmesg_delta(self) -> List[str]:
        """Collect new dmesg entries since marker"""
        if self.dmesg_marker is None:
            self.logger.warn(
                "diagnostics", "No dmesg marker set, collecting recent entries"
            )
            return self.collect_recent_dmesg()

        try:
            dmesg_output = self._run_command(
                ["dmesg", "--since", f"@{self.dmesg_marker}", "--time-format", "iso"],
                capture=True,
            )

            if not dmesg_output.strip():
                return []

            # Filter for Chrome-related entries
            chrome_lines = []
            for line in dmesg_output.split("\n"):
                if re.search(
                    r"chrome|chromium|gpu|i915|amdgpu|nvidia|seccomp|oom|segfault|vaapi",
                    line,
                    re.IGNORECASE,
                ):
                    chrome_lines.append(line)

            if chrome_lines:
                self.logger.info(
                    "diagnostics",
                    f"Collected {len(chrome_lines)} dmesg entries since marker",
                )

            return chrome_lines

        except Exception as e:
            self.logger.error("diagnostics", f"Error collecting dmesg delta: {e}")
            return []

    def collect_recent_dmesg(self, minutes: int = 10) -> List[str]:
        """Collect recent dmesg entries"""
        try:
            since_time = datetime.now() - timedelta(minutes=minutes)
            dmesg_output = self._run_command(
                [
                    "dmesg",
                    "--since",
                    since_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "--time-format",
                    "iso",
                ],
                capture=True,
            )

            if not dmesg_output.strip():
                return []

            # Filter for relevant entries
            relevant_lines = []
            for line in dmesg_output.split("\n"):
                if re.search(
                    r"chrome|chromium|gpu|i915|amdgpu|nvidia|seccomp|oom|segfault|vaapi",
                    line,
                    re.IGNORECASE,
                ):
                    relevant_lines.append(line)

            return relevant_lines

        except Exception as e:
            self.logger.error("diagnostics", f"Error collecting recent dmesg: {e}")
            return []

    def collect_coredump_info(self) -> List[Dict[str, Any]]:
        """Collect coredump information for Chrome processes"""
        coredumps = []

        try:
            # List recent Chrome coredumps
            coredump_output = self._run_command(
                ["coredumpctl", "list", "google-chrome", "--no-pager"], capture=True
            )

            if not coredump_output.strip():
                return coredumps

            # Parse coredumpctl output
            lines = coredump_output.strip().split("\n")
            for line in lines[1:]:  # Skip header
                parts = line.split()
                if len(parts) >= 5:
                    coredump_info = {
                        "timestamp": parts[0] + " " + parts[1],
                        "pid": parts[2],
                        "uid": parts[3],
                        "gid": parts[4],
                        "signal": parts[5] if len(parts) > 5 else "unknown",
                        "executable": (
                            " ".join(parts[6:]) if len(parts) > 6 else "unknown"
                        ),
                    }
                    coredumps.append(coredump_info)

            self.logger.info("diagnostics", f"Found {len(coredumps)} Chrome coredumps")

        except Exception as e:
            self.logger.error("diagnostics", f"Error collecting coredump info: {e}")

        return coredumps

    def collect_abrt_reports(self) -> List[Dict[str, Any]]:
        """Collect ABRT crash reports"""
        reports = []

        try:
            abrt_output = self._run_command(
                ["abrt-cli", "list", "--since", "-1day"], capture=True
            )

            if abrt_output.strip():
                # Parse ABRT output (format varies)
                for line in abrt_output.strip().split("\n"):
                    if "chrome" in line.lower():
                        reports.append({"raw": line})

                self.logger.info("diagnostics", f"Found {len(reports)} ABRT reports")

        except Exception as e:
            self.logger.debug("diagnostics", f"ABRT not available or error: {e}")

        return reports

    def collect_selinux_denials(self) -> List[str]:
        """Collect SELinux AVC denials related to Chrome"""
        denials = []

        try:
            # Search for recent AVC denials
            ausearch_output = self._run_command(
                ["ausearch", "-m", "avc", "-ts", "recent"],
                capture=True,
                require_sudo=True,
            )

            if ausearch_output.strip():
                for line in ausearch_output.split("\n"):
                    if "chrome" in line.lower():
                        denials.append(line)

                self.logger.info("diagnostics", f"Found {len(denials)} SELinux denials")

        except Exception as e:
            self.logger.debug("diagnostics", f"SELinux audit search failed: {e}")

        return denials

    def analyze_crash_patterns(self, dmesg_lines: List[str]) -> Dict[str, Any]:
        """Analyze crash patterns from dmesg and other logs"""
        analysis = {
            "seccomp_issues": False,
            "gpu_hangs": False,
            "oom_kills": False,
            "segfaults": False,
            "vaapi_errors": False,
            "wayland_issues": False,
            "patterns_found": [],
        }

        # Pattern matching
        patterns = {
            "seccomp_issues": [
                r"seccomp.*chrome",
                r"chrome.*seccomp",
                r"SECCOMP.*chrome",
            ],
            "gpu_hangs": [
                r"i915.*hang",
                r"amdgpu.*hang",
                r"gpu.*hang",
                r"ring.*timeout",
            ],
            "oom_kills": [r"oom-killer.*chrome", r"chrome.*killed.*memory"],
            "segfaults": [r"chrome.*segfault", r"chrome.*SIGSEGV"],
            "vaapi_errors": [r"vaapi.*error", r"va-api.*fail"],
            "wayland_issues": [r"wayland.*chrome.*error", r"chrome.*wayland.*fail"],
        }

        all_text = "\n".join(dmesg_lines).lower()

        for issue_type, pattern_list in patterns.items():
            for pattern in pattern_list:
                if re.search(pattern, all_text, re.IGNORECASE):
                    analysis[issue_type] = True
                    analysis["patterns_found"].append(f"{issue_type}: {pattern}")
                    break

        return analysis

    def _run_command(
        self,
        cmd: List[str],
        capture: bool = False,
        require_sudo: bool = False,
        timeout: int = 30,
    ) -> str:
        """Run system command with error handling"""
        try:
            if require_sudo and os.getuid() != 0:
                cmd = ["sudo"] + cmd

            if capture:
                result = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=timeout, check=False
                )
                return result.stdout
            else:
                subprocess.run(cmd, timeout=timeout, check=True)
                return ""

        except subprocess.TimeoutExpired:
            self.logger.error("diagnostics", f"Command timeout: {' '.join(cmd)}")
            return ""
        except subprocess.CalledProcessError as e:
            self.logger.debug(
                "diagnostics",
                f"Command failed: {' '.join(cmd)} (exit code: {e.returncode})",
            )
            return ""
        except FileNotFoundError:
            self.logger.debug("diagnostics", f"Command not found: {cmd[0]}")
            return ""
        except Exception as e:
            self.logger.error("diagnostics", f"Command error: {' '.join(cmd)} - {e}")
            return ""

    def full_diagnostic_sweep(self, journal_lines: int = 200) -> Dict[str, Any]:
        """Perform comprehensive diagnostic collection"""
        self.logger.info("diagnostics", "Starting full diagnostic sweep")

        diagnostics = {
            "timestamp": datetime.now().isoformat(),
            "system_info": self.get_system_info(),
            "gpu_info": self.get_gpu_info(),
            "chrome_debug_logs": self.collect_chrome_debug_logs(),
            "crashpad_dumps": self.collect_crashpad_dumps(),
            "journal_logs": self.collect_journal_logs(journal_lines),
            "dmesg_delta": self.collect_dmesg_delta(),
            "coredump_info": self.collect_coredump_info(),
            "abrt_reports": self.collect_abrt_reports(),
            "selinux_denials": self.collect_selinux_denials(),
        }

        # Analyze patterns
        all_dmesg = diagnostics["dmesg_delta"]
        diagnostics["crash_analysis"] = self.analyze_crash_patterns(all_dmesg)

        # Log summary
        total_entries = sum(
            len(v) if isinstance(v, list) else 0 for v in diagnostics.values()
        )
        self.logger.info(
            "diagnostics", f"Diagnostic sweep complete: {total_entries} total entries"
        )

        return diagnostics
