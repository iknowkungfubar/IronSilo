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


class TestWizardMissingCoverage:
    """Tests for missing coverage in wizard.py."""
    
    def test_select_option_non_numeric_input(self, capsys):
        """Test select_option with non-numeric input then valid."""
        options = ["Option A", "Option B"]
        
        with patch("builtins.input", side_effect=["abc", "1"]):
            result = select_option("Pick:", options, default=0)
            assert result == 0
        
        captured = capsys.readouterr()
        assert "Please enter a number" in captured.out
    
    def test_step_detect_hosts_with_detected_hosts(self, capsys):
        """Test _step_detect_hosts with detected hosts."""
        from setup.detector import HostInfo, LLMHost
        
        with tempfile.TemporaryDirectory() as tmpdir:
            wizard = SetupWizard(workspace_dir=Path(tmpdir))
            
            mock_hosts = [
                HostInfo(
                    host_type=LLMHost.LM_STUDIO,
                    name="LM Studio",
                    default_port=1234,
                    api_path="/v1/chat/completions",
                    description="Test",
                    detected=True,
                    port=1234,
                ),
                HostInfo(
                    host_type=LLMHost.OLLAMA,
                    name="Ollama",
                    default_port=11434,
                    api_path="/v1/chat/completions",
                    description="Test",
                    detected=False,
                ),
            ]
            
            with patch("setup.wizard.detect_llm_hosts", return_value=mock_hosts):
                wizard._step_detect_hosts()
            
            captured = capsys.readouterr()
            assert "LM Studio detected" in captured.out
            assert "Ollama not detected" in captured.out
            assert len(wizard.detected_hosts) == 2
    
    def test_step_select_host_with_detected_hosts(self):
        """Test _step_select_host with detected hosts."""
        from setup.detector import HostInfo, LLMHost
        
        with tempfile.TemporaryDirectory() as tmpdir:
            wizard = SetupWizard(workspace_dir=Path(tmpdir))
            
            mock_hosts = [
                HostInfo(
                    host_type=LLMHost.LM_STUDIO,
                    name="LM Studio",
                    default_port=1234,
                    api_path="/v1/chat/completions",
                    description="Test",
                    detected=True,
                    port=1234,
                ),
            ]
            wizard.detected_hosts = mock_hosts
            
            with patch("builtins.input", return_value="1"):
                wizard._step_select_host()
            
            assert wizard.config.llm_host == LLMHost.LM_STUDIO
            assert "1234" in wizard.config.llm_endpoint
    
    def test_step_select_host_invalid_then_valid_endpoint(self):
        """Test _step_select_host with invalid then valid custom endpoint."""
        with tempfile.TemporaryDirectory() as tmpdir:
            wizard = SetupWizard(workspace_dir=Path(tmpdir))
            wizard.detected_hosts = []
            
            with patch("setup.wizard.get_input", side_effect=["invalid", "http://localhost:8000/v1/chat/completions"]):
                with patch("setup.wizard.validate_endpoint", side_effect=[(False, "bad url"), (True, "")]):
                    wizard._step_select_host()
            
            assert "localhost" in wizard.config.llm_endpoint
    
    def test_step_configure_resources_invalid_input(self, capsys):
        """Test _step_configure_resources with invalid number input."""
        with tempfile.TemporaryDirectory() as tmpdir:
            wizard = SetupWizard(workspace_dir=Path(tmpdir))
            
            with patch("setup.wizard.get_input", side_effect=["not_a_number", "2.5"]):
                wizard._step_configure_resources()
            
            captured = capsys.readouterr()
            assert "Invalid number" in captured.out or "Memory limit" in captured.out
    
    def test_step_configure_security_short_password(self, capsys):
        """Test _step_configure_security with short password warning."""
        with tempfile.TemporaryDirectory() as tmpdir:
            wizard = SetupWizard(workspace_dir=Path(tmpdir))
            
            with patch("setup.wizard.get_input", side_effect=["user", "short"]):
                wizard._step_configure_security()
            
            captured = capsys.readouterr()
            assert "short" in captured.out.lower()
    
    def test_step_review_and_save_with_validation_errors(self, capsys):
        """Test _step_review_and_save with validation errors."""
        from setup.configurator import Configurator
        
        with tempfile.TemporaryDirectory() as tmpdir:
            wizard = SetupWizard(workspace_dir=Path(tmpdir))
            wizard.config.llm_endpoint = ""  # Invalid config
            
            mock_configurator = MagicMock(spec=Configurator)
            mock_configurator.validate_config.return_value = ["LLM endpoint is required"]
            
            with patch("setup.wizard.get_yes_no", return_value=True):
                with patch("setup.wizard.Configurator", return_value=mock_configurator):
                    wizard._step_review_and_save()
            
            captured = capsys.readouterr()
            assert "errors" in captured.out.lower()
    
    def test_full_wizard_run(self, capsys):
        """Test complete wizard run flow."""
        from setup.detector import HostInfo, LLMHost
        
        with tempfile.TemporaryDirectory() as tmpdir:
            wizard = SetupWizard(workspace_dir=Path(tmpdir))
            
            mock_hosts = [
                HostInfo(
                    host_type=LLMHost.LM_STUDIO,
                    name="LM Studio",
                    default_port=1234,
                    api_path="/v1/chat/completions",
                    description="Test",
                    detected=True,
                    port=1234,
                ),
            ]
            
            # Mock all the input calls for the wizard
            input_responses = [
                "1",  # select host
                "y",  # enable ironclaw
                "y",  # enable searxng
                "4096",  # memory limit
                "2.0",  # cpu limit
                "testuser",  # db user
                "password123",  # db password
                "y",  # save config
            ]
            
            with patch("setup.wizard.detect_llm_hosts", return_value=mock_hosts):
                with patch("builtins.input", side_effect=input_responses):
                    config = wizard.run()
            
            assert config.llm_host == LLMHost.LM_STUDIO
            assert config.enable_ironclaw is True
            assert config.memory_limit_mb == 4096
    
    def test_main_with_non_interactive(self, capsys):
        """Test main function with --non-interactive flag."""
        import sys
        from setup.wizard import main
        
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(sys, "argv", ["ironsilo-setup", "--non-interactive", "--workspace", tmpdir]):
                main()
            
            captured = capsys.readouterr()
            assert "configuration" in captured.out.lower() or "written" in captured.out.lower()
    
    def test_main_interactive_mode(self):
        """Test main function in interactive mode."""
        import sys
        from setup.wizard import main
        
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_wizard = MagicMock()
            mock_wizard.run.return_value = MagicMock()
            
            with patch.object(sys, "argv", ["ironsilo-setup", "--workspace", tmpdir]):
                with patch("setup.wizard.SetupWizard", return_value=mock_wizard):
                    main()
            
            mock_wizard.run.assert_called_once()
    
    def test_get_input_no_default(self):
        """Test get_input without default value."""
        with patch("builtins.input", return_value="user_value"):
            result = get_input("Enter something", default=None)
            assert result == "user_value"
    
    def test_get_input_empty_no_default(self):
        """Test get_input with empty input and no default."""
        with patch("builtins.input", return_value=""):
            result = get_input("Enter something", default=None)
            assert result == ""
    
    def test_step_configure_resources_cpu_invalid(self, capsys):
        """Test _step_configure_resources with invalid CPU input."""
        with tempfile.TemporaryDirectory() as tmpdir:
            wizard = SetupWizard(workspace_dir=Path(tmpdir))
            
            with patch("setup.wizard.get_input", side_effect=["4096", "invalid_cpu"]):
                wizard._step_configure_resources()
            
            captured = capsys.readouterr()
            assert "Invalid number" in captured.out
    
    def test_step_review_and_save_windows_platform(self, capsys):
        """Test _step_review_and_save on Windows platform."""
        import sys as sys_module
        
        with tempfile.TemporaryDirectory() as tmpdir:
            wizard = SetupWizard(workspace_dir=Path(tmpdir))
            wizard.config.llm_endpoint = "http://localhost:8000/v1/chat/completions"
            
            mock_configurator = MagicMock()
            mock_configurator.validate_config.return_value = []
            mock_configurator.write_env_file.return_value = Path(tmpdir) / ".env"
            
            original_platform = sys_module.platform
            
            with patch("setup.wizard.get_yes_no", return_value=True):
                with patch("setup.wizard.Configurator", return_value=mock_configurator):
                    with patch.object(sys_module, "platform", "win32"):
                        wizard._step_review_and_save()
            
            captured = capsys.readouterr()
            assert "Start_Workspace.bat" in captured.out
