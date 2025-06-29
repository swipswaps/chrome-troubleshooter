"""
🔧 CHROME TROUBLESHOOTER
Advanced Chrome crash diagnosis and auto-remediation tool for Linux systems
"""

# VERSION SYNC: Keep in sync with pyproject.toml
# Following ChatGPT audit suggestion U-P1 for version consistency
__version__ = "0.2.0b0"
__author__ = "swipswaps"
__description__ = "Advanced Chrome crash diagnosis and auto-remediation tool"

# AUDIT-COMPLIANT IMPORTS: Updated to match consolidated module interface
# Following ChatGPT audit suggestion U-C1 for Single Source of Truth
# The audit version uses functions rather than classes for simplicity
#
# IMPORT STRATEGY EXPLANATION:
# - Import only the essential public interface
# - Avoid importing everything to prevent circular dependencies
# - Match the actual implementation (functions vs classes)
# - Keep __all__ minimal to reduce API surface area
from .launcher import safe_launch
from .diagnostics import collect_all
from .logger import StructuredLogger
from .constants import CACHE_DIR

__all__ = [
    "safe_launch",      # Main launcher function
    "collect_all",      # Diagnostics collection function
    "StructuredLogger", # Logger class (enhanced with orjson)
    "CACHE_DIR",        # Cache directory constant
    "__version__",      # Version string
]
