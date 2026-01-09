"""
SDK Hooks for automatic quality enforcement.

Provides PostToolUse hooks that run tests after code changes,
giving Claude immediate feedback when tests fail.
"""

import asyncio
import logging
import subprocess
from pathlib import Path
from typing import Any

from claude_agent_sdk import HookMatcher


# Default test commands to try (in order of preference)
DEFAULT_TEST_COMMANDS = [
    ["pytest", "-x", "--tb=short"],  # Python
    ["npm", "test"],                  # Node.js
    ["cargo", "test"],                # Rust
    ["go", "test", "./..."],          # Go
    ["make", "test"],                 # Makefile-based
]


def detect_test_command(project_dir: Path) -> list[str] | None:
    """
    Detect the appropriate test command for a project.
    Returns None if no test framework is detected.
    """
    # Check for Python (pytest/pyproject.toml)
    if (project_dir / "pytest.ini").exists() or \
       (project_dir / "pyproject.toml").exists() or \
       (project_dir / "setup.py").exists() or \
       (project_dir / "tests").is_dir():
        return ["pytest", "-x", "--tb=short"]

    # Check for Node.js
    if (project_dir / "package.json").exists():
        return ["npm", "test"]

    # Check for Rust
    if (project_dir / "Cargo.toml").exists():
        return ["cargo", "test"]

    # Check for Go
    if (project_dir / "go.mod").exists():
        return ["go", "test", "./..."]

    # Check for Makefile with test target
    makefile = project_dir / "Makefile"
    if makefile.exists():
        content = makefile.read_text()
        if "test:" in content:
            return ["make", "test"]

    return None


