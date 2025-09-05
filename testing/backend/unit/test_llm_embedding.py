"""
Tests for llm_embedding module.
"""
import pytest
import sys
import os
import numpy as np
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

class TestLLMEmbedding:
    """Test LLM embedding functionality."""
    
    def test_user_data_dir_with_localappdata(self):
        """Test user data directory with LOCALAPPDATA."""
        with patch.dict('sys.modules', {
            'sentence_transformers': MagicMock(),
            'faiss': MagicMock()
        }):
            with patch('os.environ.get') as mock_env:
                mock_env.return_value = "C:\\Users\\Test\\AppData\\Local"
                
                from backend.app.src.llm_embedding import _user_data_dir
                
                result = _user_data_dir()
                expected = Path("C:\\Users\\Test\\AppData\\Local\\FinLite")
                assert result == expected

    def test_user_data_dir_fallback(self):
        """Test user data directory fallback."""
        with patch.dict('sys.modules', {
            'sentence_transformers': MagicMock(),
            'faiss': MagicMock()
        }):
            with patch('os.environ.get') as mock_env:
                with patch('pathlib.Path.home') as mock_home:
                    mock_env.return_value = None
                    mock_home.return_value = Path("C:\\Users\\Test")
                    
                    from backend.app.src.llm_embedding import _user_data_dir
                    
                    result = _user_data_dir()
                    expected = Path("C:\\Users\\Test\\AppData\\Local\\FinLite")
                    assert result == expected

    def test_resolved_index_path_not_frozen(self):
        """Test resolved index path when not frozen."""
        with patch.dict('sys.modules', {
            'sentence_transformers': MagicMock(),
            'faiss': MagicMock()
        }):
            with patch('backend.app.src.llm_embedding.INDEX_PATH', 'test_index.faiss'):
                with patch('backend.app.src.llm_embedding.getattr', return_value=False):
                    from backend.app.src.llm_embedding import _resolved_index_path
                    
                    result = _resolved_index_path()
                    assert str(result).endswith('test_index.faiss')

    def test_resolved_index_path_frozen(self):
        """Test resolved index path when frozen."""
        with patch.dict('sys.modules', {
            'sentence_transformers': MagicMock(),
            'faiss': MagicMock()
        }):
            with patch('backend.app.src.llm_embedding.INDEX_PATH', 'test_index.faiss'):
                with patch('backend.app.src.llm_embedding.getattr', return_value=True):
                    with patch('backend.app.src.llm_embedding.sys.executable', '/path/to/exe'):
                        from backend.app.src.llm_embedding import _resolved_index_path
                        
                        result = _resolved_index_path()
                        assert str(result).endswith('test_index.faiss')

    def test_resolved_index_path_absolute(self):
        """Test resolved index path with absolute path."""
        with patch.dict('sys.modules', {
            'sentence_transformers': MagicMock(),
            'faiss': MagicMock()
        }):
            abs_path = "/absolute/path/to/index.faiss"
            with patch('backend.app.src.llm_embedding.INDEX_PATH', abs_path):
                from backend.app.src.llm_embedding import _resolved_index_path
                
                result = _resolved_index_path()
                # On Windows, absolute paths get converted to Windows format
                result_str = str(result).replace('\\', '/')
                # Remove drive letter if present (E: becomes empty)
                if len(result_str) > 1 and result_str[1] == ':':
                    result_str = result_str[2:]
                assert result_str == abs_path

    @patch('backend.app.src.llm_embedding.faiss')
    @patch('backend.app.src.llm_embedding._encoder')
    def test_build_index(self, mock_encoder, mock_faiss):
        """Test index building."""
        with patch.dict('sys.modules', {
            'sentence_transformers': MagicMock(),
            'faiss': MagicMock()
        }):
            mock_encoder.encode.return_value = np.array([[1, 2, 3], [4, 5, 6]])
            
            mock_index = Mock()
            mock_faiss.IndexFlatL2.return_value = mock_index
            
            with patch('backend.app.src.llm_embedding._resolved_index_path') as mock_path:
                mock_path.return_value = Mock()
                mock_path.return_value.parent.mkdir = Mock()
                
                from backend.app.src.llm_embedding import build_index
                
                texts = ["text1", "text2"]
                result = build_index(texts)
                
                assert result is None
                mock_encoder.encode.assert_called_once_with(texts, convert_to_numpy=True)
                mock_index.add.assert_called_once()

    @patch('backend.app.src.llm_embedding.faiss')
    @patch('backend.app.src.llm_embedding._resolved_index_path')
    def test_load_index_success(self, mock_path, mock_faiss):
        """Test successful index loading."""
        with patch.dict('sys.modules', {
            'sentence_transformers': MagicMock(),
            'faiss': MagicMock()
        }):
            mock_path_obj = Mock()
            mock_path_obj.exists.return_value = True
            mock_path.return_value = mock_path_obj
            mock_index = Mock()
            mock_faiss.read_index.return_value = mock_index
            
            from backend.app.src.llm_embedding import load_index
            
            result = load_index()
            
            assert result == mock_index
            mock_faiss.read_index.assert_called_once_with(str(mock_path_obj))

    @patch('backend.app.src.llm_embedding.faiss')
    @patch('backend.app.src.llm_embedding._resolved_index_path')
    def test_load_index_file_not_exists(self, mock_path, mock_faiss):
        """Test index loading when file doesn't exist."""
        with patch.dict('sys.modules', {
            'sentence_transformers': MagicMock(),
            'faiss': MagicMock()
        }):
            with patch('backend.app.src.llm_embedding._index', None):
                mock_path_obj = Mock()
                mock_path_obj.exists.return_value = False
                mock_path.return_value = mock_path_obj
                
                from backend.app.src.llm_embedding import load_index
                
                result = load_index()
                
                assert result is None

    @patch('backend.app.src.llm_embedding.faiss')
    @patch('backend.app.src.llm_embedding._resolved_index_path')
    def test_load_index_exception(self, mock_path, mock_faiss):
        """Test index loading with exception."""
        with patch.dict('sys.modules', {
            'sentence_transformers': MagicMock(),
            'faiss': MagicMock()
        }):
            # Reset the global _index variable
            with patch('backend.app.src.llm_embedding._index', None):
                mock_path_obj = Mock()
                mock_path_obj.exists.return_value = True
                mock_path.return_value = mock_path_obj
                mock_faiss.read_index.side_effect = Exception("Test error")
                
                from backend.app.src.llm_embedding import load_index
                
                result = load_index()
                
                assert result is None

    @patch('backend.app.src.llm_embedding._encoder')
    def test_encode_query(self, mock_encoder):
        """Test query encoding."""
        with patch.dict('sys.modules', {
            'sentence_transformers': MagicMock(),
            'faiss': MagicMock()
        }):
            # encode_query calls encode([query]), so it returns a 2D array
            mock_encoder.encode.return_value = np.array([[1, 2, 3]])
            
            from backend.app.src.llm_embedding import encode_query
            
            result = encode_query("test query")
            
            np.testing.assert_array_equal(result, np.array([[1, 2, 3]]))
            mock_encoder.encode.assert_called_once_with(["test query"], convert_to_numpy=True)

    @patch('backend.app.src.llm_embedding.load_index')
    def test_search_index_no_index(self, mock_load):
        """Test search when no index available."""
        with patch.dict('sys.modules', {
            'sentence_transformers': MagicMock(),
            'faiss': MagicMock()
        }):
            mock_load.return_value = None
            
            from backend.app.src.llm_embedding import search_index
            
            result = search_index(np.array([[1, 2, 3]]), k=2)
            
            assert result == []

    @patch('backend.app.src.llm_embedding.load_index')
    def test_search_index_success(self, mock_load):
        """Test successful index search."""
        with patch.dict('sys.modules', {
            'sentence_transformers': MagicMock(),
            'faiss': MagicMock()
        }):
            mock_index = Mock()
            mock_load.return_value = mock_index
            mock_index.search.return_value = (np.array([[0.9, 0.8]]), np.array([[0, 1]]))
            
            from backend.app.src.llm_embedding import search_index
            
            # Original search_index function signature: search_index(q_emb, k)
            result = search_index(np.array([[1, 2, 3]]), k=2)
            
            expected = [0, 1]  # Returns list of indices
            assert result == expected

    @patch('backend.app.src.llm_embedding.SentenceTransformer')
    def test_encode_texts_empty(self, mock_transformer):
        """Test encoding empty text list."""
        with patch.dict('sys.modules', {
            'sentence_transformers': MagicMock(),
            'faiss': MagicMock()
        }):
            from backend.app.src.llm_embedding import encode_texts
            
            result = encode_texts([])
            
            assert result.shape == (0, 384)

    @patch('backend.app.src.llm_embedding._encoder')
    def test_encode_texts_success(self, mock_encoder):
        """Test successful text encoding."""
        with patch.dict('sys.modules', {
            'sentence_transformers': MagicMock(),
            'faiss': MagicMock()
        }):
            mock_encoder.encode.return_value = np.array([[1, 2, 3], [4, 5, 6]])
            
            from backend.app.src.llm_embedding import encode_texts
            
            result = encode_texts(["text1", "text2"])
            
            np.testing.assert_array_equal(result, np.array([[1, 2, 3], [4, 5, 6]]))
            mock_encoder.encode.assert_called_once_with(["text1", "text2"], convert_to_numpy=True)
