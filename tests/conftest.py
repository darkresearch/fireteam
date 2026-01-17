"""Shared pytest fixtures for fireteam tests."""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch


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
def mock_cli_result():
    """Create a mock CLIResult for testing."""
    from fireteam.claude_cli import CLIResult
    return CLIResult(
        success=True,
        output="Task completed successfully.\nCOMPLETION: 100%",
        session_id="test-session-123",
    )


@pytest.fixture
def mock_cli_query(mock_cli_result):
    """Mock the run_cli_query function."""
    async def _mock_query(*args, **kwargs):
        return mock_cli_result
    return _mock_query


@pytest.fixture
def mock_execution_result():
    """Create a mock ExecutionResult for testing."""
    from fireteam.models import ExecutionResult, ExecutionMode
    return ExecutionResult(
        success=True,
        mode=ExecutionMode.SINGLE_TURN,
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
        help="Run integration tests that require Claude Code CLI"
    )


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests (fast, no external deps)")
    config.addinivalue_line("markers", "integration: Integration tests (require Claude CLI)")
    config.addinivalue_line("markers", "slow: Slow running tests")


def pytest_collection_modifyitems(config, items):
    """Skip integration tests unless --run-integration is passed."""
    if not config.getoption("--run-integration"):
        skip_integration = pytest.mark.skip(reason="need --run-integration option to run")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)
