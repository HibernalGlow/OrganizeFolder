import pytest
from unittest.mock import patch
from organizef.input import get_paths

def test_get_paths_clipboard_valid():
    """Test getting paths from clipboard with valid paths"""
    with patch('pyperclip.paste', return_value='C:\\test\nD:\\downloads'), \
         patch('os.path.exists', return_value=True), \
         patch('rich.prompt.Confirm.ask', return_value=True):
        paths = get_paths()
        assert paths == ['C:\\test', 'D:\\downloads']

def test_get_paths_clipboard_invalid_confirm():
    """Test clipboard with invalid paths, user confirms"""
    with patch('pyperclip.paste', return_value='C:\\test\ninvalid\nD:\\downloads'), \
         patch('os.path.exists', side_effect=[True, False, True]), \
         patch('rich.prompt.Confirm.ask', return_value=True):
        paths = get_paths()
        assert paths == ['C:\\test', 'D:\\downloads']

def test_get_paths_clipboard_reject():
    """Test clipboard paths rejected by user"""
    with patch('pyperclip.paste', return_value='C:\\test\nD:\\downloads'), \
         patch('os.path.exists', return_value=True), \
         patch('rich.prompt.Confirm.ask', return_value=False), \
         patch('rich.prompt.Prompt.ask') as mock_prompt:
        mock_prompt.side_effect = ['C:\\manual', '']  # Manual input then empty
        paths = get_paths()
        assert paths == ['C:\\manual']

def test_get_paths_manual_input():
    """Test manual path input"""
    with patch('pyperclip.paste', return_value=''), \
         patch('rich.prompt.Prompt.ask') as mock_prompt:
        mock_prompt.side_effect = ['C:\\test1', 'C:\\test2', '']  # Two paths then empty
        with patch('os.path.exists', return_value=True):
            paths = get_paths()
            assert paths == ['C:\\test1', 'C:\\test2']

def test_get_paths_duplicate_removal():
    """Test duplicate path removal"""
    with patch('pyperclip.paste', return_value=''), \
         patch('rich.prompt.Prompt.ask') as mock_prompt:
        mock_prompt.side_effect = ['C:\\test', 'C:\\test', '']  # Duplicate input
        with patch('os.path.exists', return_value=True), \
             patch('rich.console.Console.print'):
            paths = get_paths()
            assert paths == ['C:\\test']

def test_get_paths_invalid_path_retry():
    """Test invalid path retry"""
    with patch('pyperclip.paste', return_value=''), \
         patch('rich.prompt.Prompt.ask') as mock_prompt:
        mock_prompt.side_effect = ['invalid', 'C:\\valid', '']  # Invalid then valid
        with patch('os.path.exists', side_effect=[False, True]), \
             patch('rich.console.Console.print'):
            paths = get_paths()
            assert paths == ['C:\\valid']

def test_get_paths_no_paths():
    """Test no paths provided"""
    with patch('pyperclip.paste', return_value=''), \
         patch('rich.prompt.Prompt.ask', return_value=''):  # Empty input
        paths = get_paths()
        assert paths is None