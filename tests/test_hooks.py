"""Unit tests for SDK hooks."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import subprocess

from fireteam.hooks import (
    detect_test_command,
    run_tests_sync,
    run_tests_after_edit,
    block_user_questions,
    log_tool_usage,
    create_test_hooks,
    QUALITY_HOOKS,
    AUTONOMOUS_HOOKS,
    DEBUG_HOOKS,
    DEFAULT_TEST_COMMANDS,
)


class TestDetectTestCommand:
    """Tests for test command detection."""

    def test_detects_pytest_ini(self, isolated_tmp_dir):
        """Detects Python project with pytest.ini."""
        (isolated_tmp_dir / "pytest.ini").write_text("[pytest]")
        result = detect_test_command(isolated_tmp_dir)
        assert result == ["pytest", "-x", "--tb=short"]

    def test_detects_pyproject_toml(self, isolated_tmp_dir):
        """Detects Python project with pyproject.toml."""
        (isolated_tmp_dir / "pyproject.toml").write_text("[project]")
        result = detect_test_command(isolated_tmp_dir)
        assert result == ["pytest", "-x", "--tb=short"]

    def test_detects_setup_py(self, isolated_tmp_dir):
        """Detects Python project with setup.py."""
        (isolated_tmp_dir / "setup.py").write_text("from setuptools import setup")
        result = detect_test_command(isolated_tmp_dir)
        assert result == ["pytest", "-x", "--tb=short"]

    def test_detects_tests_directory(self, isolated_tmp_dir):
        """Detects Python project with tests/ directory."""
        (isolated_tmp_dir / "tests").mkdir()
        result = detect_test_command(isolated_tmp_dir)
        assert result == ["pytest", "-x", "--tb=short"]

    def test_detects_nodejs(self, isolated_tmp_dir):
        """Detects Node.js project with package.json."""
        (isolated_tmp_dir / "package.json").write_text('{"name": "test"}')
        result = detect_test_command(isolated_tmp_dir)
        assert result == ["npm", "test"]

    def test_detects_rust(self, isolated_tmp_dir):
        """Detects Rust project with Cargo.toml."""
        (isolated_tmp_dir / "Cargo.toml").write_text("[package]")
        result = detect_test_command(isolated_tmp_dir)
        assert result == ["cargo", "test"]

    def test_detects_go(self, isolated_tmp_dir):
        """Detects Go project with go.mod."""
        (isolated_tmp_dir / "go.mod").write_text("module test")
        result = detect_test_command(isolated_tmp_dir)
        assert result == ["go", "test", "./..."]

    def test_detects_makefile_with_test(self, isolated_tmp_dir):
        """Detects Makefile with test target."""
        (isolated_tmp_dir / "Makefile").write_text("test:\n\techo 'testing'")
        result = detect_test_command(isolated_tmp_dir)
        assert result == ["make", "test"]

    def test_ignores_makefile_without_test(self, isolated_tmp_dir):
        """Ignores Makefile without test target."""
        (isolated_tmp_dir / "Makefile").write_text("build:\n\techo 'building'")
        result = detect_test_command(isolated_tmp_dir)
        assert result is None

    def test_returns_none_for_unknown_project(self, isolated_tmp_dir):
        """Returns None for unknown project type."""
        result = detect_test_command(isolated_tmp_dir)
        assert result is None

    def test_python_takes_priority(self, isolated_tmp_dir):
        """Python detection takes priority over other frameworks."""
        # Create both Python and Node.js markers
        (isolated_tmp_dir / "pyproject.toml").write_text("[project]")
        (isolated_tmp_dir / "package.json").write_text('{"name": "test"}')
        result = detect_test_command(isolated_tmp_dir)
        assert result == ["pytest", "-x", "--tb=short"]


class TestRunTestsSync:
    """Tests for synchronous test execution."""

    def test_returns_success_on_zero_exit(self, isolated_tmp_dir):
        """Returns success=True when command exits with 0."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="All tests passed",
                stderr=""
            )
            success, output = run_tests_sync(isolated_tmp_dir, ["pytest"])
            assert success is True
            assert "All tests passed" in output

    def test_returns_failure_on_nonzero_exit(self, isolated_tmp_dir):
        """Returns success=False when command exits with non-zero."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="",
                stderr="1 test failed"
            )
            success, output = run_tests_sync(isolated_tmp_dir, ["pytest"])
            assert success is False
            assert "1 test failed" in output

    def test_handles_timeout(self, isolated_tmp_dir):
        """Handles test timeout gracefully."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="pytest", timeout=120)
            success, output = run_tests_sync(isolated_tmp_dir, ["pytest"], timeout=120)
            assert success is False
            assert "timed out" in output

    def test_handles_command_not_found(self, isolated_tmp_dir):
        """Handles missing command gracefully."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()
            success, output = run_tests_sync(isolated_tmp_dir, ["nonexistent"])
            assert success is False
            assert "not found" in output

    def test_handles_generic_error(self, isolated_tmp_dir):
        """Handles generic errors gracefully."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = Exception("Something went wrong")
            success, output = run_tests_sync(isolated_tmp_dir, ["pytest"])
            assert success is False
            assert "Error" in output

    def test_combines_stdout_and_stderr(self, isolated_tmp_dir):
        """Combines stdout and stderr in output."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="stdout content",
                stderr="stderr content"
            )
            success, output = run_tests_sync(isolated_tmp_dir, ["pytest"])
            assert "stdout content" in output
            assert "stderr content" in output


class TestRunTestsAfterEdit:
    """Tests for PostToolUse test running hook."""

    @pytest.mark.asyncio
    async def test_ignores_non_post_tool_use(self):
        """Ignores events that aren't PostToolUse."""
        result = await run_tests_after_edit(
            {"hook_event_name": "PreToolUse"},
            None,
            None
        )
        assert result == {}

    @pytest.mark.asyncio
    async def test_ignores_non_edit_write_tools(self):
        """Ignores tools other than Edit/Write."""
        result = await run_tests_after_edit(
            {"hook_event_name": "PostToolUse", "tool_name": "Read"},
            None,
            None
        )
        assert result == {}

    @pytest.mark.asyncio
    async def test_ignores_missing_cwd(self):
        """Ignores when cwd is not provided."""
        result = await run_tests_after_edit(
            {"hook_event_name": "PostToolUse", "tool_name": "Edit", "cwd": ""},
            None,
            None
        )
        assert result == {}

    @pytest.mark.asyncio
    async def test_ignores_no_test_framework(self, isolated_tmp_dir):
        """Ignores when no test framework is detected."""
        result = await run_tests_after_edit(
            {
                "hook_event_name": "PostToolUse",
                "tool_name": "Edit",
                "cwd": str(isolated_tmp_dir),
            },
            None,
            None
        )
        assert result == {}

    @pytest.mark.asyncio
    async def test_returns_empty_on_success(self, isolated_tmp_dir):
        """Returns empty dict when tests pass."""
        (isolated_tmp_dir / "pyproject.toml").write_text("[project]")

        with patch("fireteam.hooks.run_tests_sync", return_value=(True, "All passed")):
            result = await run_tests_after_edit(
                {
                    "hook_event_name": "PostToolUse",
                    "tool_name": "Edit",
                    "cwd": str(isolated_tmp_dir),
                    "tool_input": {"file_path": "test.py"},
                },
                None,
                None
            )
            assert result == {}

    @pytest.mark.asyncio
    async def test_returns_feedback_on_failure(self, isolated_tmp_dir):
        """Returns feedback when tests fail."""
        (isolated_tmp_dir / "pyproject.toml").write_text("[project]")

        with patch("fireteam.hooks.run_tests_sync", return_value=(False, "1 test failed")):
            result = await run_tests_after_edit(
                {
                    "hook_event_name": "PostToolUse",
                    "tool_name": "Edit",
                    "cwd": str(isolated_tmp_dir),
                    "tool_input": {"file_path": "test.py"},
                },
                None,
                None
            )
            assert "hookSpecificOutput" in result
            assert "Tests failed" in result["hookSpecificOutput"]["additionalContext"]

    @pytest.mark.asyncio
    async def test_truncates_long_output(self, isolated_tmp_dir):
        """Truncates output longer than 2000 chars."""
        (isolated_tmp_dir / "pyproject.toml").write_text("[project]")
        long_output = "x" * 3000

        with patch("fireteam.hooks.run_tests_sync", return_value=(False, long_output)):
            result = await run_tests_after_edit(
                {
                    "hook_event_name": "PostToolUse",
                    "tool_name": "Edit",
                    "cwd": str(isolated_tmp_dir),
                    "tool_input": {"file_path": "test.py"},
                },
                None,
                None
            )
            context = result["hookSpecificOutput"]["additionalContext"]
            assert "truncated" in context
            assert len(context) < 3000


