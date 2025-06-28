"""
🔧 CHROME TROUBLESHOOTER
Advanced Chrome crash diagnosis and auto-remediation tool for Linux systems
"""

__version__ = "1.0.0"
__author__ = "swipswaps"
__description__ = "Advanced Chrome crash diagnosis and auto-remediation tool"

# Import main classes for easy access
from .launcher import ChromeLauncher
from .diagnostics import DiagnosticsCollector
from .logger import StructuredLogger
from .config import Config

__all__ = [
    "ChromeLauncher",
    "DiagnosticsCollector",
    "StructuredLogger",
    "Config",
    "__version__",
]
