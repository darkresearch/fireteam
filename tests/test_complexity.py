"""Unit tests for complexity estimation."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from fireteam.complexity import ComplexityLevel, estimate_complexity, COMPLEXITY_PROMPT


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
        mock_message = MagicMock()
        mock_message.result = "TRIVIAL"

        async def mock_query(*args, **kwargs):
            yield mock_message

        with patch("fireteam.complexity.query", mock_query):
            result = await estimate_complexity("fix typo")
            assert result == ComplexityLevel.TRIVIAL

    @pytest.mark.asyncio
    async def test_returns_simple(self):
        """Returns SIMPLE when model responds with SIMPLE."""
        mock_message = MagicMock()
        mock_message.result = "SIMPLE"

        async def mock_query(*args, **kwargs):
            yield mock_message

        with patch("fireteam.complexity.query", mock_query):
            result = await estimate_complexity("add logging")
            assert result == ComplexityLevel.SIMPLE

    @pytest.mark.asyncio
    async def test_returns_moderate(self):
        """Returns MODERATE when model responds with MODERATE."""
        mock_message = MagicMock()
        mock_message.result = "MODERATE"

        async def mock_query(*args, **kwargs):
            yield mock_message

        with patch("fireteam.complexity.query", mock_query):
            result = await estimate_complexity("refactor auth module")
            assert result == ComplexityLevel.MODERATE

    @pytest.mark.asyncio
    async def test_returns_complex(self):
        """Returns COMPLEX when model responds with COMPLEX."""
        mock_message = MagicMock()
        mock_message.result = "COMPLEX"

        async def mock_query(*args, **kwargs):
            yield mock_message

        with patch("fireteam.complexity.query", mock_query):
            result = await estimate_complexity("redesign the architecture")
            assert result == ComplexityLevel.COMPLEX

    @pytest.mark.asyncio
    async def test_handles_lowercase_response(self):
        """Handles lowercase response."""
        mock_message = MagicMock()
        mock_message.result = "moderate"

        async def mock_query(*args, **kwargs):
            yield mock_message

        with patch("fireteam.complexity.query", mock_query):
            result = await estimate_complexity("some task")
            assert result == ComplexityLevel.MODERATE

    @pytest.mark.asyncio
    async def test_handles_response_with_extra_text(self):
        """Handles response with extra text around the level."""
        mock_message = MagicMock()
        mock_message.result = "I think this is COMPLEX because it involves many files."

        async def mock_query(*args, **kwargs):
            yield mock_message

        with patch("fireteam.complexity.query", mock_query):
            result = await estimate_complexity("big task")
            assert result == ComplexityLevel.COMPLEX

    @pytest.mark.asyncio
    async def test_defaults_to_simple_on_unclear_response(self):
        """Defaults to SIMPLE when response is unclear."""
        mock_message = MagicMock()
        mock_message.result = "I'm not sure how to classify this."

        async def mock_query(*args, **kwargs):
            yield mock_message

        with patch("fireteam.complexity.query", mock_query):
            result = await estimate_complexity("ambiguous task")
            assert result == ComplexityLevel.SIMPLE

    @pytest.mark.asyncio
    async def test_defaults_to_simple_on_empty_response(self):
        """Defaults to SIMPLE when response is empty."""
        mock_message = MagicMock()
        mock_message.result = ""

        async def mock_query(*args, **kwargs):
            yield mock_message

        with patch("fireteam.complexity.query", mock_query):
            result = await estimate_complexity("task")
            assert result == ComplexityLevel.SIMPLE

    @pytest.mark.asyncio
    async def test_context_is_included_in_prompt(self):
        """Context is included when provided."""
        mock_message = MagicMock()
        mock_message.result = "SIMPLE"
        captured_prompt = None

        async def mock_query(prompt, **kwargs):
            nonlocal captured_prompt
            captured_prompt = prompt
            yield mock_message

        with patch("fireteam.complexity.query", mock_query):
            await estimate_complexity("fix bug", context="Error: NullPointer")

        assert "Error: NullPointer" in captured_prompt

    @pytest.mark.asyncio
    async def test_no_context_shows_none_provided(self):
        """Shows 'None provided' when no context given."""
        mock_message = MagicMock()
        mock_message.result = "SIMPLE"
        captured_prompt = None

        async def mock_query(prompt, **kwargs):
            nonlocal captured_prompt
            captured_prompt = prompt
            yield mock_message

        with patch("fireteam.complexity.query", mock_query):
            await estimate_complexity("fix bug")

        assert "None provided" in captured_prompt

    @pytest.mark.asyncio
    async def test_uses_no_tools(self):
        """Estimation uses no tools (just needs model response)."""
        mock_message = MagicMock()
        mock_message.result = "SIMPLE"
        captured_options = None

        async def mock_query(prompt, options):
            nonlocal captured_options
            captured_options = options
            yield mock_message

        with patch("fireteam.complexity.query", mock_query):
            await estimate_complexity("task")

        assert captured_options.allowed_tools == []

    @pytest.mark.asyncio
    async def test_uses_single_turn(self):
        """Estimation uses max_turns=1."""
        mock_message = MagicMock()
        mock_message.result = "SIMPLE"
        captured_options = None

        async def mock_query(prompt, options):
            nonlocal captured_options
            captured_options = options
            yield mock_message

        with patch("fireteam.complexity.query", mock_query):
            await estimate_complexity("task")

        assert captured_options.max_turns == 1
