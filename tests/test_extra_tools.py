"""Tests for extra tools loading functionality."""

import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock

# Import our module
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from strands_agents_builder.strands import load_extra_tools


class TestExtraTools:
    """Test extra tools loading functionality."""

    def test_load_from_tools_file(self):
        """Test loading tools from .tools file."""
        # Create a temporary .tools file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.tools', delete=False) as f:
            f.write("# Comment line\n")
            f.write("strands_tools.memory\n")
            f.write("\n")  # Empty line
            f.write("strands_tools.current_time\n")
            tools_file = f.name

        try:
            # Patch the tools file path
            with patch('strands_agents_builder.strands.os.path.exists') as mock_exists:
                mock_exists.return_value = True
                
                with patch('builtins.open', mock_open(read_data=open(tools_file).read())):
                    with patch('strands_agents_builder.strands.importlib.import_module') as mock_import:
                        mock_module = MagicMock()
                        mock_tool = MagicMock()
                        mock_module.memory = mock_tool
                        mock_module.current_time = mock_tool
                        mock_import.return_value = mock_module
                        
                        tools = load_extra_tools()
                        assert len(tools) == 2
        finally:
            os.unlink(tools_file)

    def test_load_from_environment_variable(self):
        """Test loading tools from STRANDS_EXTRA_TOOLS environment variable."""
        with patch.dict(os.environ, {'STRANDS_EXTRA_TOOLS': 'strands_tools.memory,strands_tools.current_time'}):
            with patch('strands_agents_builder.strands.os.path.exists') as mock_exists:
                mock_exists.return_value = False  # No .tools file
                
                with patch('strands_agents_builder.strands.importlib.import_module') as mock_import:
                    mock_module = MagicMock()
                    mock_tool = MagicMock()
                    mock_module.memory = mock_tool
                    mock_module.current_time = mock_tool
                    mock_import.return_value = mock_module
                    
                    tools = load_extra_tools()
                    assert len(tools) == 2

    def test_load_from_both_sources(self):
        """Test loading tools from both .tools file and environment variable."""
        # Create a temporary .tools file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.tools', delete=False) as f:
            f.write("strands_tools.memory\n")
            tools_file = f.name

        try:
            with patch.dict(os.environ, {'STRANDS_EXTRA_TOOLS': 'strands_tools.current_time'}):
                with patch('strands_agents_builder.strands.os.path.exists') as mock_exists:
                    mock_exists.return_value = True
                    
                    with patch('builtins.open', mock_open(read_data=open(tools_file).read())):
                        with patch('strands_agents_builder.strands.importlib.import_module') as mock_import:
                            mock_module = MagicMock()
                            mock_tool = MagicMock()
                            mock_module.memory = mock_tool
                            mock_module.current_time = mock_tool
                            mock_import.return_value = mock_module
                            
                            tools = load_extra_tools()
                            assert len(tools) == 2
        finally:
            os.unlink(tools_file)

    def test_handle_invalid_tool_name(self):
        """Test handling of invalid tool names."""
        with patch.dict(os.environ, {'STRANDS_EXTRA_TOOLS': 'invalid.tool.name'}):
            with patch('strands_agents_builder.strands.os.path.exists') as mock_exists:
                mock_exists.return_value = False
                
                with patch('strands_agents_builder.strands.importlib.import_module') as mock_import:
                    mock_import.side_effect = ImportError("Module not found")
                    
                    tools = load_extra_tools()
                    assert len(tools) == 0  # Should handle the error gracefully


def mock_open(read_data=''):
    """Mock open function for testing."""
    from unittest.mock import mock_open as base_mock_open
    return base_mock_open(read_data=read_data)