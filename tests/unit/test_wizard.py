"""
Unit tests for setup/wizard.py.

Tests cover:
- SetupWizard initialization
- Helper functions (print_header, print_section, etc.)
- Input functions with mocked input
- Wizard steps with mocked input
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from setup.wizard import (
    SetupWizard,
    get_input,
    get_yes_no,
    print_error,
    print_header,
    print_section,
    print_success,
    print_warning,
    select_option,
)


class TestPrintFunctions:
    """Test print helper functions."""
    
    def test_print_header(self, capsys):
        """Test print_header function."""
        print_header("Test Header")
        
        captured = capsys.readouterr()
        assert "Test Header" in captured.out
        assert "=" in captured.out
    
    def test_print_section(self, capsys):
        """Test print_section function."""
        print_section("Test Section")
        
        captured = capsys.readouterr()
        assert "Test Section" in captured.out
        assert "---" in captured.out
    
    def test_print_success(self, capsys):
        """Test print_success function."""
        print_success("Operation successful")
        
        captured = capsys.readouterr()
        assert "Operation successful" in captured.out
        assert "✓" in captured.out
    
    def test_print_error(self, capsys):
        """Test print_error function."""
        print_error("Error occurred")
        
        captured = capsys.readouterr()
        assert "Error occurred" in captured.out
        assert "✗" in captured.out
    
    def test_print_warning(self, capsys):
        """Test print_warning function."""
        print_warning("Warning message")
        
        captured = capsys.readouterr()
        assert "Warning message" in captured.out
        assert "⚠" in captured.out


class TestInputFunctions:
    """Test input helper functions."""
    
    def test_get_input_with_default(self):
        """Test get_input with default value."""
        with patch("builtins.input", return_value=""):
            result = get_input("Enter value", default="default_value")
            assert result == "default_value"
    
    def test_get_input_with_user_input(self):
        """Test get_input with user input."""
        with patch("builtins.input", return_value="user_input"):
            result = get_input("Enter value", default="default")
            assert result == "user_input"
    
    def test_get_input_eof_error(self):
        """Test get_input handles EOFError."""
        with patch("builtins.input", side_effect=EOFError):
            result = get_input("Enter value", default="fallback")
            assert result == "fallback"
    
    def test_get_yes_no_default_yes(self):
        """Test get_yes_no with default yes."""
        with patch("builtins.input", return_value=""):
            result = get_yes_no("Confirm?", default=True)
            assert result is True
    
    def test_get_yes_no_default_no(self):
        """Test get_yes_no with default no."""
        with patch("builtins.input", return_value=""):
            result = get_yes_no("Confirm?", default=False)
            assert result is False
    
    def test_get_yes_no_user_yes(self):
        """Test get_yes_no with user yes."""
        with patch("builtins.input", return_value="y"):
            result = get_yes_no("Confirm?", default=False)
            assert result is True
    
    def test_get_yes_no_user_no(self):
        """Test get_yes_no with user no."""
        with patch("builtins.input", return_value="n"):
            result = get_yes_no("Confirm?", default=True)
            assert result is False


class TestSelectOption:
    """Test select_option function."""
    
    def test_select_option_valid_choice(self):
        """Test select_option with valid choice."""
        options = ["Option 1", "Option 2", "Option 3"]
        
        with patch("builtins.input", return_value="2"):
            result = select_option("Select:", options, default=0)
            assert result == 1  # 0-indexed
    
    def test_select_option_invalid_then_valid(self):
        """Test select_option with invalid then valid choice."""
        options = ["Option 1", "Option 2"]
        
        with patch("builtins.input", side_effect=["5", "1"]):
            result = select_option("Select:", options, default=0)
            assert result == 0


class TestSetupWizard:
    """Test SetupWizard class."""
    
    def test_wizard_initialization(self):
        """Test wizard initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            wizard = SetupWizard(workspace_dir=Path(tmpdir))
            
            assert wizard.workspace_dir == Path(tmpdir)
            assert wizard.config is not None
            assert wizard.detected_hosts == []
    
    def test_wizard_default_workspace(self):
        """Test wizard with default workspace."""
        wizard = SetupWizard()
        
        assert wizard.workspace_dir == Path.cwd()
    
    def test_wizard_run_catches_keyboard_interrupt(self):
        """Test that wizard catches KeyboardInterrupt."""
        with tempfile.TemporaryDirectory() as tmpdir:
            wizard = SetupWizard(workspace_dir=Path(tmpdir))
            
            with patch.object(wizard, "_step_detect_hosts", side_effect=KeyboardInterrupt):
                with pytest.raises(SystemExit):
                    wizard.run()
    
    def test_step_detect_hosts(self, capsys):
        """Test _step_detect_hosts method."""
        with tempfile.TemporaryDirectory() as tmpdir:
            wizard = SetupWizard(workspace_dir=Path(tmpdir))
            
            # Mock detect_llm_hosts to return empty list
            with patch("setup.wizard.detect_llm_hosts", return_value=[]):
                wizard._step_detect_hosts()
            
            captured = capsys.readouterr()
            assert "Detecting LLM Hosts" in captured.out
    
    def test_step_select_host_custom_endpoint(self):
        """Test _step_select_host with custom endpoint."""
        with tempfile.TemporaryDirectory() as tmpdir:
            wizard = SetupWizard(workspace_dir=Path(tmpdir))
            
            # No detected hosts
            wizard.detected_hosts = []
            
            with patch("setup.wizard.get_input", return_value="http://localhost:8000/v1/chat/completions"):
                with patch("setup.wizard.validate_endpoint", return_value=(True, "")):
                    wizard._step_select_host()
            
            assert "localhost" in wizard.config.llm_endpoint
    
    def test_step_configure_features(self):
        """Test _step_configure_features method."""
        with tempfile.TemporaryDirectory() as tmpdir:
            wizard = SetupWizard(workspace_dir=Path(tmpdir))
            
            with patch("setup.wizard.get_yes_no", return_value=True):
                wizard._step_configure_features()
            
            assert wizard.config.enable_ironclaw is True
            assert wizard.config.enable_searxng is True
    
    def test_step_configure_resources(self):
        """Test _step_configure_resources method."""
        with tempfile.TemporaryDirectory() as tmpdir:
            wizard = SetupWizard(workspace_dir=Path(tmpdir))
            
            with patch("setup.wizard.get_input", return_value="8192"):
                wizard._step_configure_resources()
            
            assert wizard.config.memory_limit_mb == 8192
    
    def test_step_configure_security(self):
        """Test _step_configure_security method."""
        with tempfile.TemporaryDirectory() as tmpdir:
            wizard = SetupWizard(workspace_dir=Path(tmpdir))
            
            with patch("setup.wizard.get_input", side_effect=["test_user", "test_password123"]):
                wizard._step_configure_security()
            
            assert wizard.config.postgres_user == "test_user"
            assert wizard.config.postgres_password == "test_password123"
    
    def test_step_review_and_save(self, capsys):
        """Test _step_review_and_save method."""
        with tempfile.TemporaryDirectory() as tmpdir:
            wizard = SetupWizard(workspace_dir=Path(tmpdir))
            
            with patch("setup.wizard.get_yes_no", return_value=False):
                wizard._step_review_and_save()
            
            captured = capsys.readouterr()
            assert "Review" in captured.out or "Configuration" in captured.out
