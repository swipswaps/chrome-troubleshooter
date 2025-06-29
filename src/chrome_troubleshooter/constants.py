"""Pure constants — NO I/O, NO directory traversal."""

APP_NAME = "chrome-troubleshooter"
SESSION_FMT = "session_%Y-%m-%d_%H-%M-%S"

def ensure_cache_dir():
    """Create cache directory and return its Path."""
    from pathlib import Path
    cache_dir = Path("~/.cache/chrome-troubleshooter").expanduser()
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir

def get_cache_dir():
    """Get cache directory as Path object."""
    from pathlib import Path
    return Path("~/.cache/chrome-troubleshooter").expanduser()

__all__ = ["APP_NAME", "SESSION_FMT", "ensure_cache_dir", "get_cache_dir"]
