"""
Unit tests for the retrieval module.
"""
import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add the backend path to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

class TestRetrievalModule:
    """Test retrieval module functionality."""
    
    @patch('backend.app.src.retrieval.encode_query')
    @patch('backend.app.src.retrieval.encode_texts') 
    @patch('backend.app.src.retrieval.load_index')
    @patch('backend.app.src.retrieval.search_index')
    def test_import_retrieval_module(self, mock_search, mock_load, mock_encode_texts, mock_encode_query):
        """Test that retrieval module can be imported."""
        from backend.app.src.retrieval import retrieve_with_fallback
        assert retrieve_with_fallback is not None
        
    @patch('backend.app.src.retrieval.encode_query')
    @patch('backend.app.src.retrieval.encode_texts') 
    @patch('backend.app.src.retrieval.load_index')
    @patch('backend.app.src.retrieval.search_index')
    def test_normalize_text_function(self, mock_search, mock_load, mock_encode_texts, mock_encode_query):
        """Test text normalization."""
        from backend.app.src.retrieval import _normalize_text
        
        result = _normalize_text("Hello World")
        assert result == "Hello World"
        
        result = _normalize_text("")
        assert result == ""
        
    @patch('backend.app.src.retrieval.encode_query')
    @patch('backend.app.src.retrieval.encode_texts') 
    @patch('backend.app.src.retrieval.load_index')
    @patch('backend.app.src.retrieval.search_index')
    def test_tokenize_function(self, mock_search, mock_load, mock_encode_texts, mock_encode_query):
        """Test tokenization function."""
        from backend.app.src.retrieval import _tokenize
        
        result = _tokenize("hello world test")
        assert isinstance(result, list)
        
        result = _tokenize("")
        assert result == []
        
    @patch('backend.app.src.retrieval.encode_query')
    @patch('backend.app.src.retrieval.encode_texts') 
    @patch('backend.app.src.retrieval.load_index')
    @patch('backend.app.src.retrieval.search_index')
    def test_bm25_class(self, mock_search, mock_load, mock_encode_texts, mock_encode_query):
        """Test BM25 class functionality."""
        from backend.app.src.retrieval import BM25
        
        corpus = ["hello world", "world test", "test case"]
        bm25 = BM25(corpus)
        
        assert bm25.N == 3
        assert len(bm25.corpus_tokens) == 3
        
        scores = bm25.score("hello world")
        assert len(scores) == 3
        assert all(isinstance(s, float) for s in scores)
        
    @patch('backend.app.src.retrieval.encode_query')
    @patch('backend.app.src.retrieval.encode_texts') 
    @patch('backend.app.src.retrieval.load_index')
    @patch('backend.app.src.retrieval.search_index')
    def test_normalize_function(self, mock_search, mock_load, mock_encode_texts, mock_encode_query):
        """Test normalize function."""
        from backend.app.src.retrieval import _normalize
        
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = _normalize(values)
        
        assert len(result) == 5
        assert min(result) == 0.0
        assert max(result) == 1.0
        
        result = _normalize([])
        assert result == []
        
    @patch('backend.app.src.retrieval.encode_query')
    @patch('backend.app.src.retrieval.encode_texts') 
    @patch('backend.app.src.retrieval.load_index')
    @patch('backend.app.src.retrieval.search_index')
    def test_retrieve_with_fallback_basic(self, mock_search, mock_load, mock_encode_texts, mock_encode_query):
        """Test retrieve_with_fallback function."""
        mock_load.return_value = None  # No index available
        mock_encode_query.return_value = np.array([[0.1, 0.2, 0.3]])
        mock_search.return_value = []
        mock_encode_texts.return_value = np.array([[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]])
        
        from backend.app.src.retrieval import retrieve_with_fallback
        
        chunks = ["machine learning is great", "deep learning algorithms"]
        query = "machine learning"
        
        indices, texts, score = retrieve_with_fallback(query, chunks, k=2)
        
        assert isinstance(indices, list)
        assert isinstance(texts, list)
        assert isinstance(score, float)
        assert score >= 0.0
        
    @patch('backend.app.src.retrieval.encode_query')
    @patch('backend.app.src.retrieval.encode_texts') 
    @patch('backend.app.src.retrieval.load_index')
    @patch('backend.app.src.retrieval.search_index')
    def test_retrieve_with_fallback_empty_chunks(self, mock_search, mock_load, mock_encode_texts, mock_encode_query):
        """Test retrieve_with_fallback with empty chunks."""
        from backend.app.src.retrieval import retrieve_with_fallback
        
        indices, texts, score = retrieve_with_fallback("test", [], k=2)
        
        assert indices == []
        assert texts == []
        assert score == 0.0
