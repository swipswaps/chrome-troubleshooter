#!/usr/bin/env python3
"""
🔧 CHROME TROUBLESHOOTER - UTILITIES
Shared utility functions for Chrome troubleshooting
"""

import shutil
import sys
import subprocess
import os
import platform
import time
from pathlib import Path
from typing import Optional, List, Dict, Any

# Try to use orjson for faster JSON processing, fallback to standard json
try:
    import orjson

    def json_dumps(obj: Any) -> str:
        """Fast JSON serialization using orjson"""
        return orjson.dumps(obj).decode('utf-8')

    def json_loads(data: str) -> Any:
        """Fast JSON deserialization using orjson"""
        return orjson.loads(data)

except ImportError:
    import json

    def json_dumps(obj: Any) -> str:
        """Standard JSON serialization fallback"""
        return json.dumps(obj, default=str)

    def json_loads(data: str) -> Any:
        """Standard JSON deserialization fallback"""
        return json.loads(data)

from .constants import CHROME_BINARIES, CHROME_PATHS, SYSTEM_DEPS


def which_chrome() -> Optional[str]:
    """
    Locate a Chrome binary using PATH and common installation paths.
    
    Returns:
        Path to Chrome executable or None if not found
    """
    # First try PATH lookup
    for binary in CHROME_BINARIES:
        path = shutil.which(binary)
        if path:
            return path
    
    # Then try common installation paths
    for path in CHROME_PATHS:
        if Path(path).exists():
            return path
    
    return None


def run_command(
    cmd: List[str], 
    timeout: Optional[int] = None,
    capture_output: bool = True,
    check: bool = True,
    **kwargs
) -> subprocess.CompletedProcess:
    """
    Enhanced subprocess.run wrapper with better error handling.
    
    Args:
        cmd: Command and arguments as list
        timeout: Timeout in seconds
        capture_output: Whether to capture stdout/stderr
        check: Whether to raise on non-zero exit
        **kwargs: Additional arguments to subprocess.run
        
    Returns:
        CompletedProcess instance
        
    Raises:
        subprocess.CalledProcessError: If command fails and check=True
        subprocess.TimeoutExpired: If command times out
    """
    try:
        return subprocess.run(
            cmd,
            text=True,
            capture_output=capture_output,
            check=check,
            timeout=timeout,
            **kwargs
        )
    except subprocess.CalledProcessError as exc:
        if capture_output and exc.stderr:
            sys.stderr.write(f"Command failed: {' '.join(cmd)}\n")
            sys.stderr.write(exc.stderr)
        raise
    except subprocess.TimeoutExpired as exc:
        sys.stderr.write(f"Command timed out: {' '.join(cmd)}\n")
        raise


def check_system_dependencies() -> Dict[str, bool]:
    """
    Check availability of system dependencies.
    
    Returns:
        Dictionary mapping dependency names to availability status
    """
    deps = {}
    
    # Check Chrome
    deps["chrome"] = which_chrome() is not None
    
    # Check other system tools
    for dep in ["journalctl", "dmesg", "flock", "flatpak", "coredumpctl"]:
        deps[dep] = shutil.which(dep) is not None
    
    return deps


def get_system_info() -> Dict[str, Any]:
    """
    Collect basic system information.
    
    Returns:
        Dictionary with system information
    """
    info = {
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "python_version": platform.python_version(),
        "hostname": platform.node(),
    }
    
    # Add environment info
    info["session_type"] = os.environ.get("XDG_SESSION_TYPE", "unknown")
    info["desktop"] = os.environ.get("XDG_CURRENT_DESKTOP", "unknown")
    info["display"] = os.environ.get("DISPLAY", "unknown")
    info["wayland_display"] = os.environ.get("WAYLAND_DISPLAY", "unknown")
    
    # Add Chrome info if available
    chrome_path = which_chrome()
    if chrome_path:
        info["chrome_path"] = chrome_path
        try:
            result = run_command([chrome_path, "--version"], timeout=5)
            info["chrome_version"] = result.stdout.strip()
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            info["chrome_version"] = "unknown"
    
    return info


