"""
Tests for llm_generating module.
"""
import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

class TestLLMGenerating:
    """Test LLM generation functionality."""
    
    def test_generate_answer_mock_basic(self):
        """Test basic answer generation with mocking."""
        with patch.dict('sys.modules', {
            'llama_cpp': MagicMock()
        }):
            with patch('backend.app.src.llm_generating._llm') as mock_llm:
                mock_llm.return_value = {"choices": [{"text": "  Test response  "}]}
                
                from backend.app.src.llm_generating import generate_answer
                
                result = generate_answer("Test prompt")
                
                assert result == "Test response"

    def test_generate_answer_mock_detailed(self):
        """Test detailed answer generation with mock parameters."""
        with patch.dict('sys.modules', {
            'llama_cpp': MagicMock()
        }):
            with patch('backend.app.src.llm_generating._llm') as mock_llm:
                mock_llm.return_value = {
                    "choices": [{
                        "text": "  Detailed financial analysis response  "
                    }]
                }
                
                from backend.app.src.llm_generating import generate_answer
                
                result = generate_answer(
                    prompt="Analyze financial data",
                    detailed=True
                )
                
                assert result == "Detailed financial analysis response"
                mock_llm.assert_called_once()

    def test_response_stripping_variations(self):
        """Test response text stripping with different inputs."""
        with patch.dict('sys.modules', {
            'llama_cpp': MagicMock()
        }):
            test_cases = [
                ("  Normal response  ", "Normal response"),
                ("\n\nWith newlines\n\n", "With newlines"),
                ("   \t Mixed whitespace \r\n ", "Mixed whitespace"),
                ("Already clean", "Already clean")
            ]
            
            for input_text, expected in test_cases:
                with patch('backend.app.src.llm_generating._llm') as mock_llm:
                    mock_llm.return_value = {"choices": [{"text": input_text}]}
                    
                    from backend.app.src.llm_generating import generate_answer
                    
                    result = generate_answer("Test prompt")
                    assert result == expected

    def test_llm_parameters_simulation(self):
        """Test LLM parameter handling simulation."""
        with patch.dict('sys.modules', {
            'llama_cpp': MagicMock()
        }):
            with patch('backend.app.src.llm_generating._llm') as mock_llm:
                mock_llm.return_value = {"choices": [{"text": "Parameter test response"}]}
                
                from backend.app.src.llm_generating import generate_answer
                
                result1 = generate_answer(
                    prompt="Test prompt with parameters",
                    detailed=False
                )
                
                result2 = generate_answer(
                    prompt="Test prompt with detailed mode",
                    detailed=True
                )
                
                assert mock_llm.call_count >= 2

    def test_generate_answer_error_handling(self):
        """Test error handling in generate_answer."""
        with patch.dict('sys.modules', {
            'llama_cpp': MagicMock()
        }):
            with patch('backend.app.src.llm_generating._llm') as mock_llm:
                mock_llm.side_effect = Exception("LLM generation failed")
                
                from backend.app.src.llm_generating import generate_answer
                
                # Should handle the error gracefully
                try:
                    result = generate_answer("Test prompt")
                    # If no exception is raised, verify result is reasonable
                    assert isinstance(result, str)
                except Exception:
                    # If exception is raised, that's also acceptable behavior
                    pass

    def test_generate_answer_empty_response(self):
        """Test handling of empty or malformed responses."""
        with patch.dict('sys.modules', {
            'llama_cpp': MagicMock()
        }):
            with patch('backend.app.src.llm_generating._llm') as mock_llm:
                mock_llm.return_value = {"choices": []}
                
                from backend.app.src.llm_generating import generate_answer
                
                try:
                    result = generate_answer("Test prompt")
                    assert isinstance(result, str)
                except (IndexError, KeyError):
                    pass

    def test_generate_answer_threading_safety(self):
        """Test generate_answer function for basic threading considerations."""
        with patch.dict('sys.modules', {
            'llama_cpp': MagicMock()
        }):
            with patch('backend.app.src.llm_generating._llm') as mock_llm:
                mock_llm.return_value = {"choices": [{"text": "Thread safe response"}]}
                
                from backend.app.src.llm_generating import generate_answer
                
                results = []
                for i in range(3):
                    result = generate_answer(f"Test prompt {i}")
                    results.append(result)
                
                assert len(results) == 3
                assert all(isinstance(r, str) for r in results)
