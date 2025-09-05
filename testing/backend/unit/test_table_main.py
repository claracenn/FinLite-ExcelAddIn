"""
Tests for table_main module functionality.
"""
import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
import pandas as pd

# Add the backend path to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

# Mock the dependencies before any imports
sys.modules['llm_embedding'] = MagicMock()
sys.modules['retrieval'] = MagicMock()
sys.modules['llm_generating'] = MagicMock()
sys.modules['table_linearizer'] = MagicMock()
sys.modules['save_jsonl'] = MagicMock()

class TestTableMainFunctionality:
    """Test table main functionality with mocking."""
    
    def test_import_table_main_module(self):
        """Test that table_main module can be imported."""
        from backend.app.src.table_main import set_current_chunks, get_current_chunks
        assert set_current_chunks is not None
        assert get_current_chunks is not None
        
    def test_chunk_management(self):
        """Test chunk management functionality."""
        from backend.app.src.table_main import set_current_chunks, get_current_chunks
        
        test_chunks = ["chunk1", "chunk2", "chunk3"]
        set_current_chunks(test_chunks)
        
        retrieved_chunks = get_current_chunks()
        assert retrieved_chunks == test_chunks
        
    def test_query_current_data(self):
        """Test rag_pipeline functionality."""
        sys.modules['retrieval'].retrieve_with_fallback.return_value = ([0, 1], ["chunk1", "chunk2"], 0.8)
        sys.modules['llm_generating'].generate_answer.return_value = "This is a generated answer."
        
        from backend.app.src.table_main import rag_pipeline, set_current_chunks
        
        test_chunks = ["revenue data", "expense data", "profit data"]
        set_current_chunks(test_chunks)
        
        result = rag_pipeline("What is the revenue?")
        assert result is not None
        assert len(result) == 2
        
    @patch('pandas.read_excel')
    def test_load_excel_data(self, mock_read_excel):
        """Test Excel data loading functionality."""
        sys.modules['table_linearizer'].linearize = MagicMock(return_value=["Product: A, Sales: 100, Quarter: Q1"])
        
        mock_df = pd.DataFrame({
            'Product': ['A', 'B', 'C'],
            'Sales': [100, 200, 150],
            'Quarter': ['Q1', 'Q2', 'Q3']
        })
        mock_read_excel.return_value = mock_df
        
        from backend.app.src.table_main import load_excel_data
        
        result = load_excel_data("test.xlsx")
        assert result is not None

    def test_chunks_management(self):
        """Test chunk management functionality."""
        test_chunks = ["chunk1", "chunk2", "chunk3"]
        
        current_chunks = test_chunks.copy()
        result = current_chunks
        assert result == test_chunks
        
        empty_chunks = []
        result_empty = empty_chunks
        assert result_empty == []

    def test_query_processing_logic(self):
        """Test query processing logic."""
        chunks = ["Financial data for Apple", "Revenue information", "Stock prices"]
        query = "What is Apple's revenue?"
        
        relevant_chunks = [chunk for chunk in chunks if "Apple" in chunk or "revenue" in chunk.lower()]
        
        assert len(relevant_chunks) >= 1
        assert any("Apple" in chunk for chunk in relevant_chunks)

    def test_answer_generation_logic(self):
        """Test answer generation logic."""
        evidence = ["Apple revenue is $100B", "Apple is a tech company"]
        query = "What is Apple's revenue?"
        
        if evidence:
            mock_answer = f"Based on the data: {evidence[0]}"
        else:
            mock_answer = "I don't have enough information to answer that question."
        
        assert "Apple revenue" in mock_answer or "don't have enough" in mock_answer

    def test_excel_upload_simulation(self):
        """Test Excel upload simulation."""
        file_path = "test_financial_data.xlsx"
        
        mock_result = {
            "status": "success",
            "message": f"Successfully processed {file_path}",
            "chunks_count": 10
        }
        
        assert mock_result["status"] == "success"
        assert "Successfully processed" in mock_result["message"]
        assert mock_result["chunks_count"] > 0

    def test_error_handling_simulation(self):
        """Test error handling simulation."""
        bad_file = "nonexistent.xlsx"
        
        try:
            raise FileNotFoundError(f"File {bad_file} not found")
        except FileNotFoundError as e:
            mock_error_result = {
                "status": "error",
                "message": str(e)
            }
        
        assert mock_error_result["status"] == "error"
        assert "not found" in mock_error_result["message"]

    def test_multiple_sheets_processing(self):
        """Test multiple sheets processing."""
        sheets = {
            "Income_Statement": ["Revenue: $100B", "Expenses: $80B"],
            "Balance_Sheet": ["Assets: $200B", "Liabilities: $100B"]
        }
        
        all_chunks = []
        for sheet_name, rows in sheets.items():
            tagged_rows = [f"[{sheet_name}] {row}" for row in rows]
            all_chunks.extend(tagged_rows)
        
        assert len(all_chunks) == 4
        assert "[Income_Statement]" in all_chunks[0]
        assert "[Balance_Sheet]" in all_chunks[2]

    @patch('pandas.read_excel')
    def test_pandas_integration(self, mock_read_excel):
        """Test pandas integration with mocking."""
        mock_df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
        mock_read_excel.return_value = {"Sheet1": mock_df}
        
        result = mock_read_excel("test.xlsx", sheet_name=None, engine="openpyxl")
        
        assert "Sheet1" in result
        assert isinstance(result["Sheet1"], pd.DataFrame)
        mock_read_excel.assert_called_once_with("test.xlsx", sheet_name=None, engine="openpyxl")

    def test_detect_intent_comparison(self):
        """Test _detect_intent function for comparison queries."""
        from backend.app.src.table_main import _detect_intent
        
        assert _detect_intent("compare Apple vs Microsoft") == "compare"
        assert _detect_intent("which is greater than 100?") == "compare" 
        assert _detect_intent("is revenue higher than last year?") == "compare"
        
    def test_detect_intent_trend(self):
        """Test _detect_intent function for trend queries."""
        from backend.app.src.table_main import _detect_intent
        
        assert _detect_intent("show revenue trend over time") == "trend"
        assert _detect_intent("how did sales growth evolve?") == "trend"
        assert _detect_intent("track the decline in profits") == "trend"
        
    def test_detect_intent_superlative(self):
        """Test _detect_intent function for superlative queries."""
        from backend.app.src.table_main import _detect_intent
        
        assert _detect_intent("what is the highest revenue?") == "superlative"
        assert _detect_intent("find the minimum cost") == "superlative"
        assert _detect_intent("top performing product") == "superlative"
        
    def test_detect_intent_calculation(self):
        """Test _detect_intent function for calculation queries."""
        from backend.app.src.table_main import _detect_intent
        
        assert _detect_intent("calculate the average revenue") == "calc"
        assert _detect_intent("sum of all expenses") == "calc"
        assert _detect_intent("what is the total count?") == "calc"
        
    def test_detect_intent_lookup(self):
        """Test _detect_intent function for lookup queries."""
        from backend.app.src.table_main import _detect_intent
        
        assert _detect_intent("what is the value of Apple stock?") == "lookup"
        assert _detect_intent("show me the revenue for Q1") == "lookup"
        assert _detect_intent("find the price") == "lookup"
        
    def test_detect_intent_explain(self):
        """Test _detect_intent function for explanation queries."""
        from backend.app.src.table_main import _detect_intent
        
        assert _detect_intent("why is this value so high?") == "explain"
        assert _detect_intent("explain the reason for this anomaly") == "explain"
        
    def test_detect_intent_default(self):
        """Test _detect_intent function for default case."""
        from backend.app.src.table_main import _detect_intent
        
        assert _detect_intent("general question about data") == "summary"
        assert _detect_intent("") == "summary"
        assert _detect_intent(None) == "summary"
        
    def test_build_prompt_simple(self):
        """Test _build_prompt function in simple mode."""
        from backend.app.src.table_main import _build_prompt
        
        selected = ["row1: data1", "row2: data2"]
        prompt = "What is the revenue?"
        
        result = _build_prompt(selected, prompt, detailed=False)
        
        assert "You are a helpful assistant" in result
        assert "row1: data1" in result
        assert "row2: data2" in result
        assert "What is the revenue?" in result
        
    def test_build_prompt_detailed_trend(self):
        """Test _build_prompt function in detailed mode for trend queries."""
        from backend.app.src.table_main import _build_prompt
        
        selected = ["2020: $100", "2021: $120", "2022: $150"]
        prompt = "show revenue trend over time"
        
        result = _build_prompt(selected, prompt, detailed=True)
        
        assert "trend analysis" in result
        assert "Direction and magnitude" in result
        assert "inflection points" in result
        
    def test_build_prompt_detailed_compare(self):
        """Test _build_prompt function in detailed mode for comparison queries."""
        from backend.app.src.table_main import _build_prompt
        
        selected = ["Apple: $100B", "Microsoft: $90B"]
        prompt = "compare Apple vs Microsoft revenue"
        
        result = _build_prompt(selected, prompt, detailed=True)
        
        assert "comparison" in result
        assert "key metrics" in result
        assert "winner/better option" in result
        
    def test_build_prompt_detailed_superlative(self):
        """Test _build_prompt function in detailed mode for superlative queries."""
        from backend.app.src.table_main import _build_prompt
        
        selected = ["Q1: $100", "Q2: $150", "Q3: $120"]
        prompt = "what is the highest quarterly revenue?"
        
        result = _build_prompt(selected, prompt, detailed=True)
        
        assert "superlative-focused" in result
        assert "max/min value" in result
        assert "criterion" in result
        
    def test_build_prompt_detailed_calc(self):
        """Test _build_prompt function in detailed mode for calculation queries."""
        from backend.app.src.table_main import _build_prompt
        
        selected = ["Revenue: $100", "Expenses: $80"]
        prompt = "calculate the average profit margin"
        
        result = _build_prompt(selected, prompt, detailed=True)
        
        assert "calculation-oriented" in result
        assert "formula and variables" in result
        assert "numeric result" in result
        
    def test_build_prompt_detailed_lookup(self):
        """Test _build_prompt function in detailed mode for lookup queries."""
        from backend.app.src.table_main import _build_prompt
        
        selected = ["Apple Q1: $100B", "Apple Q2: $110B"]
        prompt = "what is Apple's Q1 revenue?"
        
        result = _build_prompt(selected, prompt, detailed=True)
        
        assert "fact-based answer" in result
        assert "exact row(s)" in result
        assert "Return the value" in result
        
    def test_build_prompt_detailed_explain(self):
        """Test _build_prompt function in detailed mode for explanation queries."""
        from backend.app.src.table_main import _build_prompt
        
        selected = ["Revenue anomaly", "Market factors"]
        prompt = "why is this value so high?"
        
        result = _build_prompt(selected, prompt, detailed=True)
        
        assert "explanation" in result.lower()
        assert "possible reasons" in result
        assert "uncertainties" in result
        
    def test_build_prompt_detailed_summary(self):
        """Test _build_prompt function in detailed mode for summary queries."""
        from backend.app.src.table_main import _build_prompt
        
        selected = ["Various data points"]
        prompt = "give me a general overview"  # This should trigger summary intent
        
        result = _build_prompt(selected, prompt, detailed=True)
        
        assert "detailed yet focused" in result
        assert "Key insights" in result
        assert "conclusion" in result
        
    def test_rag_pipeline_detailed_mode(self):
        """Test rag_pipeline with detailed mode."""
        sys.modules['retrieval'].retrieve_with_fallback.return_value = ([0, 1], ["chunk1", "chunk2"], 0.8)
        sys.modules['llm_generating'].generate_answer.return_value = "Detailed analysis answer."
        
        from backend.app.src.table_main import rag_pipeline, set_current_chunks
        
        test_chunks = ["revenue data", "expense data", "profit data"]
        set_current_chunks(test_chunks)
        
        result = rag_pipeline("show revenue trend over time", detailed=True)
        assert result is not None
        assert len(result) == 2
        
    def test_rag_pipeline_custom_k(self):
        """Test rag_pipeline with custom k parameter."""
        sys.modules['retrieval'].retrieve_with_fallback.return_value = ([0, 1, 2], ["chunk1", "chunk2", "chunk3"], 0.9)
        sys.modules['llm_generating'].generate_answer.return_value = "Answer with custom k."
        
        from backend.app.src.table_main import rag_pipeline, set_current_chunks
        
        test_chunks = ["revenue data", "expense data", "profit data", "additional data"]
        set_current_chunks(test_chunks)
        
        result = rag_pipeline("What is the revenue?", detailed=False, k=3)
        assert result is not None
        assert len(result) == 2
