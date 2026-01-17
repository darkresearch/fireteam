"""
Complexity estimation for adaptive execution mode selection.

Fireteam estimates task complexity to choose the appropriate execution mode:
- TRIVIAL: Single CLI call, no loop
- SIMPLE: Single CLI call, no loop (same as TRIVIAL)
- MODERATE: Executor + single Reviewer loop
- COMPLEX: Full Planner + Executor + triple Reviewer loop

Uses Claude Code CLI for estimation, piggybacking on user's session.
"""

from enum import Enum
from pathlib import Path

from .claude_cli import run_cli_query, CLISession
from .models import PhaseType
from .prompts import COMPLEXITY_PROMPT
from . import config


class ComplexityLevel(Enum):
    """Task complexity levels."""
    TRIVIAL = "trivial"      # Single turn, no loop
    SIMPLE = "simple"        # Single turn, no loop (merged with TRIVIAL)
    MODERATE = "moderate"    # Executor + single Reviewer
    COMPLEX = "complex"      # Full Planner + Executor + triple Reviewer


async def estimate_complexity(
    goal: str,
    context: str = "",
    project_dir: str | Path | None = None,
    session: CLISession | None = None,
) -> ComplexityLevel:
    """
    Estimate task complexity using Claude Code CLI.

    When project_dir is provided, Claude can explore the codebase using
    read-only tools (Glob, Grep, Read) to make a more accurate estimate.

    Args:
        goal: The task description
        context: Additional context (e.g., crash logs, file contents)
        project_dir: Project directory for codebase exploration (optional)
        session: Optional CLI session for continuity

    Returns:
        ComplexityLevel indicating how to execute this task
    """
    prompt = COMPLEXITY_PROMPT.format(goal=goal, context=context or "None provided")

    # Use PLAN phase for read-only exploration
    cwd = Path(project_dir).resolve() if project_dir else Path.cwd()

    result = await run_cli_query(
        prompt=prompt,
        phase=PhaseType.PLAN,  # Read-only tools
        cwd=cwd,
        session=session,
        model=config.SDK_MODEL,
    )

    if not result.success:
        # Default to SIMPLE on error
        return ComplexityLevel.SIMPLE

    # Parse the response - look for complexity level keywords
    result_upper = result.output.strip().upper()

    # Check for explicit complexity keywords (last occurrence wins for multi-turn)
    if "COMPLEX" in result_upper:
        return ComplexityLevel.COMPLEX
    elif "MODERATE" in result_upper:
        return ComplexityLevel.MODERATE
    elif "TRIVIAL" in result_upper:
        return ComplexityLevel.TRIVIAL
    elif "SIMPLE" in result_upper:
        return ComplexityLevel.SIMPLE
    else:
        # Default to SIMPLE if unclear
        return ComplexityLevel.SIMPLE
