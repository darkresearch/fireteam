"""Integration tests for fireteam.

These tests verify the full execution flow with mocked SDK calls.
Run with --run-integration for tests that require API keys.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from fireteam.api import execute
from fireteam.models import ExecutionMode, ExecutionResult
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
            else:  # Reviews (3 parallel)
                mock_message.result = "COMPLETION: 98%"
            yield mock_message

        with patch("fireteam.api.estimate_complexity", return_value=ComplexityLevel.COMPLEX):
            with patch("fireteam.loops.query", mock_query):
                with patch("fireteam.api.query", mock_query):
                    result = await execute(
                        project_dir=project_dir,
                        goal="redesign the authentication system",
                        run_tests=False,
                    )

                    # Should have at least 3 calls: plan, execute, reviews
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
                mode=ExecutionMode.SINGLE_TURN,
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
                mode=ExecutionMode.SINGLE_TURN,
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
                mode=ExecutionMode.SINGLE_TURN,
                run_tests=False,
            )

            # Hooks should be None
            assert captured_options.hooks is None


class TestModerateModeLoop:
    """Tests for MODERATE mode execute-review loop."""

    @pytest.mark.asyncio
    async def test_moderate_mode_loops_until_complete(self, project_dir):
        """MODERATE mode loops execute->review until >95%."""
        call_count = 0

        async def mock_query(prompt, options):
            nonlocal call_count
            call_count += 1
            mock_message = MagicMock()
            # First iteration: execute, review (70%)
            # Second iteration: execute, review (96%)
            if call_count == 1:
                mock_message.result = "First implementation attempt."
            elif call_count == 2:
                mock_message.result = "Looks incomplete. COMPLETION: 70%"
            elif call_count == 3:
                mock_message.result = "Fixed based on feedback."
            else:
                mock_message.result = "Now complete. COMPLETION: 96%"
            yield mock_message

        with patch("fireteam.loops.query", mock_query):
            result = await execute(
                project_dir=project_dir,
                goal="refactor auth",
                mode=ExecutionMode.MODERATE,
                run_tests=False,
            )

            # Should have looped: 2 execute + 2 review = 4 calls
            assert call_count == 4
            assert result.success is True
            assert result.completion_percentage >= 95
            assert result.iterations == 2

    @pytest.mark.asyncio
    async def test_moderate_mode_stops_at_max_iterations(self, project_dir):
        """MODERATE mode stops after max iterations."""
        call_count = 0

        async def mock_query(prompt, options):
            nonlocal call_count
            call_count += 1
            mock_message = MagicMock()
            if call_count % 2 == 1:
                mock_message.result = "Still working..."
            else:
                mock_message.result = "Not quite there. COMPLETION: 70%"
            yield mock_message

        with patch("fireteam.loops.query", mock_query):
            result = await execute(
                project_dir=project_dir,
                goal="endless task",
                mode=ExecutionMode.MODERATE,
                max_iterations=3,
                run_tests=False,
            )

            # Should stop after 3 iterations (6 calls: 3 execute + 3 review)
            assert call_count == 6
            assert result.success is False
            assert result.iterations == 3


class TestFullModeLoop:
    """Tests for FULL mode plan-execute-review loop."""

    @pytest.mark.asyncio
    async def test_full_mode_uses_parallel_reviews(self, project_dir):
        """FULL mode runs 3 parallel reviewers."""
        call_count = 0
        review_count = 0

        async def mock_query(prompt, options):
            nonlocal call_count, review_count
            call_count += 1
            mock_message = MagicMock()

            # Match actual prompt patterns from prompts/*.md
            if "analyzing" in prompt.lower():  # Planner: "You are analyzing..."
                mock_message.result = "Plan: Step 1, Step 2, Step 3"
            elif "executing" in prompt.lower():  # Executor: "You are executing..."
                mock_message.result = "Executed all steps."
            elif "reviewing" in prompt.lower():  # Reviewer: "You are reviewing..."
                review_count += 1
                mock_message.result = f"Reviewer check. COMPLETION: 96%"
            else:
                mock_message.result = "Done."
            yield mock_message

        with patch("fireteam.loops.query", mock_query):
            result = await execute(
                project_dir=project_dir,
                goal="big refactor",
                mode=ExecutionMode.FULL,
                run_tests=False,
            )

            # Should have 3 parallel reviews (need 2/3 majority)
            assert review_count == 3
            assert result.success is True
            assert "final_reviews" in result.metadata

    @pytest.mark.asyncio
    async def test_full_mode_majority_required(self, project_dir):
        """FULL mode requires 2/3 majority to complete."""
        review_index = 0

        async def mock_query(prompt, options):
            nonlocal review_index
            mock_message = MagicMock()

            if "analyzing" in prompt.lower():  # Planner
                mock_message.result = "Plan: Do the thing"
            elif "executing" in prompt.lower():  # Executor
                mock_message.result = "Did the thing."
            elif "reviewing" in prompt.lower():  # Reviewer
                review_index += 1
                # Only 1 of 3 passes - not majority
                if review_index % 3 == 1:
                    mock_message.result = "COMPLETION: 96%"
                else:
                    mock_message.result = "COMPLETION: 70%"
            else:
                mock_message.result = "Done."
            yield mock_message

        with patch("fireteam.loops.query", mock_query):
            result = await execute(
                project_dir=project_dir,
                goal="task needing consensus",
                mode=ExecutionMode.FULL,
                max_iterations=2,
                run_tests=False,
            )

            # Should fail - only 1/3 pass, need 2/3
            assert result.success is False

    @pytest.mark.asyncio
    async def test_full_mode_feedback_flows_to_next_iteration(self, project_dir):
        """Review feedback flows to next execution iteration."""
        review_count = 0
        captured_exec_prompts = []

        async def mock_query(prompt, options):
            nonlocal review_count
            mock_message = MagicMock()

            if "analyzing" in prompt.lower():  # Planner
                mock_message.result = "Plan: Fix the bug"
            elif "executing" in prompt.lower():  # Executor
                captured_exec_prompts.append(prompt)
                mock_message.result = "Attempted fix."
            elif "reviewing" in prompt.lower():  # Reviewer
                review_count += 1
                if review_count <= 3:
                    # First iteration reviews say incomplete
                    mock_message.result = "Missing error handling. COMPLETION: 70%"
                else:
                    mock_message.result = "COMPLETION: 96%"
            else:
                mock_message.result = "Done."
            yield mock_message

        with patch("fireteam.loops.query", mock_query):
            result = await execute(
                project_dir=project_dir,
                goal="fix bug",
                mode=ExecutionMode.FULL,
                run_tests=False,
            )

            # Second execution should include feedback from first review
            assert len(captured_exec_prompts) >= 2
            # Check for feedback indicators in second execution prompt
            second_prompt = captured_exec_prompts[1].lower()
            assert "feedback" in second_prompt or "previous" in second_prompt or "iteration" in second_prompt


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
                mode=ExecutionMode.SINGLE_TURN,
                run_tests=False,
            )

            assert result.success is False
            assert "rate limit" in result.error.lower() or "error" in result.error.lower()

    @pytest.mark.asyncio
    async def test_handles_planning_failure(self, project_dir):
        """Handles planning phase failure in FULL mode."""
        async def mock_query(prompt, options):
            if "analyzing" in prompt.lower():  # Planner
                raise Exception("Planning failed")
            mock_message = MagicMock()
            mock_message.result = "Done."
            yield mock_message

        with patch("fireteam.loops.query", mock_query):
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
