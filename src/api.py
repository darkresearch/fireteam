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
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from claude_agent_sdk import query, ClaudeAgentOptions

from . import config
from .complexity import ComplexityLevel, estimate_complexity
from .hooks import QUALITY_HOOKS, create_test_hooks
from .prompts import EXECUTOR_PROMPT, REVIEWER_PROMPT, PLANNER_PROMPT


class ExecutionMode(Enum):
    """Execution modes for fireteam tasks."""
    SINGLE_TURN = "single_turn"  # Direct Opus call, minimal tools
    SIMPLE = "simple"            # Execute only
    MODERATE = "moderate"        # Execute + single review
    FULL = "full"                # Plan + execute + validation reviews


@dataclass
class ExecutionResult:
    """Result of a fireteam execution."""
    success: bool
    mode: ExecutionMode
    output: str | None = None
    error: str | None = None
    completion_percentage: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


COMPLEXITY_TO_MODE = {
    ComplexityLevel.TRIVIAL: ExecutionMode.SINGLE_TURN,
    ComplexityLevel.SIMPLE: ExecutionMode.SIMPLE,
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
    logger: logging.Logger | None = None,
) -> ExecutionResult:
    """
    Execute a task with appropriate complexity handling.

    Args:
        project_dir: Path to the project directory
        goal: Task description
        mode: Execution mode (None = auto-detect)
        context: Additional context (crash logs, etc.)
        run_tests: Run tests after code changes (default: True)
        test_command: Custom test command (auto-detected if None)
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
        log.info("Quality hooks enabled: tests run after code changes")

    # Auto-detect mode if not specified
    if mode is None:
        log.info("Estimating task complexity...")
        complexity = await estimate_complexity(goal, context)
        mode = COMPLEXITY_TO_MODE[complexity]
        log.info(f"Complexity: {complexity.value} -> Mode: {mode.value}")

    # Dispatch based on mode
    if mode == ExecutionMode.SINGLE_TURN:
        return await _single_turn(project_dir, goal, context, log)
    elif mode == ExecutionMode.SIMPLE:
        return await _simple(project_dir, goal, context, hooks, log)
    elif mode == ExecutionMode.MODERATE:
        return await _moderate(project_dir, goal, context, hooks, log)
    elif mode == ExecutionMode.FULL:
        return await _full(project_dir, goal, context, hooks, log)
    else:
        return ExecutionResult(success=False, mode=mode, error=f"Unknown mode: {mode}")


async def _single_turn(
    project_dir: Path,
    goal: str,
    context: str,
    log: logging.Logger,
) -> ExecutionResult:
    """Trivial task - single SDK call, minimal tools."""
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
        max_turns=10,  # Limit for trivial tasks
    )

    try:
        output = await _run_query(prompt, options)
        return ExecutionResult(
            success=True,
            mode=ExecutionMode.SINGLE_TURN,
            output=output,
            completion_percentage=100,
        )
    except Exception as e:
        log.error(f"Single turn failed: {e}")
        return ExecutionResult(success=False, mode=ExecutionMode.SINGLE_TURN, error=str(e))


async def _simple(
    project_dir: Path,
    goal: str,
    context: str,
    hooks: dict | None,
    log: logging.Logger,
) -> ExecutionResult:
    """Simple task - execute only, no review."""
    log.info("SIMPLE: Execute only")

    prompt = f"{EXECUTOR_PROMPT}\n\nGoal: {goal}"
    if context:
        prompt += f"\n\nContext:\n{context}"

    options = ClaudeAgentOptions(
        allowed_tools=config.SDK_ALLOWED_TOOLS,
        permission_mode=config.SDK_PERMISSION_MODE,
        model=config.SDK_MODEL,
        cwd=str(project_dir),
        setting_sources=config.SDK_SETTING_SOURCES,
        hooks=hooks,
    )

    try:
        output = await _run_query(prompt, options)
        return ExecutionResult(
            success=True,
            mode=ExecutionMode.SIMPLE,
            output=output,
            completion_percentage=100,
        )
    except Exception as e:
        log.error(f"Simple execution failed: {e}")
        return ExecutionResult(success=False, mode=ExecutionMode.SIMPLE, error=str(e))


async def _moderate(
    project_dir: Path,
    goal: str,
    context: str,
    hooks: dict | None,
    log: logging.Logger,
) -> ExecutionResult:
    """Moderate task - execute + single review."""
    log.info("MODERATE: Execute + review")

    # Phase 1: Execute
    exec_prompt = f"{EXECUTOR_PROMPT}\n\nGoal: {goal}"
    if context:
        exec_prompt += f"\n\nContext:\n{context}"

    exec_options = ClaudeAgentOptions(
        allowed_tools=config.SDK_ALLOWED_TOOLS,
        permission_mode=config.SDK_PERMISSION_MODE,
        model=config.SDK_MODEL,
        cwd=str(project_dir),
        setting_sources=config.SDK_SETTING_SOURCES,
        hooks=hooks,
    )

    try:
        exec_output = await _run_query(exec_prompt, exec_options)
        log.info("Execution complete, starting review")
    except Exception as e:
        log.error(f"Execution failed: {e}")
        return ExecutionResult(success=False, mode=ExecutionMode.MODERATE, error=str(e))

    # Phase 2: Review (read-only)
    review_prompt = f"""{REVIEWER_PROMPT}

