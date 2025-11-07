"""
Unit tests for configuration module.
Tests environment variable loading, validation, and configuration values.
"""

import pytest
import os
from unittest.mock import patch
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestConfig:
    """Test configuration module."""

    def test_system_directories(self):
        """Test that system directories are configured."""
        import config
        
        # System directory should be set
        assert config.SYSTEM_DIR is not None
        assert isinstance(config.SYSTEM_DIR, str)
        
        # Derived directories should be set
        assert config.STATE_DIR is not None
        assert config.LOGS_DIR is not None
        assert config.CLI_DIR is not None
        assert config.MEMORY_DIR is not None
        
        # Paths should be properly constructed
        assert config.SYSTEM_DIR in config.STATE_DIR
        assert config.SYSTEM_DIR in config.LOGS_DIR
        assert config.SYSTEM_DIR in config.CLI_DIR
        assert config.SYSTEM_DIR in config.MEMORY_DIR

    @patch.dict(os.environ, {"FIRETEAM_DIR": "/custom/path"}, clear=False)
    def test_custom_system_dir(self):
        """Test FIRETEAM_DIR environment variable override."""
        # Need to reimport to pick up env var
        import importlib
        import config as config_module
        importlib.reload(config_module)
        
        # Should use custom path
        assert "/custom/path" in config_module.SYSTEM_DIR or config_module.SYSTEM_DIR == "/custom/path"

    def test_anthropic_api_key_function(self):
        """Test Anthropic API key lazy loading."""
        import config
        
        # Should have the function
        assert hasattr(config, 'get_anthropic_api_key')
        assert callable(config.get_anthropic_api_key)
        
        # If ANTHROPIC_API_KEY is set, should return it
        if os.getenv("ANTHROPIC_API_KEY"):
            api_key = config.get_anthropic_api_key()
            assert api_key is not None
            assert isinstance(api_key, str)
            assert len(api_key) > 0

    @patch.dict(os.environ, {}, clear=False)
    @patch("os.getenv", side_effect=lambda key, default=None: default if key == "ANTHROPIC_API_KEY" else os.environ.get(key, default))
    def test_anthropic_api_key_missing(self, mock_getenv):
        """Test that missing API key raises error when accessed."""
        import importlib
        import config as config_module
        importlib.reload(config_module)
        
        # Should raise ValueError when accessed
        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
            config_module.get_anthropic_api_key()

    def test_sdk_configuration(self):
        """Test Claude SDK configuration values."""
        import config
        
        # SDK tools should be defined
        assert hasattr(config, 'SDK_ALLOWED_TOOLS')
        assert isinstance(config.SDK_ALLOWED_TOOLS, list)
        assert len(config.SDK_ALLOWED_TOOLS) > 0
        
        # Should include essential tools
        assert "Read" in config.SDK_ALLOWED_TOOLS
        assert "Write" in config.SDK_ALLOWED_TOOLS
        assert "Bash" in config.SDK_ALLOWED_TOOLS
        
        # Permission mode should be set
        assert hasattr(config, 'SDK_PERMISSION_MODE')
        assert config.SDK_PERMISSION_MODE == "bypassPermissions"
        
        # Model should be set
        assert hasattr(config, 'SDK_MODEL')
        assert isinstance(config.SDK_MODEL, str)
        assert "claude" in config.SDK_MODEL.lower()

    def test_agent_configuration(self):
        """Test agent-related configuration."""
        import config
        
        # Retry configuration
        assert hasattr(config, 'MAX_RETRIES')
        assert isinstance(config.MAX_RETRIES, int)
        assert config.MAX_RETRIES > 0
        
        assert hasattr(config, 'RETRY_DELAY')
        assert isinstance(config.RETRY_DELAY, (int, float))
        assert config.RETRY_DELAY > 0

    def test_agent_timeouts(self):
        """Test agent timeout configurations."""
        import config
        
        # Timeouts dictionary should exist
        assert hasattr(config, 'AGENT_TIMEOUTS')
        assert isinstance(config.AGENT_TIMEOUTS, dict)
        
        # Should have timeouts for each agent type
        assert "planner" in config.AGENT_TIMEOUTS
        assert "executor" in config.AGENT_TIMEOUTS
        assert "reviewer" in config.AGENT_TIMEOUTS
        
        # All timeouts should be positive integers
        for agent_type, timeout in config.AGENT_TIMEOUTS.items():
            assert isinstance(timeout, int)
            assert timeout > 0
        
        # Executor should have longest timeout (builds, tests, etc.)
        assert config.AGENT_TIMEOUTS["executor"] >= config.AGENT_TIMEOUTS["planner"]
        assert config.AGENT_TIMEOUTS["executor"] >= config.AGENT_TIMEOUTS["reviewer"]

    def test_completion_thresholds(self):
        """Test completion threshold configurations."""
        import config
        
        # Completion threshold
        assert hasattr(config, 'COMPLETION_THRESHOLD')
        assert isinstance(config.COMPLETION_THRESHOLD, int)
        assert 0 <= config.COMPLETION_THRESHOLD <= 100
        
        # Validation checks
        assert hasattr(config, 'VALIDATION_CHECKS_REQUIRED')
        assert isinstance(config.VALIDATION_CHECKS_REQUIRED, int)
        assert config.VALIDATION_CHECKS_REQUIRED > 0

    def test_git_configuration(self):
        """Test git-related configuration."""
        import config
        
        # Git user configuration
        assert hasattr(config, 'GIT_USER_NAME')
        assert isinstance(config.GIT_USER_NAME, str)
        assert len(config.GIT_USER_NAME) > 0
        
        assert hasattr(config, 'GIT_USER_EMAIL')
        assert isinstance(config.GIT_USER_EMAIL, str)
        assert "@" in config.GIT_USER_EMAIL

    def test_logging_configuration(self):
        """Test logging configuration."""
        import config
        
        # Log level should be set
        assert hasattr(config, 'LOG_LEVEL')
        assert isinstance(config.LOG_LEVEL, str)
        assert config.LOG_LEVEL in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        
        # Log format should be set
        assert hasattr(config, 'LOG_FORMAT')
        assert isinstance(config.LOG_FORMAT, str)
        assert len(config.LOG_FORMAT) > 0

    def test_sudo_configuration(self):
        """Test sudo password configuration."""
        import config
        
        # Should have sudo password attribute
        assert hasattr(config, 'SUDO_PASSWORD')
        
        # has_sudo_access function should exist
        assert hasattr(config, 'has_sudo_access')
        assert callable(config.has_sudo_access)
        
        # Function should return boolean
        result = config.has_sudo_access()
        assert isinstance(result, bool)

    def test_memory_configuration(self):
        """Test memory system configuration."""
        import config
        
        # Memory directory should be set
        assert hasattr(config, 'MEMORY_DIR')
        assert isinstance(config.MEMORY_DIR, str)
        
        # Embedding model should be configured
        assert hasattr(config, 'MEMORY_EMBEDDING_MODEL')
        assert isinstance(config.MEMORY_EMBEDDING_MODEL, str)
        assert len(config.MEMORY_EMBEDDING_MODEL) > 0
        
        # Search limit should be set
        assert hasattr(config, 'MEMORY_SEARCH_LIMIT')
        assert isinstance(config.MEMORY_SEARCH_LIMIT, int)
        assert config.MEMORY_SEARCH_LIMIT > 0

    @patch.dict(os.environ, {"ANTHROPIC_MODEL": "claude-opus-4-20250514"}, clear=False)
    def test_model_override(self):
        """Test that model can be overridden via environment variable."""
        import importlib
        import config as config_module
        importlib.reload(config_module)
        
        # Should use overridden model
        assert config_module.SDK_MODEL == "claude-opus-4-20250514"

    @patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"}, clear=False)
    def test_log_level_override(self):
        """Test that log level can be overridden via environment variable."""
        import importlib
        import config as config_module
        importlib.reload(config_module)
        
        # Should use overridden log level
        assert config_module.LOG_LEVEL == "DEBUG"

    def test_configuration_types(self):
        """Test that all configuration values have correct types."""
        import config
        
        # String configurations
        assert isinstance(config.SYSTEM_DIR, str)
        assert isinstance(config.SDK_PERMISSION_MODE, str)
        assert isinstance(config.SDK_MODEL, str)
        assert isinstance(config.GIT_USER_NAME, str)
        assert isinstance(config.GIT_USER_EMAIL, str)
        assert isinstance(config.LOG_LEVEL, str)
        assert isinstance(config.LOG_FORMAT, str)
        assert isinstance(config.MEMORY_EMBEDDING_MODEL, str)
        
        # Integer configurations
        assert isinstance(config.MAX_RETRIES, int)
        assert isinstance(config.COMPLETION_THRESHOLD, int)
        assert isinstance(config.VALIDATION_CHECKS_REQUIRED, int)
        assert isinstance(config.MEMORY_SEARCH_LIMIT, int)
        
        # List configurations
        assert isinstance(config.SDK_ALLOWED_TOOLS, list)
        
        # Dict configurations
        assert isinstance(config.AGENT_TIMEOUTS, dict)