class TestBlockUserQuestions:
    """Tests for PreToolUse AskUserQuestion blocking hook."""

    @pytest.mark.asyncio
    async def test_ignores_non_pre_tool_use(self):
        """Ignores events that aren't PreToolUse."""
        result = await block_user_questions(
            {"hook_event_name": "PostToolUse"},
            None,
            None
        )
        assert result == {}

    @pytest.mark.asyncio
    async def test_ignores_other_tools(self):
        """Ignores tools other than AskUserQuestion."""
        result = await block_user_questions(
            {"hook_event_name": "PreToolUse", "tool_name": "Edit"},
            None,
            None
        )
        assert result == {}

    @pytest.mark.asyncio
    async def test_blocks_ask_user_question(self):
        """Blocks AskUserQuestion with deny decision."""
        result = await block_user_questions(
            {"hook_event_name": "PreToolUse", "tool_name": "AskUserQuestion"},
            None,
            None
        )
        assert "hookSpecificOutput" in result
        output = result["hookSpecificOutput"]
        assert output["permissionDecision"] == "deny"
        assert "autonomous" in output["permissionDecisionReason"].lower()


class TestLogToolUsage:
    """Tests for debug logging hook."""

    @pytest.mark.asyncio
    async def test_ignores_non_post_tool_use(self):
        """Ignores events that aren't PostToolUse."""
        result = await log_tool_usage(
            {"hook_event_name": "PreToolUse"},
            None,
            None
        )
        assert result == {}

    @pytest.mark.asyncio
    async def test_returns_empty_dict(self):
        """Always returns empty dict (just logs)."""
        result = await log_tool_usage(
            {"hook_event_name": "PostToolUse", "tool_name": "Edit", "tool_input": {}},
            None,
            None
        )
        assert result == {}


