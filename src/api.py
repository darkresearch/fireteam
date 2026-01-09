"""
Public API for fireteam library.

Provides adaptive task execution using Claude Agent SDK primitives.
Minimal layer on top of SDK - complexity estimation + execution mode selection.

Usage:
    import fireteam

    result = await fireteam.execute(
        project_dir="/path/to/project",
        goal="Fix the bug in auth.py",
        context="Error logs: ...",
    )
"""

import logging
from pathlib import Path

from claude_agent_sdk import query, ClaudeAgentOptions

from . import config
from .complexity import ComplexityLevel, estimate_complexity
from .hooks import QUALITY_HOOKS, create_test_hooks
from .models import ExecutionMode, ExecutionResult, LoopConfig, PhaseType
from .loops import moderate_loop, full_loop, run_phase


# Map complexity levels to execution modes
# SIMPLE is now treated as SINGLE_TURN (no separate mode)
COMPLEXITY_TO_MODE = {
    ComplexityLevel.TRIVIAL: ExecutionMode.SINGLE_TURN,
    ComplexityLevel.SIMPLE: ExecutionMode.SINGLE_TURN,  # Merged with SINGLE_TURN
    ComplexityLevel.MODERATE: ExecutionMode.MODERATE,
    ComplexityLevel.COMPLEX: ExecutionMode.FULL,
}


async def execute(
    project_dir: str | Path,
    goal: str,
    mode: ExecutionMode | None = None,
    context: str = "",
    run_tests: bool = True,
    test_command: list[str] | None = None,
    max_iterations: int | None = None,
    logger: logging.Logger | None = None,
) -> ExecutionResult:
    """
    Execute a task with appropriate complexity handling.

    Args:
        project_dir: Path to the project directory
        goal: Task description
        mode: Execution mode (None = auto-detect from complexity)
        context: Additional context (crash logs, etc.)
        run_tests: Run tests after code changes (default: True)
        test_command: Custom test command (auto-detected if None)
        max_iterations: Maximum loop iterations for MODERATE/FULL modes (None = infinite)
        logger: Optional logger

    Returns:
        ExecutionResult with success status and output
    """
    project_dir = Path(project_dir).resolve()
    log = logger or logging.getLogger("fireteam")

    # Configure quality hooks
    hooks = None
    if run_tests:
        hooks = create_test_hooks(test_command=test_command) if test_command else QUALITY_HOOKS
        log.info("Quality hooks enabled")

    # Auto-detect mode if not specified
    if mode is None:
        log.info("Estimating task complexity...")
        complexity = await estimate_complexity(goal, context)
        mode = COMPLEXITY_TO_MODE[complexity]
        log.info(f"Complexity: {complexity.value} -> Mode: {mode.value}")

    # Use config default if max_iterations not explicitly provided
    effective_max_iterations = max_iterations if max_iterations is not None else config.MAX_ITERATIONS

    # Dispatch based on mode
    if mode == ExecutionMode.SINGLE_TURN:
        return await _single_turn(project_dir, goal, context, hooks, log)

    elif mode == ExecutionMode.MODERATE:
        cfg = LoopConfig(
            max_iterations=effective_max_iterations,
            parallel_reviewers=1,
            majority_required=1,
        )
        return await moderate_loop(project_dir, goal, context, hooks, cfg, log)

    elif mode == ExecutionMode.FULL:
        cfg = LoopConfig(
            max_iterations=effective_max_iterations,
            parallel_reviewers=3,
            majority_required=2,
        )
        return await full_loop(project_dir, goal, context, hooks, cfg, log)

    else:
        return ExecutionResult(success=False, mode=mode, error=f"Unknown mode: {mode}")


async def _single_turn(
    project_dir: Path,
    goal: str,
    context: str,
    hooks: dict | None,
    log: logging.Logger,
) -> ExecutionResult:
    """Trivial task - single SDK call, no loop."""
    log.info("SINGLE_TURN: Direct SDK call")

    prompt = f"Task: {goal}"
    if context:
        prompt += f"\n\nContext:\n{context}"

    options = ClaudeAgentOptions(
        allowed_tools=["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
        permission_mode=config.SDK_PERMISSION_MODE,
        model=config.SDK_MODEL,
        cwd=str(project_dir),
        setting_sources=config.SDK_SETTING_SOURCES,
        hooks=hooks,
        max_turns=10,  # Limit for trivial tasks
    )

    try:
        result_text = ""
        async for message in query(prompt=prompt, options=options):
            if hasattr(message, "result"):
                result_text = message.result
            elif hasattr(message, "content"):
                if isinstance(message.content, str):
                    result_text += message.content
                elif isinstance(message.content, list):
                    for block in message.content:
                        if hasattr(block, "text"):
                            result_text += block.text

        return ExecutionResult(
            success=True,
            mode=ExecutionMode.SINGLE_TURN,
            output=result_text,
            completion_percentage=100,
            iterations=1,
        )
    except Exception as e:
        log.error(f"Single turn failed: {e}")
        return ExecutionResult(success=False, mode=ExecutionMode.SINGLE_TURN, error=str(e))
