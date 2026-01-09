"""Integration tests for fireteam.

These tests verify the full execution flow with mocked SDK calls.
Run with --run-integration for tests that require API keys.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from fireteam.api import execute, ExecutionMode, ExecutionResult
from fireteam.complexity import ComplexityLevel, estimate_complexity


class TestComplexityToExecutionFlow:
    """Tests for complexity estimation to execution mode flow."""

    @pytest.mark.asyncio
    async def test_trivial_task_uses_single_turn(self, project_dir):
        """Trivial tasks use SINGLE_TURN mode."""
        # Mock complexity estimation to return TRIVIAL
        with patch("fireteam.api.estimate_complexity", return_value=ComplexityLevel.TRIVIAL):
            # Mock SDK query
            mock_message = MagicMock()
            mock_message.result = "Fixed the typo."

            async def mock_query(*args, **kwargs):
                yield mock_message

            with patch("fireteam.api.query", mock_query):
                result = await execute(
                    project_dir=project_dir,
                    goal="fix typo in readme",
                    run_tests=False,
                )

                assert result.success is True
                assert result.mode == ExecutionMode.SINGLE_TURN

    @pytest.mark.asyncio
    async def test_complex_task_uses_full_mode(self, project_dir):
        """Complex tasks use FULL mode with planning and review."""
        call_prompts = []

        async def mock_query(prompt, options):
            call_prompts.append(prompt)
            mock_message = MagicMock()
            # Return different responses based on call
            if len(call_prompts) == 1:  # Planning
                mock_message.result = "Plan: 1. Analyze 2. Implement 3. Test"
            elif len(call_prompts) == 2:  # Execution
                mock_message.result = "Implemented the feature."
            else:  # Review
                mock_message.result = "COMPLETION: 98%"
            yield mock_message

        with patch("fireteam.api.estimate_complexity", return_value=ComplexityLevel.COMPLEX):
            with patch("fireteam.api.query", mock_query):
                result = await execute(
                    project_dir=project_dir,
                    goal="redesign the authentication system",
                    run_tests=False,
                )

                # Should have at least 3 calls: plan, execute, review
                assert len(call_prompts) >= 3
                assert result.mode == ExecutionMode.FULL


class TestExecutionWithContext:
    """Tests for execution with additional context."""

    @pytest.mark.asyncio
    async def test_context_flows_to_execution(self, project_dir):
        """Context is included in execution prompt."""
        captured_prompts = []

        async def mock_query(prompt, options):
            captured_prompts.append(prompt)
            mock_message = MagicMock()
            mock_message.result = "Fixed based on crash logs."
            yield mock_message

        with patch("fireteam.api.query", mock_query):
            await execute(
                project_dir=project_dir,
                goal="fix the crash",
                context="Error: NullPointerException at auth.py:42",
                mode=ExecutionMode.SIMPLE,
                run_tests=False,
            )

            # Context should be in the prompt
            assert any("NullPointerException" in p for p in captured_prompts)


class TestHooksIntegration:
    """Tests for hooks integration with execution."""

    @pytest.mark.asyncio
    async def test_quality_hooks_enabled_by_default(self, project_dir):
        """Quality hooks are enabled when run_tests=True."""
        captured_options = None

        async def mock_query(prompt, options):
            nonlocal captured_options
            captured_options = options
            mock_message = MagicMock()
            mock_message.result = "Done."
            yield mock_message

        with patch("fireteam.api.query", mock_query):
            await execute(
                project_dir=project_dir,
                goal="add feature",
                mode=ExecutionMode.SIMPLE,
                run_tests=True,  # Default
            )

            # Hooks should be configured
            assert captured_options.hooks is not None

    @pytest.mark.asyncio
    async def test_hooks_disabled_when_run_tests_false(self, project_dir):
        """No hooks when run_tests=False."""
        captured_options = None

        async def mock_query(prompt, options):
            nonlocal captured_options
            captured_options = options
            mock_message = MagicMock()
            mock_message.result = "Done."
            yield mock_message

        with patch("fireteam.api.query", mock_query):
            await execute(
                project_dir=project_dir,
                goal="add feature",
                mode=ExecutionMode.SIMPLE,
                run_tests=False,
            )

            # Hooks should be None
            assert captured_options.hooks is None


class TestModerateModeReview:
    """Tests for MODERATE mode review behavior."""

    @pytest.mark.asyncio
    async def test_moderate_mode_extracts_completion(self, project_dir):
        """MODERATE mode extracts completion percentage from review."""
        call_count = 0

        async def mock_query(prompt, options):
            nonlocal call_count
            call_count += 1
            mock_message = MagicMock()
            if call_count == 1:
                mock_message.result = "Implementation complete."
            else:
                mock_message.result = "Looks good. COMPLETION: 85%"
            yield mock_message

        with patch("fireteam.api.query", mock_query):
            result = await execute(
                project_dir=project_dir,
                goal="refactor auth",
                mode=ExecutionMode.MODERATE,
                run_tests=False,
            )

            assert result.completion_percentage == 85
            assert "review" in result.metadata


class TestFullModeValidation:
    """Tests for FULL mode validation loop."""

    @pytest.mark.asyncio
    async def test_full_mode_requires_multiple_validations(self, project_dir):
        """FULL mode requires multiple successful validations."""
        review_count = 0

        async def mock_query(prompt, options):
            nonlocal review_count
            mock_message = MagicMock()

            if "plan" in prompt.lower() or "PLANNER" in prompt:
                mock_message.result = "Plan: Step 1, Step 2, Step 3"
            elif "execute" in prompt.lower() or "EXECUTOR" in prompt:
                mock_message.result = "Executed all steps."
            else:
                review_count += 1
                # Return 96% for all reviews to pass validation
                mock_message.result = f"Review {review_count}: COMPLETION: 96%"
            yield mock_message

        with patch("fireteam.api.query", mock_query):
            result = await execute(
                project_dir=project_dir,
                goal="big refactor",
                mode=ExecutionMode.FULL,
                run_tests=False,
            )

            # Should have done multiple reviews (needs 3 consecutive >95%)
            assert review_count >= 3
            assert result.success is True

    @pytest.mark.asyncio
    async def test_full_mode_fails_on_low_completion(self, project_dir):
        """FULL mode fails when completion stays below threshold."""
        review_count = 0

        async def mock_query(prompt, options):
            nonlocal review_count
            mock_message = MagicMock()

            if "plan" in prompt.lower() or "PLANNER" in prompt:
                mock_message.result = "Plan: Step 1"
            elif "execute" in prompt.lower() or "EXECUTOR" in prompt:
                mock_message.result = "Executed."
            else:
                review_count += 1
                # Always return 70% - never passes threshold
                mock_message.result = f"Review {review_count}: COMPLETION: 70%"
            yield mock_message

        with patch("fireteam.api.query", mock_query):
            result = await execute(
                project_dir=project_dir,
                goal="incomplete task",
                mode=ExecutionMode.FULL,
                run_tests=False,
            )

            # Should fail validation
            assert result.success is False
            assert "validation" in result.error.lower()


class TestErrorHandling:
    """Tests for error handling in execution flow."""

    @pytest.mark.asyncio
    async def test_handles_sdk_exception(self, project_dir):
        """Handles SDK exceptions gracefully."""
        async def mock_query(*args, **kwargs):
            raise Exception("API rate limit exceeded")
            yield  # Never reached

        with patch("fireteam.api.query", mock_query):
            result = await execute(
                project_dir=project_dir,
                goal="do something",
                mode=ExecutionMode.SIMPLE,
                run_tests=False,
            )

            assert result.success is False
            assert "rate limit" in result.error.lower() or "error" in result.error.lower()

    @pytest.mark.asyncio
    async def test_handles_planning_failure(self, project_dir):
        """Handles planning phase failure in FULL mode."""
        async def mock_query(prompt, options):
            if "plan" in prompt.lower() or "PLANNER" in prompt:
                raise Exception("Planning failed")
            mock_message = MagicMock()
            mock_message.result = "Done."
            yield mock_message

        with patch("fireteam.api.query", mock_query):
            result = await execute(
                project_dir=project_dir,
                goal="complex task",
                mode=ExecutionMode.FULL,
                run_tests=False,
            )

            assert result.success is False
            assert "planning" in result.error.lower() or "failed" in result.error.lower()


@pytest.mark.integration
class TestRealExecution:
    """Integration tests that require real API calls.

    Run with: pytest --run-integration
    """

    @pytest.mark.asyncio
    async def test_trivial_task_real_execution(self, project_dir):
        """Test real execution of a trivial task."""
        # This test requires ANTHROPIC_API_KEY
        import os
        if not os.environ.get("ANTHROPIC_API_KEY"):
            pytest.skip("ANTHROPIC_API_KEY not set")

        result = await execute(
            project_dir=project_dir,
            goal="What is 2 + 2?",
            mode=ExecutionMode.SINGLE_TURN,
            run_tests=False,
        )

        assert result.success is True
        assert result.output is not None
        assert "4" in result.output
