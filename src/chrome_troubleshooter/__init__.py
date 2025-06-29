"""
🔧 CHROME TROUBLESHOOTER
Advanced Chrome crash diagnosis and auto-remediation tool for Linux systems
"""

# VERSION SYNC: Keep in sync with pyproject.toml
# Following ChatGPT audit suggestion U-P1 for version consistency
__version__ = "0.2.0b0"
__author__ = "swipswaps"
__description__ = "Advanced Chrome crash diagnosis and auto-remediation tool"

# CIRCULAR DEPENDENCY FIX: NO imports to prevent import loops
# Following ChatGPT audit recommendation for zero-dependency __init__.py
#
# CRITICAL FIX: Removed ALL imports that cause circular dependencies
# Users should import specific modules directly:
# - from chrome_troubleshooter.constants import get_cache_dir
# - from chrome_troubleshooter.launcher import safe_launch
# - from chrome_troubleshooter.logger import StructuredLogger
#
# IMPORT STRATEGY EXPLANATION:
# - Import NOTHING to prevent any circular dependencies
# - Keep __all__ empty to force explicit imports
# - This ensures fast, reliable imports for IDEs and tools
# No imports here - users import modules directly

__all__ = [
    "__version__",      # Version string
    # Note: All other imports removed to prevent circular dependencies
    # Users should import modules directly:
    # from chrome_troubleshooter.constants import get_cache_dir
    # from chrome_troubleshooter.launcher import safe_launch
    # from chrome_troubleshooter.logger import StructuredLogger
]
