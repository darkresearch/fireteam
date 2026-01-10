"""Smoke tests for fireteam using the sample_cli fixture.

These tests run fireteam against a real (toy) project to verify
end-to-end functionality across all execution modes.

Run with: pytest tests/e2e/test_smoke.py --run-integration -v
"""

import os
import shutil
import subprocess
import pytest
from pathlib import Path

from fireteam.api import execute
from fireteam.models import ExecutionMode


# Path to the sample_cli fixture
FIXTURE_SOURCE = Path(__file__).parent.parent / "fixtures" / "sample_cli"


@pytest.fixture
def sample_cli_project(isolated_tmp_dir):
    """Copy sample_cli fixture to a temp directory for modification.

    Each test gets a fresh copy so they don't interfere with each other.
    """
    dest = isolated_tmp_dir / "sample_cli"
    shutil.copytree(FIXTURE_SOURCE, dest, ignore=shutil.ignore_patterns(".venv", "__pycache__", "*.pyc", ".pytest_cache", "uv.lock"))

    # Initialize uv in the copied project
    subprocess.run(
        ["uv", "sync", "--extra", "dev"],
        cwd=dest,
        capture_output=True,
        timeout=60,
    )

    return dest


def run_tests_in_project(project_dir: Path) -> tuple[bool, str]:
    """Run pytest in the project directory and return (success, output)."""
    result = subprocess.run(
        ["uv", "run", "pytest", "-v"],
        cwd=project_dir,
        capture_output=True,
        text=True,
        timeout=60,
    )
    return result.returncode == 0, result.stdout + result.stderr


def run_cli_command(project_dir: Path, *args) -> tuple[int, str, str]:
    """Run the calc CLI and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        ["uv", "run", "calc", *args],
        cwd=project_dir,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.returncode, result.stdout.strip(), result.stderr


@pytest.mark.smoke
@pytest.mark.integration
async def test_bugfix_division_by_zero(sample_cli_project):
    """Test that fireteam can fix the division by zero bug.

    Task: Fix the divide function to handle division by zero gracefully.
    Mode: MODERATE (execute -> review loop)
    """
    # Verify the bug exists before fix
    returncode, stdout, stderr = run_cli_command(sample_cli_project, "divide", "10", "0")
    assert returncode != 0, "Bug should exist before fix"
    assert "ZeroDivisionError" in stderr

    # Run fireteam to fix the bug
    result = await execute(
        project_dir=sample_cli_project,
        goal="Fix the division by zero bug in the calculator. The divide function in ops.py should return an error message instead of crashing when dividing by zero.",
        context="Currently `calc divide 10 0` crashes with ZeroDivisionError. It should print an error message and exit gracefully.",
        mode=ExecutionMode.MODERATE,
        max_iterations=3,
    )

    assert result.success, f"Execution failed: {result.error or result.output}"

    # Verify the fix works
    returncode, stdout, stderr = run_cli_command(sample_cli_project, "divide", "10", "0")
    assert returncode == 0 or "error" in stdout.lower() or "error" in stderr.lower(), \
        f"Division by zero should be handled gracefully. Got: {stdout} {stderr}"

    # Verify tests still pass
    tests_pass, test_output = run_tests_in_project(sample_cli_project)
    assert tests_pass, f"Tests should pass after fix: {test_output}"


@pytest.mark.smoke
@pytest.mark.integration
async def test_add_power_operation(sample_cli_project):
    """Test that fireteam can add a new power operation.

    Task: Add a power operation that raises a number to an exponent.
    Mode: MODERATE (execute -> review loop)
    """
    # Verify power operation doesn't exist
    returncode, stdout, stderr = run_cli_command(sample_cli_project, "power", "2", "3")
    assert returncode != 0, "Power operation should not exist yet"

    # Run fireteam to add the feature
    result = await execute(
        project_dir=sample_cli_project,
        goal="Add a power operation to the calculator that raises a number to an exponent.",
        context="Add a `power` function to ops.py and wire it up in main.py so `calc power 2 3` returns 8.",
        mode=ExecutionMode.MODERATE,
        max_iterations=3,
    )

    assert result.success, f"Execution failed: {result.error or result.output}"

    # Verify the feature works
    returncode, stdout, stderr = run_cli_command(sample_cli_project, "power", "2", "3")
    assert returncode == 0, f"Power command should work. Got: {stderr}"
    assert "8" in stdout, f"2^3 should equal 8. Got: {stdout}"

    # Verify tests still pass
    tests_pass, test_output = run_tests_in_project(sample_cli_project)
    assert tests_pass, f"Tests should pass after adding power: {test_output}"


@pytest.mark.smoke
@pytest.mark.integration
async def test_refactor_history_to_class(sample_cli_project):
    """Test that fireteam can refactor the history module.

    Task: Refactor history.py to use a class instead of global state.
    Mode: FULL (plan -> execute -> review loop)
    """
    # Read the original history.py to verify it uses global state
    history_path = sample_cli_project / "src" / "calculator" / "history.py"
    original_content = history_path.read_text()
    assert "_history: list[str] = []" in original_content, "Should have global state before refactor"

    # Run fireteam to refactor
    result = await execute(
        project_dir=sample_cli_project,
        goal="Refactor the history module to use a class instead of global state.",
        context="The history.py file uses a module-level _history list. Refactor it to use a History class that encapsulates the state. Keep the same public API (add_entry, get_history, clear_history, get_last_entry).",
        mode=ExecutionMode.FULL,
        max_iterations=3,
    )

    assert result.success, f"Execution failed: {result.error or result.output}"

    # Verify the refactor was applied
    refactored_content = history_path.read_text()
    assert "class History" in refactored_content or "class CommandHistory" in refactored_content, \
        f"Should have a History class after refactor. Content:\n{refactored_content}"

    # Verify tests still pass
    tests_pass, test_output = run_tests_in_project(sample_cli_project)
    assert tests_pass, f"Tests should pass after refactor: {test_output}"


@pytest.mark.smoke
@pytest.mark.integration
async def test_add_verbose_flag(sample_cli_project):
    """Test that fireteam can add a verbose flag.

    Task: Add a --verbose flag that shows the operation before the result.
    Mode: FULL (plan -> execute -> review loop)
    """
    # Run fireteam to add the verbose flag
    result = await execute(
        project_dir=sample_cli_project,
        goal="Add a --verbose flag that shows the operation being performed before the result.",
        context="When --verbose is passed, the output should show something like 'Adding 2 + 3 = 5' instead of just '5'. The flag should work with all operations.",
        mode=ExecutionMode.FULL,
        max_iterations=3,
    )

    assert result.success, f"Execution failed: {result.error or result.output}"

    # Verify the verbose flag works
    returncode, stdout, stderr = run_cli_command(sample_cli_project, "--verbose", "add", "2", "3")
    assert returncode == 0, f"Verbose add should work. stderr: {stderr}"
    # Check for some indication of verbosity (the exact format may vary)
    output_lower = stdout.lower()
    assert "5" in stdout, f"Result 5 should be in output. Got: {stdout}"
    assert any(word in output_lower for word in ["add", "+"]), \
        f"Verbose output should mention the operation. Got: {stdout}"

    # Verify tests still pass
    tests_pass, test_output = run_tests_in_project(sample_cli_project)
    assert tests_pass, f"Tests should pass after adding verbose: {test_output}"
