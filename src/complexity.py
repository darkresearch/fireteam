"""
Complexity estimation for adaptive execution mode selection.

Fireteam estimates task complexity to choose the appropriate execution mode:
- TRIVIAL: Single Opus turn (direct SDK call, no agents)
- SIMPLE: Executor only
- MODERATE: Executor + single Reviewer
- COMPLEX: Full Planner + Executor + triple Reviewer
"""

from enum import Enum
from pathlib import Path

from claude_agent_sdk import query, ClaudeAgentOptions

from . import config
from .prompts import COMPLEXITY_PROMPT


class ComplexityLevel(Enum):
    """Task complexity levels."""
    TRIVIAL = "trivial"      # Single turn, no agents
    SIMPLE = "simple"        # Executor only
    MODERATE = "moderate"    # Executor + single Reviewer
    COMPLEX = "complex"      # Full Planner + Executor + triple Reviewer


# Read-only tools for codebase exploration during complexity estimation
EXPLORATION_TOOLS = ["Glob", "Grep", "Read"]


async def estimate_complexity(
    goal: str,
    context: str = "",
    project_dir: str | Path | None = None,
) -> ComplexityLevel:
    """
    Estimate task complexity by asking Opus.

    When project_dir is provided, Claude can explore the codebase using
    read-only tools (Glob, Grep, Read) to make a more accurate estimate.

    Args:
        goal: The task description
        context: Additional context (e.g., crash logs, file contents)
        project_dir: Project directory for codebase exploration (optional)

    Returns:
        ComplexityLevel indicating how to execute this task
    """
    prompt = COMPLEXITY_PROMPT.format(goal=goal, context=context or "None provided")

    # Enable codebase exploration if project_dir is provided
    if project_dir:
        options = ClaudeAgentOptions(
            allowed_tools=EXPLORATION_TOOLS,
            permission_mode="plan",  # Read-only mode
            model=config.SDK_MODEL,
            cwd=str(Path(project_dir).resolve()),
            setting_sources=config.SDK_SETTING_SOURCES,
        )
    else:
        # No tools - quick estimation without codebase access
        options = ClaudeAgentOptions(
            allowed_tools=[],
            max_turns=1,
            model=config.SDK_MODEL,
        )

    result_text = ""
    async for message in query(prompt=prompt, options=options):
        if hasattr(message, "result"):
            result_text = message.result
        elif hasattr(message, "content"):
            # Capture final text response after tool use
            if isinstance(message.content, str):
                result_text = message.content
            elif isinstance(message.content, list):
                for block in message.content:
                    if hasattr(block, "text"):
                        result_text = block.text

    # Parse the response - look for complexity level keywords
    result_upper = result_text.strip().upper()

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