Goal: {goal}

Execution summary:
{exec_output[:2000]}  # Truncate if long

Review the changes and assess completion."""

    review_options = ClaudeAgentOptions(
        allowed_tools=["Read", "Glob", "Grep", "Bash"],  # Read-only + test running
        permission_mode="plan",  # Read-only mode
        model=config.SDK_MODEL,
        cwd=str(project_dir),
        setting_sources=config.SDK_SETTING_SOURCES,
    )

    try:
        review_output = await _run_query(review_prompt, review_options)
        completion = _extract_completion(review_output)
        return ExecutionResult(
            success=True,
            mode=ExecutionMode.MODERATE,
            output=exec_output,
            completion_percentage=completion,
            metadata={"review": review_output},
        )
    except Exception as e:
        log.warning(f"Review failed: {e}, returning execution result")
        return ExecutionResult(
            success=True,
            mode=ExecutionMode.MODERATE,
            output=exec_output,
            completion_percentage=80,  # Assume mostly done
            metadata={"review_error": str(e)},
        )


async def _full(
    project_dir: Path,
    goal: str,
    context: str,
    hooks: dict | None,
    log: logging.Logger,
) -> ExecutionResult:
    """Complex task - plan + execute + validation reviews."""
    log.info("FULL: Plan + execute + validate")

    # Phase 1: Plan (read-only exploration)
    plan_prompt = f"""{PLANNER_PROMPT}

Goal: {goal}

{"Context:" + chr(10) + context if context else ""}

Analyze the codebase and create an implementation plan."""

    plan_options = ClaudeAgentOptions(
        allowed_tools=["Read", "Glob", "Grep"],
        permission_mode="plan",  # Read-only
        model=config.SDK_MODEL,
        cwd=str(project_dir),
        setting_sources=config.SDK_SETTING_SOURCES,
    )

    try:
        plan = await _run_query(plan_prompt, plan_options)
        log.info("Planning complete")
    except Exception as e:
        log.error(f"Planning failed: {e}")
        return ExecutionResult(success=False, mode=ExecutionMode.FULL, error=f"Planning failed: {e}")

    # Phase 2: Execute with plan
    exec_prompt = f"""{EXECUTOR_PROMPT}

Goal: {goal}

Plan:
{plan}

Execute according to the plan."""

    exec_options = ClaudeAgentOptions(
        allowed_tools=config.SDK_ALLOWED_TOOLS,
        permission_mode=config.SDK_PERMISSION_MODE,
        model=config.SDK_MODEL,
        cwd=str(project_dir),
        setting_sources=config.SDK_SETTING_SOURCES,
        hooks=hooks,
    )

    try:
        exec_output = await _run_query(exec_prompt, exec_options)
        log.info("Execution complete")
    except Exception as e:
        log.error(f"Execution failed: {e}")
        return ExecutionResult(
            success=False,
            mode=ExecutionMode.FULL,
            error=f"Execution failed: {e}",
            metadata={"plan": plan},
        )

    # Phase 3: Validation reviews (need 3 consecutive >95%)
    validation_count = 0
    last_completion = 0

    for review_num in range(5):  # Max 5 review attempts
        log.info(f"Validation review {review_num + 1}")

        review_prompt = f"""{REVIEWER_PROMPT}

Goal: {goal}

This is validation review #{review_num + 1}. Be thorough and critical.
Check that all requirements are met and tests pass.

Previous completion estimate: {last_completion}%"""

        review_options = ClaudeAgentOptions(
            allowed_tools=["Read", "Glob", "Grep", "Bash"],
            permission_mode="plan",
            model=config.SDK_MODEL,
            cwd=str(project_dir),
            setting_sources=config.SDK_SETTING_SOURCES,
        )

        try:
            review_output = await _run_query(review_prompt, review_options)
            completion = _extract_completion(review_output)
            last_completion = completion
            log.info(f"Review {review_num + 1}: {completion}%")

            if completion >= config.COMPLETION_THRESHOLD:
                validation_count += 1
                if validation_count >= config.VALIDATION_CHECKS_REQUIRED:
                    log.info("Validation passed!")
                    return ExecutionResult(
                        success=True,
                        mode=ExecutionMode.FULL,
                        output=exec_output,
                        completion_percentage=completion,
                        metadata={
                            "plan": plan,
                            "validation_count": validation_count,
                            "reviews": review_num + 1,
                        },
                    )
            else:
                validation_count = 0  # Reset on drop below threshold

        except Exception as e:
            log.warning(f"Review {review_num + 1} failed: {e}")

    # Didn't pass validation
    return ExecutionResult(
        success=False,
        mode=ExecutionMode.FULL,
        output=exec_output,
        completion_percentage=last_completion,
        error="Did not pass validation reviews",
        metadata={"plan": plan, "validation_count": validation_count},
    )


async def _run_query(prompt: str, options: ClaudeAgentOptions) -> str:
    """Run a query and collect the output."""
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
    return result_text


def _extract_completion(review_text: str) -> int:
    """Extract completion percentage from review output."""
    import re
    match = re.search(r'COMPLETION:\s*(\d+)%', review_text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    # Fallback
    match = re.search(r'(\d+)%', review_text)
    return int(match.group(1)) if match else 50
