"""Integration tests for fireteam.

These tests verify the full execution flow with mocked CLI calls.
Run with --run-integration for tests that require Claude Code CLI.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from fireteam.api import execute
from fireteam.models import ExecutionMode, ExecutionResult
from fireteam.complexity import ComplexityLevel
from fireteam.claude_cli import CLIResult


class TestComplexityToExecutionFlow:
    """Tests for complexity estimation to execution mode flow."""

    @pytest.mark.asyncio
    async def test_trivial_task_uses_single_turn(self, project_dir):
        """Trivial tasks use SINGLE_TURN mode."""
        mock_result = CLIResult(
            success=True,
            output="Fixed the typo.",
            session_id="test-session",
        )

        async def mock_cli_query(*args, **kwargs):
            return mock_result

        with patch("fireteam.api.estimate_complexity", return_value=ComplexityLevel.TRIVIAL):
            with patch("fireteam.loops.run_cli_query", mock_cli_query):
                result = await execute(
                    project_dir=project_dir,
                    goal="fix typo in readme",
                )

                assert result.success is True
                assert result.mode == ExecutionMode.SINGLE_TURN

    @pytest.mark.asyncio
    async def test_complex_task_uses_full_mode(self, project_dir):
        """Complex tasks use FULL mode with planning and review."""
        call_count = [0]

        async def mock_cli_query(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:  # Planning
                return CLIResult(success=True, output="Plan: 1. Analyze 2. Implement 3. Test", session_id="test")
            elif call_count[0] == 2:  # Execution
                return CLIResult(success=True, output="Implemented the feature.", session_id="test")
            else:  # Reviews
                return CLIResult(success=True, output="COMPLETION: 98%", session_id="test")

        with patch("fireteam.api.estimate_complexity", return_value=ComplexityLevel.COMPLEX):
            with patch("fireteam.loops.run_cli_query", mock_cli_query):
                result = await execute(
                    project_dir=project_dir,
                    goal="redesign the authentication system",
                )

                # Should have at least 3 calls: plan, execute, reviews
                assert call_count[0] >= 3
                assert result.mode == ExecutionMode.FULL


class TestExecutionWithContext:
    """Tests for execution with additional context."""

    @pytest.mark.asyncio
    async def test_context_flows_to_execution(self, project_dir):
        """Context is included in execution prompt."""
        captured_prompts = []

        async def mock_cli_query(prompt, *args, **kwargs):
            captured_prompts.append(prompt)
            return CLIResult(
                success=True,
                output="Fixed based on crash logs.",
                session_id="test-session",
            )

        with patch("fireteam.loops.run_cli_query", mock_cli_query):
            await execute(
                project_dir=project_dir,
                goal="fix the crash",
                context="Error: NullPointerException at auth.py:42",
                mode=ExecutionMode.SINGLE_TURN,
            )

            # Context should be in the prompt
            assert any("NullPointerException" in p for p in captured_prompts)


class TestModerateModeLoop:
    """Tests for MODERATE mode execute-review loop."""

    @pytest.mark.asyncio
    async def test_moderate_mode_loops_until_complete(self, project_dir):
        """MODERATE mode loops execute->review until >95%."""
        call_count = [0]

        async def mock_cli_query(*args, **kwargs):
            call_count[0] += 1
            # First iteration: execute, review (70%)
            # Second iteration: execute, review (96%)
            if call_count[0] == 1:
                return CLIResult(success=True, output="First implementation attempt.", session_id="test")
            elif call_count[0] == 2:
                return CLIResult(success=True, output="Looks incomplete. COMPLETION: 70%", session_id="test")
            elif call_count[0] == 3:
                return CLIResult(success=True, output="Fixed based on feedback.", session_id="test")
            else:
                return CLIResult(success=True, output="Now complete. COMPLETION: 96%", session_id="test")

        with patch("fireteam.loops.run_cli_query", mock_cli_query):
            result = await execute(
                project_dir=project_dir,
                goal="refactor auth",
                mode=ExecutionMode.MODERATE,
            )

            # Should have looped: 2 execute + 2 review = 4 calls
            assert call_count[0] == 4
            assert result.success is True
            assert result.completion_percentage >= 95
            assert result.iterations == 2

    @pytest.mark.asyncio
    async def test_moderate_mode_stops_at_max_iterations(self, project_dir):
        """MODERATE mode stops after max iterations."""
        call_count = [0]

        async def mock_cli_query(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] % 2 == 1:
                return CLIResult(success=True, output="Still working...", session_id="test")
            else:
                return CLIResult(success=True, output="Not quite there. COMPLETION: 70%", session_id="test")

        with patch("fireteam.loops.run_cli_query", mock_cli_query):
            result = await execute(
                project_dir=project_dir,
                goal="endless task",
                mode=ExecutionMode.MODERATE,
                max_iterations=3,
            )

            # Should stop after 3 iterations (6 calls: 3 execute + 3 review)
            assert call_count[0] == 6
            assert result.success is False
            assert result.iterations == 3


class TestFullModeLoop:
    """Tests for FULL mode plan-execute-review loop."""

    @pytest.mark.asyncio
    async def test_full_mode_uses_parallel_reviews(self, project_dir):
        """FULL mode runs 3 parallel reviewers."""
        call_count = [0]
        review_count = [0]

        async def mock_cli_query(prompt, *args, **kwargs):
            call_count[0] += 1

            # Match actual prompt patterns from prompts/*.md
            prompt_lower = prompt.lower()
            if "analyzing" in prompt_lower:  # Planner
                return CLIResult(success=True, output="Plan: Step 1, Step 2, Step 3", session_id="test")
            elif "executing" in prompt_lower:  # Executor
                return CLIResult(success=True, output="Executed all steps.", session_id="test")
            elif "reviewing" in prompt_lower:  # Reviewer
                review_count[0] += 1
                return CLIResult(success=True, output="Reviewer check. COMPLETION: 96%", session_id="test")
            else:
                return CLIResult(success=True, output="Done.", session_id="test")

        with patch("fireteam.loops.run_cli_query", mock_cli_query):
            result = await execute(
                project_dir=project_dir,
                goal="big refactor",
                mode=ExecutionMode.FULL,
            )

            # Should have 3 parallel reviews (need 2/3 majority)
            assert review_count[0] == 3
            assert result.success is True
            assert "final_reviews" in result.metadata

    @pytest.mark.asyncio
    async def test_full_mode_majority_required(self, project_dir):
        """FULL mode requires 2/3 majority to complete."""
        review_index = [0]

        async def mock_cli_query(prompt, *args, **kwargs):
            prompt_lower = prompt.lower()
            if "analyzing" in prompt_lower:  # Planner
                return CLIResult(success=True, output="Plan: Do the thing", session_id="test")
            elif "executing" in prompt_lower:  # Executor
                return CLIResult(success=True, output="Did the thing.", session_id="test")
            elif "reviewing" in prompt_lower:  # Reviewer
                review_index[0] += 1
                # Only 1 of 3 passes - not majority
                if review_index[0] % 3 == 1:
                    return CLIResult(success=True, output="COMPLETION: 96%", session_id="test")
                else:
                    return CLIResult(success=True, output="COMPLETION: 70%", session_id="test")
            else:
                return CLIResult(success=True, output="Done.", session_id="test")

        with patch("fireteam.loops.run_cli_query", mock_cli_query):
            result = await execute(
                project_dir=project_dir,
                goal="task needing consensus",
                mode=ExecutionMode.FULL,
                max_iterations=2,
            )

            # Should fail - only 1/3 pass, need 2/3
            assert result.success is False

    @pytest.mark.asyncio
    async def test_full_mode_feedback_flows_to_next_iteration(self, project_dir):
        """Review feedback flows to next execution iteration."""
        review_count = [0]
        captured_exec_prompts = []

        async def mock_cli_query(prompt, *args, **kwargs):
            prompt_lower = prompt.lower()
            if "analyzing" in prompt_lower:  # Planner
                return CLIResult(success=True, output="Plan: Fix the bug", session_id="test")
            elif "executing" in prompt_lower:  # Executor
                captured_exec_prompts.append(prompt)
                return CLIResult(success=True, output="Attempted fix.", session_id="test")
            elif "reviewing" in prompt_lower:  # Reviewer
                review_count[0] += 1
                if review_count[0] <= 3:
                    # First iteration reviews say incomplete
                    return CLIResult(success=True, output="Missing error handling. COMPLETION: 70%", session_id="test")
                else:
                    return CLIResult(success=True, output="COMPLETION: 96%", session_id="test")
            else:
                return CLIResult(success=True, output="Done.", session_id="test")

        with patch("fireteam.loops.run_cli_query", mock_cli_query):
            result = await execute(
                project_dir=project_dir,
                goal="fix bug",
                mode=ExecutionMode.FULL,
            )

            # Second execution should include feedback from first review
            assert len(captured_exec_prompts) >= 2
            # Check for feedback indicators in second execution prompt
            second_prompt = captured_exec_prompts[1].lower()
            assert "feedback" in second_prompt or "previous" in second_prompt or "iteration" in second_prompt


class TestErrorHandling:
    """Tests for error handling in execution flow."""

    @pytest.mark.asyncio
    async def test_handles_cli_error(self, project_dir):
        """Handles CLI errors gracefully."""
        async def mock_cli_query(*args, **kwargs):
            return CLIResult(success=False, output="", error="API rate limit exceeded")

        with patch("fireteam.loops.run_cli_query", mock_cli_query):
            result = await execute(
                project_dir=project_dir,
                goal="do something",
                mode=ExecutionMode.SINGLE_TURN,
            )

            assert result.success is False
            assert "rate limit" in result.error.lower() or "error" in result.error.lower()

    @pytest.mark.asyncio
    async def test_handles_planning_failure(self, project_dir):
        """Handles planning phase failure in FULL mode."""
        async def mock_cli_query(prompt, *args, **kwargs):
            if "analyzing" in prompt.lower():  # Planner
                return CLIResult(success=False, output="", error="Planning failed")
            return CLIResult(success=True, output="Done.", session_id="test")

        with patch("fireteam.loops.run_cli_query", mock_cli_query):
            result = await execute(
                project_dir=project_dir,
                goal="complex task",
                mode=ExecutionMode.FULL,
            )

            assert result.success is False
            assert "planning" in result.error.lower() or "failed" in result.error.lower()


@pytest.mark.integration
class TestRealExecution:
    """Integration tests that require real Claude Code CLI.

    Run with: pytest --run-integration
    """

    @pytest.mark.asyncio
    async def test_trivial_task_real_execution(self, project_dir):
        """Test real execution of a trivial task."""
        import shutil
        if not shutil.which("claude"):
            pytest.skip("Claude CLI not available")

        result = await execute(
            project_dir=project_dir,
            goal="What is 2 + 2?",
            mode=ExecutionMode.SINGLE_TURN,
        )

        assert result.success is True
        assert result.output is not None
        assert "4" in result.output