def detect_gpu_vendor() -> str:
    """
    Detect GPU vendor from system information.
    
    Returns:
        GPU vendor string (nvidia, amd, intel, or unknown)
    """
    try:
        # Try lspci first
        result = run_command(["lspci"], timeout=5)
        output = result.stdout.lower()
        
        if "nvidia" in output:
            return "nvidia"
        elif "amd" in output or "radeon" in output:
            return "amd"
        elif "intel" in output:
            return "intel"
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    # Try /proc/cpuinfo as fallback
    try:
        with open("/proc/cpuinfo", "r") as f:
            content = f.read().lower()
            if "intel" in content:
                return "intel"
    except (FileNotFoundError, PermissionError):
        pass
    
    return "unknown"


def get_selinux_status() -> str:
    """
    Get SELinux status.
    
    Returns:
        SELinux status string (enforcing, permissive, disabled, or unknown)
    """
    try:
        result = run_command(["getenforce"], timeout=5)
        return result.stdout.strip().lower()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return "unknown"


def get_glibc_version() -> str:
    """
    Get glibc version.
    
    Returns:
        glibc version string or unknown
    """
    try:
        result = run_command(["ldd", "--version"], timeout=5)
        lines = result.stdout.split("\n")
        if lines:
            # First line usually contains version info
            return lines[0].strip()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    return "unknown"


def format_size(size_bytes: int) -> str:
    """
    Format byte size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string (e.g., "1.5 MB")
    """
    if size_bytes == 0:
        return "0 B"
    
    units = ["B", "KB", "MB", "GB", "TB"]
    unit_index = 0
    size = float(size_bytes)
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"
    else:
        return f"{size:.1f} {units[unit_index]}"


def format_duration(seconds: float) -> str:
    """
    Format duration in human-readable format.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted duration string (e.g., "1m 30s")
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def ensure_directory(path: Path) -> Path:
    """
    Ensure directory exists, creating it if necessary.
    
    Args:
        path: Directory path
        
    Returns:
        The directory path
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


def cleanup_old_sessions(base_dir: Path, max_age_days: int = 7) -> int:
    """
    Clean up old session directories.
    
    Args:
        base_dir: Base directory containing sessions
        max_age_days: Maximum age in days
        
    Returns:
        Number of sessions cleaned up
    """
    if not base_dir.exists():
        return 0
    
    cutoff_time = time.time() - (max_age_days * 24 * 3600)
    cleaned = 0
    
    for session_dir in base_dir.glob("session_*"):
        if session_dir.is_dir():
            try:
                # Check modification time
                if session_dir.stat().st_mtime < cutoff_time:
                    import shutil
                    shutil.rmtree(session_dir)
                    cleaned += 1
            except (OSError, PermissionError):
                # Skip if we can't access or remove
                continue
    
    return cleaned


def is_process_running(pid: int) -> bool:
    """
    Check if a process is running.
    
    Args:
        pid: Process ID
        
    Returns:
        True if process is running, False otherwise
    """
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def get_chrome_processes() -> List[Dict[str, Any]]:
    """
    Get list of running Chrome processes.
    
    Returns:
        List of process information dictionaries
    """
    processes = []
    
    try:
        result = run_command(["pgrep", "-f", "chrome"], timeout=5)
        pids = [int(pid.strip()) for pid in result.stdout.split() if pid.strip()]
        
        for pid in pids:
            try:
                with open(f"/proc/{pid}/cmdline", "r") as f:
                    cmdline = f.read().replace("\0", " ").strip()
                
                processes.append({
                    "pid": pid,
                    "cmdline": cmdline,
                })
            except (FileNotFoundError, PermissionError):
                continue
                
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    return processes
