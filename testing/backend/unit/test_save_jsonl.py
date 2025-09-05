"""
Tests for save_jsonl module.
"""
import pytest
import sys
import json
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

sys_path_backend = "e:/project/backend/app/src"
if sys_path_backend not in sys.path:
    sys.path.insert(0, sys_path_backend)

class TestSaveJsonl:
    """Test JSONL saving functionality."""
    
    @patch('backend.app.src.save_jsonl.Path')
    @patch('backend.app.src.save_jsonl._json.loads')
    def test_module_initialization(self, mock_json_loads, mock_path):
        """Test module initialization."""
        mock_config = {"LOG_JSONL": "logs/interactions.jsonl"}
        mock_json_loads.return_value = mock_config
        
        mock_path_instance = Mock()
        mock_path_instance.read_text.return_value = json.dumps(mock_config)
        mock_path.return_value = mock_path_instance
        
        import importlib
        if 'backend.app.src.save_jsonl' in sys.modules:
            importlib.reload(sys.modules['backend.app.src.save_jsonl'])

    @patch('backend.app.src.save_jsonl.serialize_request')
    @patch('backend.app.src.save_jsonl.LOG_PATH')
    @patch('builtins.open', new_callable=mock_open)
    def test_save_interaction_with_session_id(self, mock_file, mock_log_path, mock_serialize):
        """Test saving interaction with session ID."""
        mock_serialize.return_value = {
            "timestamp": "2025-09-03T12:30:45Z",
            "session_id": "test_session",
            "prompt": "test prompt",
            "response": "test response"
        }
        
        from backend.app.src.save_jsonl import save_interaction
        
        save_interaction(
            prompt="test prompt",
            snippets=["snippet1"],
            response="test response",
            session_id="test_session"
        )
        
        mock_serialize.assert_called_once()
        mock_file.assert_called()

    @patch('backend.app.src.save_jsonl.serialize_request')
    def test_save_interaction_without_session_id(self, mock_serialize):
        """Test saving interaction without session ID returns early."""
        from backend.app.src.save_jsonl import save_interaction
        
        save_interaction(
            prompt="test prompt",
            snippets=["snippet1"],
            response="test response",
            session_id=None
        )
        
        mock_serialize.assert_not_called()

    @patch('backend.app.src.save_jsonl.serialize_request')
    @patch('backend.app.src.save_jsonl.LOG_PATH')
    @patch('builtins.open', new_callable=mock_open)
    def test_save_interaction_with_metadata(self, mock_file, mock_log_path, mock_serialize):
        """Test saving interaction with metadata."""
        mock_serialize.return_value = {
            "timestamp": "2025-09-03T12:30:45Z",
            "session_id": "test_session",
            "mode": "formula",
            "meta": {"type": "excel"}
        }
        
        from backend.app.src.save_jsonl import save_interaction
        
        save_interaction(
            prompt="formula prompt",
            snippets=[],
            response="formula response",
            session_id="test_session",
            mode="formula",
            meta={"type": "excel"}
        )
        
        mock_serialize.assert_called_once_with(
            "formula prompt", [], "formula response",
            session_id="test_session", mode="formula", meta={"type": "excel"}
        )

    @patch('backend.app.src.save_jsonl.serialize_request')
    @patch('backend.app.src.save_jsonl.LOG_PATH')
    @patch('builtins.open', new_callable=mock_open)
    def test_save_interaction_file_operations(self, mock_file, mock_log_path, mock_serialize):
        """Test file operations during save."""
        mock_serialize.return_value = {"test": "data"}
        mock_log_path.exists.return_value = True
        mock_log_path.stat.return_value.st_size = 1000
        
        from backend.app.src.save_jsonl import save_interaction
        
        save_interaction(
            prompt="test",
            snippets=[],
            response="test",
            session_id="session1"
        )
        
        mock_file.assert_called()

    @patch('backend.app.src.save_jsonl.serialize_request') 
    @patch('backend.app.src.save_jsonl.LOG_PATH')
    def test_save_interaction_empty_session(self, mock_log_path, mock_serialize):
        """Test saving with empty session string."""
        from backend.app.src.save_jsonl import save_interaction
        
        save_interaction(
            prompt="test",
            snippets=[],
            response="test",
            session_id=""
        )
        
        mock_serialize.assert_not_called()
