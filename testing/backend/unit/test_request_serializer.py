"""
Tests for request_serializer module.
"""
import pytest
import sys
from datetime import datetime
from unittest.mock import patch

sys_path_backend = "e:/project/backend/app/src"
if sys_path_backend not in sys.path:
    sys.path.insert(0, sys_path_backend)

from backend.app.src.request_serializer import serialize_request, _utc_ts

class TestRequestSerializer:
    """Test request serialization functionality."""
    
    def test_utc_ts_format(self):
        """Test UTC timestamp format."""
        with patch('backend.app.src.request_serializer.datetime') as mock_datetime:
            mock_datetime.utcnow.return_value = datetime(2025, 9, 3, 12, 30, 45)
            
            result = _utc_ts()
            
            assert result == "2025-09-03T12:30:45Z"

    def test_serialize_request_basic(self):
        """Test basic request serialization."""
        with patch('backend.app.src.request_serializer._utc_ts', return_value="2025-09-03T12:30:45Z"):
            result = serialize_request(
                prompt="Test prompt",
                snippets=["snippet1", "snippet2"],
                response="Test response"
            )
            
            expected = {
                "timestamp": "2025-09-03T12:30:45Z",
                "session_id": "",
                "mode": "chat",
                "prompt": "Test prompt",
                "snippets": ["snippet1", "snippet2"],
                "response": "Test response",
                "meta": {}
            }
            
            assert result == expected

    def test_serialize_request_with_session_id(self):
        """Test serialization with session ID."""
        with patch('backend.app.src.request_serializer._utc_ts', return_value="2025-09-03T12:30:45Z"):
            result = serialize_request(
                prompt="Test prompt",
                snippets=["snippet1"],
                response="Test response",
                session_id="session123"
            )
            
            assert result["session_id"] == "session123"

    def test_serialize_request_with_mode(self):
        """Test serialization with custom mode."""
        with patch('backend.app.src.request_serializer._utc_ts', return_value="2025-09-03T12:30:45Z"):
            result = serialize_request(
                prompt="Test prompt",
                snippets=[],
                response="Test response",
                mode="formula"
            )
            
            assert result["mode"] == "formula"

    def test_serialize_request_with_meta(self):
        """Test serialization with metadata."""
        meta_data = {"user_id": "user123", "version": "1.0"}
        
        with patch('backend.app.src.request_serializer._utc_ts', return_value="2025-09-03T12:30:45Z"):
            result = serialize_request(
                prompt="Test prompt",
                snippets=[],
                response="Test response",
                meta=meta_data
            )
            
            assert result["meta"] == meta_data

    def test_serialize_request_empty_snippets(self):
        """Test serialization with empty snippets."""
        with patch('backend.app.src.request_serializer._utc_ts', return_value="2025-09-03T12:30:45Z"):
            result = serialize_request(
                prompt="Test prompt",
                snippets=[],
                response="Test response"
            )
            
            assert result["snippets"] == []

    def test_serialize_request_all_parameters(self):
        """Test serialization with all parameters."""
        with patch('backend.app.src.request_serializer._utc_ts', return_value="2025-09-03T12:30:45Z"):
            result = serialize_request(
                prompt="Complex prompt",
                snippets=["s1", "s2", "s3"],
                response="Complex response",
                session_id="complex_session",
                mode="analysis",
                meta={"complexity": "high"}
            )
            
            expected = {
                "timestamp": "2025-09-03T12:30:45Z",
                "session_id": "complex_session",
                "mode": "analysis",
                "prompt": "Complex prompt",
                "snippets": ["s1", "s2", "s3"],
                "response": "Complex response",
                "meta": {"complexity": "high"}
            }
            
            assert result == expected