def run_tests_sync(project_dir: Path, test_command: list[str], timeout: int = 120) -> tuple[bool, str]:
    """
    Run tests synchronously and return (success, output).
    """
    try:
        result = subprocess.run(
            test_command,
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        output = result.stdout + result.stderr
        success = result.returncode == 0

        return success, output

    except subprocess.TimeoutExpired:
        return False, f"Tests timed out after {timeout}s"
    except FileNotFoundError:
        return False, f"Test command not found: {test_command[0]}"
    except Exception as e:
        return False, f"Error running tests: {e}"


async def run_tests_after_edit(input_data: dict, tool_use_id: str | None, context: Any) -> dict:
    """
    PostToolUse hook: Run tests after any Edit/Write operation.

    Provides feedback to Claude if tests fail, allowing immediate correction.
    """
    # Only process PostToolUse events
    if input_data.get("hook_event_name") != "PostToolUse":
        return {}

    tool_name = input_data.get("tool_name", "")

    # Only run for file modification tools
    if tool_name not in ("Edit", "Write"):
        return {}

    # Get project directory from context
    cwd = input_data.get("cwd", "")
    if not cwd:
        return {}

    project_dir = Path(cwd)

    # Detect test command
    test_command = detect_test_command(project_dir)
    if not test_command:
        # No test framework detected - skip
        return {}

    # Get the file that was modified
    tool_input = input_data.get("tool_input", {})
    modified_file = tool_input.get("file_path", "unknown")

    # Run tests
    success, output = await asyncio.to_thread(
        run_tests_sync, project_dir, test_command
    )

    if success:
        # Tests passed - no feedback needed
        return {}

    # Tests failed - provide feedback to Claude
    # Truncate output if too long
    max_output_len = 2000
    if len(output) > max_output_len:
        output = output[:max_output_len] + "\n... (output truncated)"

    feedback = f"""Tests failed after editing {modified_file}.

Command: {' '.join(test_command)}

Output:
{output}

Please fix the failing tests before continuing."""

    return {
        "hookSpecificOutput": {
            "hookEventName": input_data["hook_event_name"],
            "additionalContext": feedback,
        }
    }


async def log_tool_usage(input_data: dict, tool_use_id: str | None, context: Any) -> dict:
    """
    PostToolUse hook: Log all tool usage for debugging/auditing.
    """
    if input_data.get("hook_event_name") != "PostToolUse":
        return {}

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    logger = logging.getLogger("fireteam.hooks")
    logger.debug(f"Tool used: {tool_name}, input: {tool_input}")

    return {}


async def block_user_questions(input_data: dict, tool_use_id: str | None, context: Any) -> dict:
    """
    PreToolUse hook: Block AskUserQuestion in autonomous mode.

    Fireteam runs autonomously without user interaction. If Claude tries to
    ask a clarifying question, we deny it and tell Claude to proceed with
    its best judgment.

    This is a belt+suspenders approach - AskUserQuestion should also not be
    in allowed_tools, but this hook catches it if it somehow gets through.
    """
    if input_data.get("hook_event_name") != "PreToolUse":
        return {}

    tool_name = input_data.get("tool_name", "")

    if tool_name == "AskUserQuestion":
        return {
            "hookSpecificOutput": {
                "hookEventName": input_data["hook_event_name"],
                "permissionDecision": "deny",
                "permissionDecisionReason": (
                    "This is an autonomous execution - no user is available to answer questions. "
                    "Proceed with your best judgment based on the available context. "
                    "Make reasonable assumptions and document them in your work."
                ),
            }
        }

    return {}


def create_test_hooks(
    test_command: list[str] | None = None,
    test_timeout: int = 120,
) -> dict[str, list]:
    """
    Create hook configuration for automatic test running.

    Args:
        test_command: Explicit test command to use (auto-detected if None)
        test_timeout: Timeout in seconds for test execution

    Returns:
        Hook configuration dict to pass to ClaudeAgentOptions
    """

    async def test_hook(input_data: dict, tool_use_id: str | None, context: Any) -> dict:
        """Custom test hook with configured command and timeout."""
        if input_data.get("hook_event_name") != "PostToolUse":
            return {}

        tool_name = input_data.get("tool_name", "")
        if tool_name not in ("Edit", "Write"):
            return {}

        cwd = input_data.get("cwd", "")
        if not cwd:
            return {}

        project_dir = Path(cwd)

        # Use configured command or auto-detect
        cmd = test_command or detect_test_command(project_dir)
        if not cmd:
            return {}

        tool_input = input_data.get("tool_input", {})
        modified_file = tool_input.get("file_path", "unknown")

        success, output = await asyncio.to_thread(
            run_tests_sync, project_dir, cmd, test_timeout
        )

        if success:
            return {}

        max_output_len = 2000
        if len(output) > max_output_len:
            output = output[:max_output_len] + "\n... (output truncated)"

        feedback = f"""Tests failed after editing {modified_file}.

Command: {' '.join(cmd)}

Output:
{output}

Please fix the failing tests before continuing."""

        return {
            "hookSpecificOutput": {
                "hookEventName": input_data["hook_event_name"],
                "additionalContext": feedback,
            }
        }

    return {
        "PreToolUse": [
            # Block AskUserQuestion in autonomous mode
            HookMatcher(matcher="AskUserQuestion", hooks=[block_user_questions])
        ],
        "PostToolUse": [
            HookMatcher(matcher="Edit|Write", hooks=[test_hook])
        ]
    }


# Pre-configured hook sets for common use cases
QUALITY_HOOKS = {
    "PreToolUse": [
        # Block AskUserQuestion in autonomous mode (belt+suspenders)
        HookMatcher(matcher="AskUserQuestion", hooks=[block_user_questions])
    ],
    "PostToolUse": [
        # Run tests after code changes
        HookMatcher(matcher="Edit|Write", hooks=[run_tests_after_edit])
    ]
}

AUTONOMOUS_HOOKS = {
    "PreToolUse": [
        # Block AskUserQuestion in autonomous mode
        HookMatcher(matcher="AskUserQuestion", hooks=[block_user_questions])
    ],
}

DEBUG_HOOKS = {
    "PostToolUse": [
        HookMatcher(hooks=[log_tool_usage])
    ]
}
