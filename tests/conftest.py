"""Shared pytest fixtures for all tests."""

import pytest
import tempfile
import shutil
import os
from pathlib import Path


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
def isolated_system_dirs(isolated_tmp_dir):
    """Create isolated state/logs/memory dirs."""
    system_dir = isolated_tmp_dir / "system"
    (system_dir / "state").mkdir(parents=True)
    (system_dir / "logs").mkdir(parents=True)
    (system_dir / "memory").mkdir(parents=True)
    return system_dir


@pytest.fixture
def lightweight_memory_manager(isolated_system_dirs):
    """MemoryManager with lightweight embedding model."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
    from memory.manager import MemoryManager
    
    return MemoryManager(
        memory_dir=str(isolated_system_dirs / "memory"),
        embedding_model='sentence-transformers/all-MiniLM-L6-v2'
    )


def pytest_addoption(parser):
    """Add custom command-line options."""
    parser.addoption(
        "--keep-artifacts",
        action="store_true",
        help="Keep test artifacts on failure for debugging"
    )


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "lightweight: Lightweight tests with small models")
    config.addinivalue_line("markers", "e2e: End-to-end tests with real subprocesses")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "integration: Integration tests with external systems")

