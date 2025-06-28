#!/usr/bin/env python3
"""
Tests for enhanced features and ChatGPT audit improvements
"""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from chrome_troubleshooter.utils import json_dumps, json_loads, format_size, format_duration
from chrome_troubleshooter.constants import CHROME_BINARIES, SESSION_FMT, LOCK_FILE


class TestEnhancedUtils:
    """Test enhanced utility functions."""
    
    def test_json_dumps_fallback(self):
        """Test JSON dumps with fallback to stdlib."""
        test_data = {"test": "data", "number": 42}
        
        # Should work regardless of orjson availability
        result = json_dumps(test_data)
        assert isinstance(result, str)
        assert "test" in result
        assert "42" in result
    
    def test_json_loads_fallback(self):
        """Test JSON loads with fallback to stdlib."""
        test_json = '{"test": "data", "number": 42}'
        
        # Should work regardless of orjson availability
        result = json_loads(test_json)
        assert isinstance(result, dict)
        assert result["test"] == "data"
        assert result["number"] == 42
    
    def test_format_size_various_sizes(self):
        """Test size formatting with various inputs."""
        assert format_size(0) == "0 B"
        assert format_size(512) == "512 B"
        assert format_size(1024) == "1.0 KB"
        assert format_size(1536) == "1.5 KB"
        assert format_size(1048576) == "1.0 MB"
        assert format_size(1073741824) == "1.0 GB"
        assert format_size(1099511627776) == "1.0 TB"
    
    def test_format_duration_various_times(self):
        """Test duration formatting with various inputs."""
        assert format_duration(0.5) == "0.5s"
        assert format_duration(30.0) == "30.0s"
        assert format_duration(90.0) == "1m 30s"
        assert format_duration(3661.0) == "1h 1m"
        assert format_duration(7322.0) == "2h 2m"


class TestEnhancedConstants:
    """Test enhanced constants."""
    
    def test_chrome_binaries_list(self):
        """Test Chrome binaries list is comprehensive."""
        assert isinstance(CHROME_BINARIES, list)
        assert len(CHROME_BINARIES) > 0
        assert "google-chrome" in CHROME_BINARIES
        assert "chromium" in CHROME_BINARIES
        
        # All should be valid binary names
        for binary in CHROME_BINARIES:
            assert isinstance(binary, str)
            assert len(binary) > 0
            assert not binary.startswith("/")  # Should be binary names, not paths
    
    def test_session_format(self):
        """Test session format string."""
        import time
        
        # Should be a valid strftime format
        formatted = time.strftime(SESSION_FMT)
        assert formatted.startswith("session_")
        assert len(formatted.split("_")) == 3  # session, date, time
        assert len(formatted) > 15  # Should be reasonably long
    
    def test_lock_file_path(self):
        """Test lock file path is reasonable."""
        assert isinstance(LOCK_FILE, str)
        assert LOCK_FILE.startswith("/tmp/")
        assert "chrome_troubleshooter" in LOCK_FILE
        assert LOCK_FILE.endswith(".lock")


class TestPerformanceFeatures:
    """Test performance-related features."""
    
    def test_orjson_import_handling(self):
        """Test that orjson import is handled gracefully."""
        # This should not raise an exception regardless of orjson availability
        try:
            from chrome_troubleshooter.utils import json_dumps, json_loads
            
            test_data = {"performance": "test", "numbers": [1, 2, 3]}
            serialized = json_dumps(test_data)
            deserialized = json_loads(serialized)
            
            assert deserialized == test_data
        except ImportError:
            pytest.fail("Utils should handle orjson import gracefully")
    
    def test_performance_constants(self):
        """Test performance-related constants."""
        from chrome_troubleshooter.constants import SIZE_LIMITS, TIMEOUTS
        
        # Size limits should be reasonable
        assert SIZE_LIMITS["max_log_file"] > 1024 * 1024  # At least 1MB
        assert SIZE_LIMITS["max_session_size"] > SIZE_LIMITS["max_log_file"]
        assert SIZE_LIMITS["max_total_cache"] > SIZE_LIMITS["max_session_size"]
        
        # Timeouts should be reasonable
        assert TIMEOUTS["chrome_launch"] > 0
        assert TIMEOUTS["diagnostics_collection"] > 0
        assert TIMEOUTS["log_collection"] > 0


class TestEnhancedCLI:
    """Test enhanced CLI features."""
    
    def test_utils_import(self):
        """Test that utils can be imported successfully."""
        from chrome_troubleshooter.utils import which_chrome, check_system_dependencies
        
        # Should be callable
        assert callable(which_chrome)
        assert callable(check_system_dependencies)
    
    def test_constants_import(self):
        """Test that constants can be imported successfully."""
        from chrome_troubleshooter.constants import CHROME_BINARIES, LOCK_FILE
        
        # Should have expected values
        assert isinstance(CHROME_BINARIES, list)
        assert isinstance(LOCK_FILE, str)


class TestJSONPerformance:
    """Test JSON performance features."""
    
    def test_json_performance_baseline(self):
        """Test JSON performance baseline."""
        import time
        
        # Create test data
        test_data = {
            "system_info": {"platform": "Linux", "version": "6.0.0"},
            "diagnostics": {"logs": ["log1", "log2"] * 100},
            "performance": {"metrics": list(range(1000))}
        }
        
        # Benchmark serialization
        start_time = time.perf_counter()
        for _ in range(10):
            result = json_dumps(test_data)
            parsed = json_loads(result)
        end_time = time.perf_counter()
        
        # Should complete in reasonable time (less than 1 second for 10 operations)
        total_time = end_time - start_time
        assert total_time < 1.0, f"JSON operations took too long: {total_time:.3f}s"
        
        # Should preserve data integrity
        assert parsed == test_data
