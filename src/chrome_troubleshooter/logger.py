#!/usr/bin/env python3
"""
🔧 CHROME TROUBLESHOOTER - STRUCTURED LOGGER
Advanced logging with JSON Lines, SQLite, and real-time terminal output
"""

import fcntl
import gzip
import shutil
import sqlite3
import sys
import threading
from contextlib import contextmanager, suppress
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

# Optimized JSON handling with orjson fallback (5-10x performance improvement)
try:
    import orjson as _json
    def dumps(obj: Any) -> str:
        """Fast JSON serialization with orjson"""
        return _json.dumps(obj).decode('utf-8')
    JSON_BACKEND = "orjson"
except ImportError:
    import json as _json
    def dumps(obj: Any) -> str:
        """Standard JSON serialization fallback"""
        return _json.dumps(obj, ensure_ascii=False)
    JSON_BACKEND = "json"

# Optional color support
try:
    import colorama
    from colorama import Fore, Style

    colorama.init(autoreset=True)
    HAS_COLORS = True
except ImportError:

    class MockColor:
        RED = GREEN = YELLOW = BLUE = MAGENTA = CYAN = WHITE = ""
        RESET_ALL = ""

    Fore = Style = MockColor()
    HAS_COLORS = False


class StructuredLogger:
    """Thread-safe structured logger with multiple output formats"""

    def __init__(
        self,
        session_dir: Path,
        enable_colors: bool = True,
        enable_sqlite: bool = True,
        enable_json: bool = True,
    ):
        self.session_dir = Path(session_dir)
        self.session_dir.mkdir(parents=True, exist_ok=True)

        self.enable_colors = enable_colors and HAS_COLORS
        self.enable_sqlite = enable_sqlite
        self.enable_json = enable_json

        # File paths
        self.log_file = self.session_dir / "launcher.log"
        self.json_file = self.session_dir / "logs.jsonl"
        self.db_file = self.session_dir / "logs.sqlite"

        # Thread safety
        self._lock = threading.Lock()
        self._db_connection = None

        # Initialize storage
        self._init_sqlite()
        self._init_json()

        # Auto-rotate old sessions (ChatGPT suggestion U4)
        self._rotate_old_sessions()

        # Session metadata
        self.session_start = datetime.now()
        self.log_count = 0

        self.info("logger", f"Session started: {self.session_start.isoformat()}")

    def _init_sqlite(self) -> None:
        """Initialize SQLite database with optimized settings"""
        if not self.enable_sqlite:
            return

        try:
            self._db_connection = sqlite3.connect(
                str(self.db_file), check_same_thread=False, timeout=30.0
            )

            # Optimize for concurrent writes and crash safety
            self._db_connection.executescript(
                """
                PRAGMA journal_mode=WAL;
                PRAGMA synchronous=NORMAL;
                PRAGMA cache_size=10000;
                PRAGMA temp_store=memory;

                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    level TEXT NOT NULL,
                    source TEXT NOT NULL,
                    content TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    metadata TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_logs_ts ON logs(ts);
                CREATE INDEX IF NOT EXISTS idx_logs_source ON logs(source);
                CREATE INDEX IF NOT EXISTS idx_logs_level ON logs(level);
                CREATE INDEX IF NOT EXISTS idx_logs_session ON logs(session_id);
            """
            )
            self._db_connection.commit()

        except sqlite3.Error as e:
            print(f"Warning: SQLite initialization failed: {e}", file=sys.stderr)
            # Try to recover by recreating the database
            if "no such column" in str(e).lower():
                self._recover_database()
            else:
                self.enable_sqlite = False

    def _recover_database(self) -> None:
        """
        Recover from database schema errors by recreating the database.

        CRITICAL FIX: Handles "no such column" errors from old database files.
        Following ChatGPT audit recommendation for graceful error recovery.
        """
        try:
            if self._db_connection:
                self._db_connection.close()

            # Backup old database if it exists
            if self.db_file.exists():
                backup_file = self.db_file.with_suffix('.db.backup')
                self.db_file.rename(backup_file)
                print(f"Warning: Backed up corrupted database to {backup_file}", file=sys.stderr)

            # Reinitialize with fresh database
            self._init_sqlite()

        except Exception as e:
            print(f"Warning: Database recovery failed: {e}", file=sys.stderr)
            self.enable_sqlite = False

    def _init_json(self) -> None:
        """Initialize JSON Lines file"""
        if not self.enable_json:
            return

        try:
            # Create file if it doesn't exist
            self.json_file.touch(exist_ok=True)
        except OSError as e:
            print(f"Warning: JSON file initialization failed: {e}", file=sys.stderr)
            self.enable_json = False

    def _rotate_old_sessions(self, max_age_days: int = 7, max_size_mb: int = 200) -> None:
        """Auto-rotate old sessions to prevent SSD bloat (ChatGPT suggestion U4)"""
        try:
            cache_dir = self.session_dir.parent
            if not cache_dir.exists():
                return

            cutoff_date = datetime.now() - timedelta(days=max_age_days)
            max_size_bytes = max_size_mb * 1024 * 1024

            for session_dir in cache_dir.glob("session_*"):
                if not session_dir.is_dir():
                    continue

                try:
                    # Check age
                    mtime = datetime.fromtimestamp(session_dir.stat().st_mtime)

                    # Check size
                    total_size = sum(f.stat().st_size for f in session_dir.rglob("*") if f.is_file())

                    if mtime < cutoff_date or total_size > max_size_bytes:
                        # Compress JSONL files before archiving
                        jsonl_file = session_dir / "logs.jsonl"
                        if jsonl_file.exists() and jsonl_file.stat().st_size > 1024:  # Only compress if > 1KB
                            with open(jsonl_file, 'rb') as f_in:
                                with gzip.open(f"{jsonl_file}.gz", 'wb') as f_out:
                                    shutil.copyfileobj(f_in, f_out)
                            jsonl_file.unlink()

                        # Create compressed archive
                        archive_name = f"{session_dir.name}.tar.gz"
                        archive_path = cache_dir / archive_name
                        shutil.make_archive(str(archive_path)[:-7], 'gztar', session_dir)

                        # Remove original directory
                        shutil.rmtree(session_dir, ignore_errors=True)

                        reason = "age" if mtime < cutoff_date else "size"
                        print(f"Rotated session {session_dir.name} ({reason}): {total_size:,} bytes -> {archive_path.name}")

                except (OSError, ValueError) as e:
                    print(f"Warning: Failed to rotate session {session_dir.name}: {e}", file=sys.stderr)

        except Exception as e:
            print(f"Warning: Session rotation failed: {e}", file=sys.stderr)

    def _get_timestamp(self) -> str:
        """Get ISO-8601 timestamp with timezone"""
        return datetime.now().astimezone().isoformat()

    def _colorize(self, text: str, level: str) -> str:
        """Apply color coding based on log level"""
        if not self.enable_colors:
            return text

        color_map = {
            "ERROR": Fore.RED,
            "WARN": Fore.YELLOW,
            "WARNING": Fore.YELLOW,
            "SUCCESS": Fore.GREEN,
            "INFO": Fore.CYAN,
            "DEBUG": Fore.MAGENTA,
        }

        color = color_map.get(level.upper(), "")
        return f"{color}{text}{Style.RESET_ALL}" if color else text

    def _write_to_sqlite(
        self,
        timestamp: str,
        level: str,
        source: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Write log entry to SQLite database"""
        if not self.enable_sqlite or not self._db_connection:
            return

        try:
            metadata_json = dumps(metadata) if metadata else None
            session_id = self.session_start.isoformat()

            self._db_connection.execute(
                "INSERT INTO logs (ts, level, source, content, session_id, metadata) VALUES (?, ?, ?, ?, ?, ?)",
                (timestamp, level, source, content, session_id, metadata_json),
            )
            self._db_connection.commit()

        except sqlite3.Error as e:
            print(f"SQLite write error: {e}", file=sys.stderr)

    def _write_to_json(
        self,
        timestamp: str,
        level: str,
        source: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Write log entry to JSON Lines file"""
        if not self.enable_json:
            return

        try:
            log_entry = {
                "ts": timestamp,
                "level": level,
                "source": source,
                "content": content,
                "session_id": self.session_start.isoformat(),
            }

            if metadata:
                log_entry["metadata"] = metadata

            with open(self.json_file, "a", encoding="utf-8") as f:
                # Use file locking for concurrent access
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    f.write(dumps(log_entry) + "\n")
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)

        except (OSError, Exception) as e:
            print(f"JSON write error: {e}", file=sys.stderr)

    def _write_to_terminal(
        self, timestamp: str, level: str, source: str, content: str
    ) -> None:
        """Write log entry to terminal and text log file"""
        formatted_msg = f"[{timestamp}][{level}][{source}] {content}"
        colored_msg = self._colorize(formatted_msg, level)

        # Write to terminal
        print(colored_msg, flush=True)

        # Write to text log file
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    f.write(formatted_msg + "\n")
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except OSError as e:
            print(f"Text log write error: {e}", file=sys.stderr)

    def log(
        self,
        level: str,
        source: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Write a log entry to all configured outputs"""
        with self._lock:
            timestamp = self._get_timestamp()
            self.log_count += 1

            # Write to all outputs
            self._write_to_terminal(timestamp, level, source, content)
            self._write_to_sqlite(timestamp, level, source, content, metadata)
            self._write_to_json(timestamp, level, source, content, metadata)

    def debug(
        self, source: str, content: str, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log debug message"""
        self.log("DEBUG", source, content, metadata)

    def info(
        self, source: str, content: str, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log info message"""
        self.log("INFO", source, content, metadata)

    def warn(
        self, source: str, content: str, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log warning message"""
        self.log("WARN", source, content, metadata)

    def warning(
        self, source: str, content: str, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log warning message (alias)"""
        self.warn(source, content, metadata)

    def error(
        self, source: str, content: str, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log error message"""
        self.log("ERROR", source, content, metadata)

    def success(
        self, source: str, content: str, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log success message"""
        self.log("SUCCESS", source, content, metadata)

    def add(
        self, source: str, content: str, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Add log entry (alias for info method).

        CRITICAL FIX: This method was missing, causing AttributeError in diagnostics.
        Following ChatGPT audit recommendation to provide backward compatibility.

        Args:
            source: Source component/module name
            content: Log message content
            metadata: Optional structured metadata
        """
        self.info(source, content, metadata)

    def close(self) -> None:
        """Close all resources"""
        with self._lock:
            if self._db_connection:
                with suppress(sqlite3.Error):
                    self._db_connection.close()
                self._db_connection = None

            self.info("logger", f"Session ended: {datetime.now().isoformat()}")
            self.info("logger", f"Total log entries: {self.log_count}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    @contextmanager
    def capture_output(self, source: str, level: str = "INFO"):
        """Context manager to capture stdout/stderr to logs"""

        class LogCapture:
            def __init__(self, logger, source, level):
                self.logger = logger
                self.source = source
                self.level = level
                self.buffer = []

            def write(self, text):
                if text.strip():
                    self.logger.log(self.level, self.source, text.strip())
                return len(text)

            def flush(self):
                pass

        capture = LogCapture(self, source, level)
        old_stdout = sys.stdout
        old_stderr = sys.stderr

        try:
            sys.stdout = capture
            sys.stderr = capture
            yield capture
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

    def get_stats(self) -> Dict[str, Any]:
        """Get logging statistics"""
        stats = {
            "session_start": self.session_start.isoformat(),
            "log_count": self.log_count,
            "sqlite_enabled": self.enable_sqlite,
            "json_enabled": self.enable_json,
            "json_backend": JSON_BACKEND,  # Show orjson vs json performance
            "colors_enabled": self.enable_colors,
            "files": {
                "log_file": str(self.log_file),
                "json_file": str(self.json_file),
                "db_file": str(self.db_file),
            },
        }

        # Add file sizes if they exist
        for key, path in stats["files"].items():
            if not key.endswith("_size"):  # Skip size entries
                path_obj = Path(path)
                if path_obj.exists():
                    stats["files"][f"{key}_size"] = path_obj.stat().st_size

        return stats
