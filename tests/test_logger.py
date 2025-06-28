#!/usr/bin/env python3
"""
Tests for chrome_troubleshooter.logger module
"""

import json
import sqlite3
import tempfile
import threading
import time
from pathlib import Path
import pytest

from chrome_troubleshooter.logger import StructuredLogger


class TestStructuredLogger:
    """Test structured logging functionality"""

    def test_logger_initialization(self):
        """Test logger initialization with different configurations"""
        with tempfile.TemporaryDirectory() as temp_dir:
            session_dir = Path(temp_dir)

            # Test with all features enabled
            logger = StructuredLogger(
                session_dir, enable_colors=True, enable_sqlite=True, enable_json=True
            )

            assert logger.session_dir == session_dir
            assert logger.enable_colors is True
            assert logger.enable_sqlite is True
            assert logger.enable_json is True
            assert logger.log_file.exists()
            assert logger.json_file.exists()
            assert logger.db_file.exists()

            logger.close()

    def test_sqlite_logging(self):
        """Test SQLite database logging"""
        with tempfile.TemporaryDirectory() as temp_dir:
            session_dir = Path(temp_dir)

            with StructuredLogger(
                session_dir, enable_sqlite=True, enable_json=False
            ) as logger:
                logger.info("test", "Test message")
                logger.error("test", "Error message")
                logger.warn("test", "Warning message")

            # Verify SQLite database
            conn = sqlite3.connect(str(logger.db_file))
            cursor = conn.cursor()

            cursor.execute("SELECT level, source, content FROM logs ORDER BY id")
            rows = cursor.fetchall()

            assert len(rows) >= 3  # At least our 3 messages plus session start

            # Find our test messages
            test_messages = [row for row in rows if row[1] == "test"]
            assert len(test_messages) == 3

            levels = [row[0] for row in test_messages]
            assert "INFO" in levels
            assert "ERROR" in levels
            assert "WARN" in levels

            conn.close()

    def test_json_logging(self):
        """Test JSON Lines logging"""
        with tempfile.TemporaryDirectory() as temp_dir:
            session_dir = Path(temp_dir)

            with StructuredLogger(
                session_dir, enable_sqlite=False, enable_json=True
            ) as logger:
                logger.info("test", "Test message", {"key": "value"})
                logger.error("test", "Error message")

            # Verify JSON Lines file
            with open(logger.json_file, "r") as f:
                lines = f.readlines()

            # Should have at least session start + our 2 messages
            assert len(lines) >= 3

            # Parse JSON lines
            json_entries = []
            for line in lines:
                if line.strip():
                    entry = json.loads(line)
                    json_entries.append(entry)

            # Find our test messages
            test_entries = [
                entry for entry in json_entries if entry.get("source") == "test"
            ]
            assert len(test_entries) == 2

            # Check metadata
            info_entry = next(
                entry for entry in test_entries if entry["level"] == "INFO"
            )
            assert info_entry["metadata"] == {"key": "value"}

    def test_text_logging(self):
        """Test text file logging"""
        with tempfile.TemporaryDirectory() as temp_dir:
            session_dir = Path(temp_dir)

            with StructuredLogger(
                session_dir, enable_sqlite=False, enable_json=False
            ) as logger:
                logger.info("test", "Test message")
                logger.error("test", "Error message")

            # Verify text log file
            with open(logger.log_file, "r") as f:
                content = f.read()

            assert "Test message" in content
            assert "Error message" in content
            assert "[INFO][test]" in content
            assert "[ERROR][test]" in content

    def test_thread_safety(self):
        """Test thread-safe logging"""
        with tempfile.TemporaryDirectory() as temp_dir:
            session_dir = Path(temp_dir)

            with StructuredLogger(session_dir) as logger:

                def log_worker(worker_id):
                    for i in range(10):
                        logger.info(f"worker_{worker_id}", f"Message {i}")
                        time.sleep(0.001)  # Small delay to encourage race conditions

                # Start multiple threads
                threads = []
                for worker_id in range(5):
                    thread = threading.Thread(target=log_worker, args=(worker_id,))
                    threads.append(thread)
                    thread.start()

                # Wait for all threads to complete
                for thread in threads:
                    thread.join()

            # Verify all messages were logged
            conn = sqlite3.connect(str(logger.db_file))
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM logs WHERE source LIKE 'worker_%'")
            count = cursor.fetchone()[0]

            assert count == 50  # 5 workers * 10 messages each

            conn.close()

    def test_log_level_methods(self):
        """Test different log level methods"""
        with tempfile.TemporaryDirectory() as temp_dir:
            session_dir = Path(temp_dir)

            with StructuredLogger(session_dir) as logger:
                logger.debug("test", "Debug message")
                logger.info("test", "Info message")
                logger.warn("test", "Warning message")
                logger.warning("test", "Warning message 2")  # Alias test
                logger.error("test", "Error message")
                logger.success("test", "Success message")

            # Verify all levels were logged
            conn = sqlite3.connect(str(logger.db_file))
            cursor = conn.cursor()

            cursor.execute("SELECT DISTINCT level FROM logs WHERE source = 'test'")
            levels = [row[0] for row in cursor.fetchall()]

            expected_levels = ["DEBUG", "INFO", "WARN", "ERROR", "SUCCESS"]
            for level in expected_levels:
                assert level in levels

            conn.close()

    def test_capture_output(self):
        """Test output capture context manager"""
        with tempfile.TemporaryDirectory() as temp_dir:
            session_dir = Path(temp_dir)

            with StructuredLogger(session_dir) as logger:
                with logger.capture_output("stdout_test"):
                    print("This should be captured")
                    print("Another line")

            # Verify captured output was logged
            conn = sqlite3.connect(str(logger.db_file))
            cursor = conn.cursor()

            cursor.execute("SELECT content FROM logs WHERE source = 'stdout_test'")
            captured_lines = [row[0] for row in cursor.fetchall()]

            assert "This should be captured" in captured_lines
            assert "Another line" in captured_lines

            conn.close()

    def test_get_stats(self):
        """Test logging statistics"""
        with tempfile.TemporaryDirectory() as temp_dir:
            session_dir = Path(temp_dir)

            with StructuredLogger(session_dir) as logger:
                logger.info("test", "Message 1")
                logger.info("test", "Message 2")
                logger.error("test", "Error message")

                stats = logger.get_stats()

                assert stats["log_count"] >= 4  # 3 our messages + session start
                assert stats["sqlite_enabled"] is True
                assert stats["json_enabled"] is True
                assert "session_start" in stats
                assert "files" in stats

                # Check file paths
                files = stats["files"]
                assert "log_file" in files
                assert "json_file" in files
                assert "db_file" in files

    def test_disabled_features(self):
        """Test logger with disabled features"""
        with tempfile.TemporaryDirectory() as temp_dir:
            session_dir = Path(temp_dir)

            # Disable all storage features
            logger = StructuredLogger(
                session_dir, enable_colors=False, enable_sqlite=False, enable_json=False
            )

            logger.info("test", "Test message")
            logger.close()

            # Only text log should exist
            assert logger.log_file.exists()
            assert not logger.db_file.exists() or logger.db_file.stat().st_size == 0
            assert not logger.json_file.exists() or logger.json_file.stat().st_size == 0

    def test_error_handling(self):
        """Test error handling in logging operations"""
        with tempfile.TemporaryDirectory() as temp_dir:
            session_dir = Path(temp_dir)

            with StructuredLogger(session_dir) as logger:
                # Test with invalid metadata (should not crash)
                class UnserializableObject:
                    def __str__(self):
                        raise Exception("Cannot serialize")

                # This should not raise an exception
                logger.info(
                    "test",
                    "Message with problematic metadata",
                    {"bad_object": UnserializableObject()},
                )

                # Logger should still be functional
                logger.info("test", "Normal message after error")

            # Verify normal operation continued
            with open(logger.log_file, "r") as f:
                content = f.read()

            assert "Normal message after error" in content


if __name__ == "__main__":
    pytest.main([__file__])