class TestCreateTestHooks:
    """Tests for hook configuration factory."""

    def test_returns_dict_with_pre_and_post(self):
        """Returns dict with PreToolUse and PostToolUse keys."""
        hooks = create_test_hooks()
        assert "PreToolUse" in hooks
        assert "PostToolUse" in hooks

    def test_pre_tool_use_blocks_questions(self):
        """PreToolUse contains AskUserQuestion blocker."""
        hooks = create_test_hooks()
        pre_hooks = hooks["PreToolUse"]
        assert len(pre_hooks) > 0

    def test_post_tool_use_runs_tests(self):
        """PostToolUse contains test runner."""
        hooks = create_test_hooks()
        post_hooks = hooks["PostToolUse"]
        assert len(post_hooks) > 0


class TestPreConfiguredHooks:
    """Tests for pre-configured hook sets."""

    def test_quality_hooks_has_pre_and_post(self):
        """QUALITY_HOOKS has both PreToolUse and PostToolUse."""
        assert "PreToolUse" in QUALITY_HOOKS
        assert "PostToolUse" in QUALITY_HOOKS

    def test_autonomous_hooks_has_pre(self):
        """AUTONOMOUS_HOOKS has PreToolUse."""
        assert "PreToolUse" in AUTONOMOUS_HOOKS

    def test_debug_hooks_has_post(self):
        """DEBUG_HOOKS has PostToolUse."""
        assert "PostToolUse" in DEBUG_HOOKS


class TestDefaultTestCommands:
    """Tests for default test commands list."""

    def test_includes_common_frameworks(self):
        """Includes commands for common test frameworks."""
        commands_flat = [cmd[0] for cmd in DEFAULT_TEST_COMMANDS]
        assert "pytest" in commands_flat
        assert "npm" in commands_flat
        assert "cargo" in commands_flat
        assert "go" in commands_flat
        assert "make" in commands_flat
