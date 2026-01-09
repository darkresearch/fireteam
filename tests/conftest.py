"""Shared pytest fixtures for fireteam tests."""

import pytest
import tempfile
import shutil
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

# Try to import real SDK; mock only if not available
# This allows integration tests to use the real SDK while unit tests use mocks
try:
    import claude_agent_sdk
    _SDK_AVAILABLE = True
except ImportError:
    _SDK_AVAILABLE = False

    # Create a mock ClaudeAgentOptions class that stores kwargs as attributes
    class MockClaudeAgentOptions:
        """Mock class that stores constructor kwargs as attributes."""
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

    mock_sdk = MagicMock()
    mock_sdk.query = AsyncMock()
    mock_sdk.ClaudeAgentOptions = MockClaudeAgentOptions
    mock_sdk.HookMatcher = MagicMock()
    sys.modules["claude_agent_sdk"] = mock_sdk


@pytest.fixture
def isolated_tmp_dir(request):
    """Create isolated temp directory for parallel test safety."""
    import uuid
    temp_dir = tempfile.mkdtemp(prefix=f"fireteam-test-{uuid.uuid4().hex[:8]}-")
    yield Path(temp_dir)
    # Cleanup unless --keep-artifacts flag set
    if not request.config.getoption("--keep-artifacts", default=False):
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def project_dir(isolated_tmp_dir):
    """Create a mock project directory with basic structure."""
    project = isolated_tmp_dir / "project"
    project.mkdir()

    # Create basic Python project structure
    (project / "src").mkdir()
    (project / "tests").mkdir()
    (project / "pyproject.toml").write_text("""
[project]
name = "test-project"
version = "0.1.0"
""")
    (project / "src" / "main.py").write_text("""
def hello():
    return "Hello, World!"
""")

    return project


@pytest.fixture
def mock_sdk_query():
    """Mock the claude_agent_sdk.query function."""
    async def mock_query(*args, **kwargs):
        # Yield a mock message with result
        class MockMessage:
            result = "Task completed successfully."
        yield MockMessage()

    return mock_query


@pytest.fixture
def mock_execution_result():
    """Create a mock ExecutionResult for testing."""
    from fireteam.api import ExecutionResult, ExecutionMode
    return ExecutionResult(
        success=True,
        mode=ExecutionMode.SIMPLE,
        output="Task completed.",
        completion_percentage=100,
    )


def pytest_addoption(parser):
    """Add custom command-line options."""
    parser.addoption(
        "--keep-artifacts",
        action="store_true",
        help="Keep test artifacts on failure for debugging"
    )
    parser.addoption(
        "--run-integration",
        action="store_true",
        help="Run integration tests that require API keys"
    )


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests (fast, no external deps)")
    config.addinivalue_line("markers", "integration: Integration tests (require API key)")
    config.addinivalue_line("markers", "slow: Slow running tests")


def pytest_collection_modifyitems(config, items):
    """Skip integration tests unless --run-integration is passed."""
    if not config.getoption("--run-integration"):
        skip_integration = pytest.mark.skip(reason="need --run-integration option to run")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)
