"""Unit tests for the fireteam API."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

from fireteam.api import (
    execute,
    ExecutionMode,
    ExecutionResult,
    COMPLEXITY_TO_MODE,
    EXECUTOR_PROMPT,
    REVIEWER_PROMPT,
    PLANNER_PROMPT,
    _extract_completion,
    _run_query,
)
from fireteam.complexity import ComplexityLevel


class TestExecutionMode:
    """Tests for ExecutionMode enum."""

    def test_modes_exist(self):
        """All expected execution modes exist."""
        assert ExecutionMode.SINGLE_TURN.value == "single_turn"
        assert ExecutionMode.SIMPLE.value == "simple"
        assert ExecutionMode.MODERATE.value == "moderate"
        assert ExecutionMode.FULL.value == "full"

    def test_modes_count(self):
        """Exactly 4 execution modes exist."""
        assert len(ExecutionMode) == 4


class TestExecutionResult:
    """Tests for ExecutionResult dataclass."""

    def test_success_result(self):
        """Can create successful result."""
        result = ExecutionResult(
            success=True,
            mode=ExecutionMode.SIMPLE,
            output="Done",
            completion_percentage=100,
        )
        assert result.success is True
        assert result.mode == ExecutionMode.SIMPLE
        assert result.output == "Done"
        assert result.completion_percentage == 100

    def test_failure_result(self):
        """Can create failure result."""
        result = ExecutionResult(
            success=False,
            mode=ExecutionMode.FULL,
            error="Something went wrong",
        )
        assert result.success is False
        assert result.error == "Something went wrong"

    def test_default_values(self):
        """Default values are correct."""
        result = ExecutionResult(success=True, mode=ExecutionMode.SIMPLE)
        assert result.output is None
        assert result.error is None
        assert result.completion_percentage == 0
        assert result.metadata == {}


class TestComplexityToMode:
    """Tests for complexity to mode mapping."""

    def test_trivial_maps_to_single_turn(self):
        """TRIVIAL maps to SINGLE_TURN."""
        assert COMPLEXITY_TO_MODE[ComplexityLevel.TRIVIAL] == ExecutionMode.SINGLE_TURN

    def test_simple_maps_to_simple(self):
        """SIMPLE maps to SIMPLE."""
        assert COMPLEXITY_TO_MODE[ComplexityLevel.SIMPLE] == ExecutionMode.SIMPLE

    def test_moderate_maps_to_moderate(self):
        """MODERATE maps to MODERATE."""
        assert COMPLEXITY_TO_MODE[ComplexityLevel.MODERATE] == ExecutionMode.MODERATE

    def test_complex_maps_to_full(self):
        """COMPLEX maps to FULL."""
        assert COMPLEXITY_TO_MODE[ComplexityLevel.COMPLEX] == ExecutionMode.FULL

    def test_all_complexity_levels_mapped(self):
        """All complexity levels have a mode mapping."""
        for level in ComplexityLevel:
            assert level in COMPLEXITY_TO_MODE


class TestPrompts:
    """Tests for system prompts."""

    def test_executor_prompt_exists(self):
        """Executor prompt exists and contains key guidance."""
        assert len(EXECUTOR_PROMPT) > 0
        assert "quality" in EXECUTOR_PROMPT.lower() or "work" in EXECUTOR_PROMPT.lower()

    def test_reviewer_prompt_exists(self):
        """Reviewer prompt exists and asks for completion percentage."""
        assert len(REVIEWER_PROMPT) > 0
        assert "COMPLETION" in REVIEWER_PROMPT

    def test_planner_prompt_exists(self):
        """Planner prompt exists and asks for analysis."""
        assert len(PLANNER_PROMPT) > 0
        assert "plan" in PLANNER_PROMPT.lower()


class TestExtractCompletion:
    """Tests for completion percentage extraction."""

    def test_extracts_completion_format(self):
        """Extracts COMPLETION: XX% format."""
        text = "Review complete.\nCOMPLETION: 95%\nGood work."
        assert _extract_completion(text) == 95

    def test_handles_lowercase(self):
        """Handles lowercase completion."""
        text = "completion: 80%"
        assert _extract_completion(text) == 80

    def test_handles_mixed_case(self):
        """Handles mixed case."""
        text = "Completion: 75%"
        assert _extract_completion(text) == 75

    def test_fallback_to_any_percentage(self):
        """Falls back to any percentage in text."""
        text = "I'd say this is about 60% done."
        assert _extract_completion(text) == 60

    def test_defaults_to_50(self):
        """Defaults to 50 when no percentage found."""
        text = "I can't really say how done this is."
        assert _extract_completion(text) == 50


class TestExecute:
    """Tests for main execute function."""

    @pytest.mark.asyncio
    async def test_auto_detects_complexity(self, project_dir):
        """Auto-detects complexity when mode is None."""
        mock_message = MagicMock()
        mock_message.result = "Task completed."

        async def mock_query(*args, **kwargs):
            yield mock_message

        with patch("fireteam.api.estimate_complexity", return_value=ComplexityLevel.SIMPLE):
            with patch("fireteam.api.query", mock_query):
                result = await execute(
                    project_dir=project_dir,
                    goal="Fix the bug",
                    mode=None,
                    run_tests=False,
                )
                assert result.mode == ExecutionMode.SIMPLE

    @pytest.mark.asyncio
    async def test_uses_specified_mode(self, project_dir):
        """Uses specified mode when provided."""
        mock_message = MagicMock()
        mock_message.result = "Task completed."

        async def mock_query(*args, **kwargs):
            yield mock_message

        with patch("fireteam.api.query", mock_query):
            result = await execute(
                project_dir=project_dir,
                goal="Fix the bug",
                mode=ExecutionMode.SINGLE_TURN,
                run_tests=False,
            )
            assert result.mode == ExecutionMode.SINGLE_TURN

    @pytest.mark.asyncio
    async def test_single_turn_mode(self, project_dir):
        """SINGLE_TURN mode makes single SDK call."""
        mock_message = MagicMock()
        mock_message.result = "Done in one turn."

        async def mock_query(*args, **kwargs):
            yield mock_message

        with patch("fireteam.api.query", mock_query):
            result = await execute(
                project_dir=project_dir,
                goal="Fix typo",
                mode=ExecutionMode.SINGLE_TURN,
                run_tests=False,
            )
            assert result.success is True
            assert result.completion_percentage == 100

    @pytest.mark.asyncio
    async def test_simple_mode(self, project_dir):
        """SIMPLE mode executes without review."""
        mock_message = MagicMock()
        mock_message.result = "Executed the task."

        async def mock_query(*args, **kwargs):
            yield mock_message

        with patch("fireteam.api.query", mock_query):
            result = await execute(
                project_dir=project_dir,
                goal="Add logging",
                mode=ExecutionMode.SIMPLE,
                run_tests=False,
            )
            assert result.success is True
            assert result.mode == ExecutionMode.SIMPLE

    @pytest.mark.asyncio
    async def test_moderate_mode_includes_review(self, project_dir):
        """MODERATE mode includes execution and review."""
        call_count = 0

        async def mock_query(prompt, options):
            nonlocal call_count
            call_count += 1
            mock_message = MagicMock()
            if call_count == 1:
                mock_message.result = "Executed."
            else:
                mock_message.result = "COMPLETION: 90%"
            yield mock_message

        with patch("fireteam.api.query", mock_query):
            result = await execute(
                project_dir=project_dir,
                goal="Refactor module",
                mode=ExecutionMode.MODERATE,
                run_tests=False,
            )
            assert result.success is True
            assert call_count == 2  # Execution + Review
            assert "review" in result.metadata or result.completion_percentage > 0

    @pytest.mark.asyncio
    async def test_handles_execution_error(self, project_dir):
        """Handles execution errors gracefully."""
        async def mock_query(*args, **kwargs):
            raise Exception("SDK error")
            yield  # Never reached

        with patch("fireteam.api.query", mock_query):
            result = await execute(
                project_dir=project_dir,
                goal="Do something",
                mode=ExecutionMode.SIMPLE,
                run_tests=False,
            )
            assert result.success is False
            assert result.error is not None

    @pytest.mark.asyncio
    async def test_includes_context_in_prompt(self, project_dir):
        """Includes context in the prompt when provided."""
        captured_prompt = None

        async def mock_query(prompt, options):
            nonlocal captured_prompt
            captured_prompt = prompt
            mock_message = MagicMock()
            mock_message.result = "Done."
            yield mock_message

        with patch("fireteam.api.query", mock_query):
            await execute(
                project_dir=project_dir,
                goal="Fix bug",
                context="Error: NullPointer at line 42",
                mode=ExecutionMode.SINGLE_TURN,
                run_tests=False,
            )
            assert "NullPointer" in captured_prompt

    @pytest.mark.asyncio
    async def test_resolves_path(self, project_dir):
        """Resolves project_dir to absolute path."""
        mock_message = MagicMock()
        mock_message.result = "Done."
        captured_options = None

        async def mock_query(prompt, options):
            nonlocal captured_options
            captured_options = options
            yield mock_message

        with patch("fireteam.api.query", mock_query):
            await execute(
                project_dir=str(project_dir),
                goal="Task",
                mode=ExecutionMode.SINGLE_TURN,
                run_tests=False,
            )
            # Should be absolute path
            assert Path(captured_options.cwd).is_absolute()


class TestRunQuery:
    """Tests for _run_query helper."""

    @pytest.mark.asyncio
    async def test_extracts_result_attribute(self):
        """Extracts result from message with result attribute."""
        mock_message = MagicMock()
        mock_message.result = "The result."

        async def mock_query(*args, **kwargs):
            yield mock_message

        with patch("fireteam.api.query", mock_query):
            options = MagicMock()
            result = await _run_query("prompt", options)
            assert result == "The result."

    @pytest.mark.asyncio
    async def test_extracts_content_string(self):
        """Extracts content when it's a string."""
        mock_message = MagicMock(spec=["content"])
        mock_message.content = "String content."
        del mock_message.result  # No result attribute

        async def mock_query(*args, **kwargs):
            yield mock_message

        with patch("fireteam.api.query", mock_query):
            options = MagicMock()
            result = await _run_query("prompt", options)
            assert "String content" in result

    @pytest.mark.asyncio
    async def test_extracts_content_list_with_text(self):
        """Extracts text from content list."""
        text_block = MagicMock()
        text_block.text = "Text from block."

        mock_message = MagicMock(spec=["content"])
        mock_message.content = [text_block]
        del mock_message.result

        async def mock_query(*args, **kwargs):
            yield mock_message

        with patch("fireteam.api.query", mock_query):
            options = MagicMock()
            result = await _run_query("prompt", options)
            assert "Text from block" in result
