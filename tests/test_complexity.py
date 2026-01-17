"""Unit tests for complexity estimation."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from fireteam.complexity import ComplexityLevel, estimate_complexity
from fireteam.prompts import COMPLEXITY_PROMPT
from fireteam.claude_cli import CLIResult


class TestComplexityLevel:
    """Tests for ComplexityLevel enum."""

    def test_complexity_levels_exist(self):
        """All expected complexity levels exist."""
        assert ComplexityLevel.TRIVIAL.value == "trivial"
        assert ComplexityLevel.SIMPLE.value == "simple"
        assert ComplexityLevel.MODERATE.value == "moderate"
        assert ComplexityLevel.COMPLEX.value == "complex"

    def test_complexity_levels_count(self):
        """Exactly 4 complexity levels exist."""
        assert len(ComplexityLevel) == 4


class TestComplexityPrompt:
    """Tests for the complexity prompt template."""

    def test_prompt_has_placeholders(self):
        """Prompt contains required placeholders."""
        assert "{goal}" in COMPLEXITY_PROMPT
        assert "{context}" in COMPLEXITY_PROMPT

    def test_prompt_describes_levels(self):
        """Prompt describes all complexity levels."""
        assert "TRIVIAL" in COMPLEXITY_PROMPT
        assert "SIMPLE" in COMPLEXITY_PROMPT
        assert "MODERATE" in COMPLEXITY_PROMPT
        assert "COMPLEX" in COMPLEXITY_PROMPT

    def test_prompt_format_works(self):
        """Prompt can be formatted with goal and context."""
        formatted = COMPLEXITY_PROMPT.format(goal="Fix a bug", context="Error logs")
        assert "Fix a bug" in formatted
        assert "Error logs" in formatted


class TestEstimateComplexity:
    """Tests for estimate_complexity function."""

    @pytest.mark.asyncio
    async def test_returns_trivial(self):
        """Returns TRIVIAL when model responds with TRIVIAL."""
        mock_result = CLIResult(success=True, output="TRIVIAL", session_id="test")

        async def mock_cli_query(*args, **kwargs):
            return mock_result

        with patch("fireteam.complexity.run_cli_query", mock_cli_query):
            result = await estimate_complexity("fix typo")
            assert result == ComplexityLevel.TRIVIAL

    @pytest.mark.asyncio
    async def test_returns_simple(self):
        """Returns SIMPLE when model responds with SIMPLE."""
        mock_result = CLIResult(success=True, output="SIMPLE", session_id="test")

        async def mock_cli_query(*args, **kwargs):
            return mock_result

        with patch("fireteam.complexity.run_cli_query", mock_cli_query):
            result = await estimate_complexity("add logging")
            assert result == ComplexityLevel.SIMPLE

    @pytest.mark.asyncio
    async def test_returns_moderate(self):
        """Returns MODERATE when model responds with MODERATE."""
        mock_result = CLIResult(success=True, output="MODERATE", session_id="test")

        async def mock_cli_query(*args, **kwargs):
            return mock_result

        with patch("fireteam.complexity.run_cli_query", mock_cli_query):
            result = await estimate_complexity("refactor auth module")
            assert result == ComplexityLevel.MODERATE

    @pytest.mark.asyncio
    async def test_returns_complex(self):
        """Returns COMPLEX when model responds with COMPLEX."""
        mock_result = CLIResult(success=True, output="COMPLEX", session_id="test")

        async def mock_cli_query(*args, **kwargs):
            return mock_result

        with patch("fireteam.complexity.run_cli_query", mock_cli_query):
            result = await estimate_complexity("redesign the architecture")
            assert result == ComplexityLevel.COMPLEX

    @pytest.mark.asyncio
    async def test_handles_lowercase_response(self):
        """Handles lowercase response."""
        mock_result = CLIResult(success=True, output="moderate", session_id="test")

        async def mock_cli_query(*args, **kwargs):
            return mock_result

        with patch("fireteam.complexity.run_cli_query", mock_cli_query):
            result = await estimate_complexity("some task")
            assert result == ComplexityLevel.MODERATE

    @pytest.mark.asyncio
    async def test_handles_response_with_extra_text(self):
        """Handles response with extra text around the level."""
        mock_result = CLIResult(
            success=True,
            output="I think this is COMPLEX because it involves many files.",
            session_id="test",
        )

        async def mock_cli_query(*args, **kwargs):
            return mock_result

        with patch("fireteam.complexity.run_cli_query", mock_cli_query):
            result = await estimate_complexity("big task")
            assert result == ComplexityLevel.COMPLEX

    @pytest.mark.asyncio
    async def test_defaults_to_simple_on_unclear_response(self):
        """Defaults to SIMPLE when response is unclear."""
        mock_result = CLIResult(
            success=True,
            output="I'm not sure how to classify this.",
            session_id="test",
        )

        async def mock_cli_query(*args, **kwargs):
            return mock_result

        with patch("fireteam.complexity.run_cli_query", mock_cli_query):
            result = await estimate_complexity("ambiguous task")
            assert result == ComplexityLevel.SIMPLE

    @pytest.mark.asyncio
    async def test_defaults_to_simple_on_empty_response(self):
        """Defaults to SIMPLE when response is empty."""
        mock_result = CLIResult(success=True, output="", session_id="test")

        async def mock_cli_query(*args, **kwargs):
            return mock_result

        with patch("fireteam.complexity.run_cli_query", mock_cli_query):
            result = await estimate_complexity("task")
            assert result == ComplexityLevel.SIMPLE

    @pytest.mark.asyncio
    async def test_defaults_to_simple_on_cli_error(self):
        """Defaults to SIMPLE when CLI returns error."""
        mock_result = CLIResult(success=False, output="", error="CLI failed")

        async def mock_cli_query(*args, **kwargs):
            return mock_result

        with patch("fireteam.complexity.run_cli_query", mock_cli_query):
            result = await estimate_complexity("task")
            assert result == ComplexityLevel.SIMPLE

    @pytest.mark.asyncio
    async def test_context_is_included_in_prompt(self):
        """Context is included when provided."""
        mock_result = CLIResult(success=True, output="SIMPLE", session_id="test")
        captured_prompt = None

        async def mock_cli_query(prompt, *args, **kwargs):
            nonlocal captured_prompt
            captured_prompt = prompt
            return mock_result

        with patch("fireteam.complexity.run_cli_query", mock_cli_query):
            await estimate_complexity("fix bug", context="Error: NullPointer")

        assert "Error: NullPointer" in captured_prompt

    @pytest.mark.asyncio
    async def test_no_context_shows_none_provided(self):
        """Shows 'None provided' when no context given."""
        mock_result = CLIResult(success=True, output="SIMPLE", session_id="test")
        captured_prompt = None

        async def mock_cli_query(prompt, *args, **kwargs):
            nonlocal captured_prompt
            captured_prompt = prompt
            return mock_result

        with patch("fireteam.complexity.run_cli_query", mock_cli_query):
            await estimate_complexity("fix bug")

        assert "None provided" in captured_prompt

    @pytest.mark.asyncio
    async def test_uses_plan_phase_for_readonly(self, project_dir):
        """Uses PLAN phase for read-only exploration."""
        from fireteam.models import PhaseType

        mock_result = CLIResult(success=True, output="MODERATE", session_id="test")
        captured_phase = None

        async def mock_cli_query(prompt, phase, *args, **kwargs):
            nonlocal captured_phase
            captured_phase = phase
            return mock_result

        with patch("fireteam.complexity.run_cli_query", mock_cli_query):
            await estimate_complexity("refactor auth", project_dir=project_dir)

        assert captured_phase == PhaseType.PLAN

    @pytest.mark.asyncio
    async def test_sets_cwd_with_project_dir(self, project_dir):
        """With project_dir, estimation sets cwd for tool access."""
        mock_result = CLIResult(success=True, output="SIMPLE", session_id="test")
        captured_cwd = None

        async def mock_cli_query(prompt, phase, cwd, *args, **kwargs):
            nonlocal captured_cwd
            captured_cwd = cwd
            return mock_result

        with patch("fireteam.complexity.run_cli_query", mock_cli_query):
            await estimate_complexity("task", project_dir=project_dir)

        from pathlib import Path
        assert Path(captured_cwd).is_absolute()
