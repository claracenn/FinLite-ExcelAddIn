"""
Unit tests for table linearization functionality.
"""
import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from backend.app.src.table_linearizer import linearize


class TestTableLinearizer:
    def test_linearize_simple_dataframe(self):
        df = pd.DataFrame({
            'Name': ['Alice', 'Bob'],
            'Age': [25, 30]
        })
        result = linearize(df)
        expected = ['Name: Alice; Age: 25', 'Name: Bob; Age: 30']
        assert result == expected

    def test_linearize_single_row(self):
        df = pd.DataFrame({
            'Name': ['Alice'],
            'Age': [25]
        })
        result = linearize(df)
        expected = ['Name: Alice; Age: 25']
        assert result == expected

    def test_linearize_single_column(self):
        df = pd.DataFrame({
            'Name': ['Alice', 'Bob', 'Charlie']
        })
        result = linearize(df)
        expected = ['Name: Alice', 'Name: Bob', 'Name: Charlie']
        assert result == expected

    def test_linearize_empty_dataframe(self):
        df = pd.DataFrame()
        result = linearize(df)
        assert result == []

    def test_linearize_with_none_values(self):
        df = pd.DataFrame({
            'Name': ['Alice', None, 'Charlie'],
            'Score': [95, 87, np.nan]
        })
        result = linearize(df)
        expected = [
            'Name: Alice; Score: 95.0',
            'Name: None; Score: 87.0',
            'Name: Charlie; Score: nan'
        ]
        assert result == expected

    def test_linearize_mixed_types(self):
        df = pd.DataFrame({
            'ID': [1, 2, 3],
            'Name': ['Alice', 'Bob', 'Charlie'],
            'Active': [True, False, True],
            'Balance': [100.5, 200.0, 150.75]
        })
        result = linearize(df)
        expected = [
            'ID: 1; Name: Alice; Active: True; Balance: 100.5',
            'ID: 2; Name: Bob; Active: False; Balance: 200.0',
            'ID: 3; Name: Charlie; Active: True; Balance: 150.75'
        ]
        assert result == expected

    def test_linearize_financial_data(self):
        df = pd.DataFrame({
            'Company': ['Apple', 'Google'],
            'Revenue': [365.8, 257.6],
            'Growth': ['5.2%', '7.1%']
        })
        result = linearize(df)
        expected = [
            'Company: Apple; Revenue: 365.8; Growth: 5.2%',
            'Company: Google; Revenue: 257.6; Growth: 7.1%'
        ]
        assert result == expected

    def test_linearize_special_characters(self):
        df = pd.DataFrame({
            'Text': ['Hello, World!', 'Test@123', 'Data & Analytics'],
            'Symbol': ['$', '%', '#']
        })
        result = linearize(df)
        expected = [
            'Text: Hello, World!; Symbol: $',
            'Text: Test@123; Symbol: %',
            'Text: Data & Analytics; Symbol: #'
        ]
        assert result == expected

    def test_linearize_unicode_data(self):
        df = pd.DataFrame({
            'Name': ['José', 'François', '张三'],
            'City': ['São Paulo', 'Montréal', '北京']
        })
        result = linearize(df)
        expected = [
            'Name: José; City: São Paulo',
            'Name: François; City: Montréal',
            'Name: 张三; City: 北京'
        ]
        assert result == expected
