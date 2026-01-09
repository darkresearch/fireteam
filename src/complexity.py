"""
Complexity estimation for adaptive execution mode selection.

Fireteam estimates task complexity to choose the appropriate execution mode:
- TRIVIAL: Single Opus turn (direct SDK call, no agents)
- SIMPLE: Executor only
- MODERATE: Executor + single Reviewer
- COMPLEX: Full Planner + Executor + triple Reviewer
"""

from enum import Enum
from claude_agent_sdk import query, ClaudeAgentOptions

from . import config
from .prompts import COMPLEXITY_PROMPT


class ComplexityLevel(Enum):
    """Task complexity levels."""
    TRIVIAL = "trivial"      # Single turn, no agents
    SIMPLE = "simple"        # Executor only
    MODERATE = "moderate"    # Executor + single Reviewer
    COMPLEX = "complex"      # Full Planner + Executor + triple Reviewer


async def estimate_complexity(goal: str, context: str = "") -> ComplexityLevel:
    """
    Estimate task complexity by asking Opus.

    Args:
        goal: The task description
        context: Additional context (e.g., crash logs, file contents)

    Returns:
        ComplexityLevel indicating how to execute this task
    """
    prompt = COMPLEXITY_PROMPT.format(goal=goal, context=context or "None provided")

    options = ClaudeAgentOptions(
        allowed_tools=[],  # No tools needed for estimation
        max_turns=1,
        model=config.SDK_MODEL,
    )

    result_text = ""
    async for message in query(prompt=prompt, options=options):
        if hasattr(message, "result"):
            result_text = message.result

    # Parse the response
    result_upper = result_text.strip().upper()

    if "TRIVIAL" in result_upper:
        return ComplexityLevel.TRIVIAL
    elif "SIMPLE" in result_upper:
        return ComplexityLevel.SIMPLE
    elif "MODERATE" in result_upper:
        return ComplexityLevel.MODERATE
    elif "COMPLEX" in result_upper:
        return ComplexityLevel.COMPLEX
    else:
        # Default to SIMPLE if unclear
        return ComplexityLevel.SIMPLE
