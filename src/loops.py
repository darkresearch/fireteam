"""
Execution implementations for fireteam.

SINGLE_TURN: direct SDK call, no loop
MODERATE: execute → review loop until complete
FULL: plan → execute → parallel reviews loop until complete
"""

import asyncio
import itertools
import logging
from pathlib import Path

from claude_agent_sdk import query, ClaudeAgentOptions

from . import config
from .models import (
    ExecutionMode,
    ExecutionResult,
    IterationState,
    LoopConfig,
    PhaseType,
    ReviewResult,
)
from .prompts.builder import build_prompt


# Tool permission sets per phase
PLAN_TOOLS = ["Glob", "Grep", "Read"]
EXECUTE_TOOLS = ["Read", "Write", "Edit", "Bash", "Glob", "Grep"]
REVIEW_TOOLS = ["Read", "Glob", "Grep", "Bash"]


async def single_turn(
    project_dir: Path,
    goal: str,
    context: str = "",
    hooks: dict | None = None,
    log: logging.Logger | None = None,
) -> ExecutionResult:
    """
    SINGLE_TURN mode: direct SDK call, no loop.

    For trivial and simple tasks that don't need iteration.
    """
    log = log or logging.getLogger("fireteam")
    log.info("SINGLE_TURN: Direct SDK call")

    prompt = build_prompt(
        phase=PhaseType.EXECUTE,
        goal=goal,
        context=context,
    )

    options = ClaudeAgentOptions(
        allowed_tools=EXECUTE_TOOLS,
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


async def run_phase(
    phase: PhaseType,
    prompt: str,
    project_dir: Path,
    hooks: dict | None = None,
) -> str:
    """
    Run a single SDK query for a phase.

    Each phase gets appropriate tool permissions:
    - PLAN: read-only (Glob, Grep, Read)
    - EXECUTE: full access + hooks
    - REVIEW: read-only + Bash for tests
    """
    if phase == PhaseType.PLAN:
        tools = PLAN_TOOLS
        permission_mode = "plan"
        phase_hooks = None
    elif phase == PhaseType.EXECUTE:
        tools = EXECUTE_TOOLS
        permission_mode = config.SDK_PERMISSION_MODE
        phase_hooks = hooks
    elif phase == PhaseType.REVIEW:
        tools = REVIEW_TOOLS
        permission_mode = "plan"
        phase_hooks = None
    else:
        raise ValueError(f"Unknown phase: {phase}")

    options = ClaudeAgentOptions(
        allowed_tools=tools,
        permission_mode=permission_mode,
        model=config.SDK_MODEL,
        cwd=str(project_dir),
        setting_sources=config.SDK_SETTING_SOURCES,
        hooks=phase_hooks,
    )

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


async def run_single_review(
    goal: str,
    state: IterationState,
    project_dir: Path,
    reviewer_id: int = 1,
    threshold: int = 95,
) -> ReviewResult:
    """Run a single reviewer and return structured result."""
    prompt = build_prompt(
        phase=PhaseType.REVIEW,
        goal=goal,
        execution_output=state.execution_output,
        plan=state.plan,
        previous_feedback=state.accumulated_feedback if state.iteration > 1 else None,
        reviewer_id=reviewer_id,
        iteration=state.iteration,
    )

    output = await run_phase(PhaseType.REVIEW, prompt, project_dir)
    return ReviewResult.from_output(output, threshold=threshold)


async def run_parallel_reviews(
    goal: str,
    state: IterationState,
    project_dir: Path,
    num_reviewers: int = 3,
    threshold: int = 95,
    log: logging.Logger | None = None,
) -> list[ReviewResult]:
    """
    Run multiple reviewers in parallel using asyncio.gather().

    Returns list of ReviewResults, handling any exceptions gracefully.
    """
    log = log or logging.getLogger("fireteam")

    tasks = [
        run_single_review(goal, state, project_dir, reviewer_id=i + 1, threshold=threshold)
        for i in range(num_reviewers)
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    processed: list[ReviewResult] = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            log.warning(f"Reviewer {i + 1} failed: {result}")
            processed.append(
                ReviewResult(
                    completion_percentage=0,
                    feedback=f"Review failed: {result}",
                    issues=["Reviewer encountered an error"],
                    passed=False,
                )
            )
        else:
            processed.append(result)

    return processed


def check_completion(reviews: list[ReviewResult], cfg: LoopConfig) -> bool:
    """Check if completion criteria is met (majority must pass)."""
    passing = sum(1 for r in reviews if r.passed)
    return passing >= cfg.majority_required


async def moderate_loop(
    project_dir: Path,
    goal: str,
    context: str = "",
    hooks: dict | None = None,
    cfg: LoopConfig | None = None,
    log: logging.Logger | None = None,
) -> ExecutionResult:
    """
    MODERATE mode: execute → review loop until complete.

    Loop continues until:
    1. Single reviewer says >= threshold, OR
    2. Max iterations reached (if set)

    Feedback from each review flows to the next execution.
    """
    cfg = cfg or LoopConfig(parallel_reviewers=1, majority_required=1)
    log = log or logging.getLogger("fireteam")
    state = IterationState()

    # Use infinite counter if max_iterations is None, otherwise bounded range
    counter = itertools.count(1) if cfg.max_iterations is None else range(1, cfg.max_iterations + 1)
    max_display = "∞" if cfg.max_iterations is None else cfg.max_iterations

    for iteration in counter:
        state.iteration = iteration
        log.info(f"MODERATE iteration {iteration}/{max_display}")

        # === EXECUTE ===
        exec_prompt = build_prompt(
            phase=PhaseType.EXECUTE,
            goal=goal,
            context=context,
            previous_feedback=state.accumulated_feedback if iteration > 1 else None,
        )

        try:
            state.execution_output = await run_phase(
                PhaseType.EXECUTE, exec_prompt, project_dir, hooks=hooks
            )
            log.info(f"Execution complete (iteration {iteration})")
        except Exception as e:
            log.error(f"Execution failed: {e}")
            return ExecutionResult(
                success=False,
                mode=ExecutionMode.MODERATE,
                error=f"Execution failed on iteration {iteration}: {e}",
                iterations=iteration,
            )

        # === REVIEW ===
        try:
            review = await run_single_review(
                goal, state, project_dir, threshold=cfg.completion_threshold
            )
            state.add_review([review])
            log.info(f"Review: {review.completion_percentage}% {'PASS' if review.passed else 'FAIL'}")
        except Exception as e:
            log.warning(f"Review failed: {e}")
            continue

        # === CHECK COMPLETION ===
        if check_completion([review], cfg):
            log.info(f"Completion threshold met at iteration {iteration}")
            return ExecutionResult(
                success=True,
                mode=ExecutionMode.MODERATE,
                output=state.execution_output,
                completion_percentage=review.completion_percentage,
                iterations=iteration,
                metadata={"review_history": state.review_history},
            )

    # Max iterations reached (only reachable if max_iterations is set)
    last_completion = 0
    if state.review_history:
        last_reviews = state.review_history[-1].get("reviews", [])
        if last_reviews:
            last_completion = last_reviews[0].get("completion", 0)

    return ExecutionResult(
        success=False,
        mode=ExecutionMode.MODERATE,
        output=state.execution_output,
        error=f"Did not reach {cfg.completion_threshold}% after {cfg.max_iterations} iterations",
        completion_percentage=last_completion,
        iterations=cfg.max_iterations or state.iteration,
        metadata={"review_history": state.review_history},
    )


async def full_loop(
    project_dir: Path,
    goal: str,
    context: str = "",
    hooks: dict | None = None,
    cfg: LoopConfig | None = None,
    log: logging.Logger | None = None,
) -> ExecutionResult:
    """
    FULL mode: plan → execute → parallel reviews loop until complete.

    Loop continues until:
    1. Majority (2 of 3) reviewers say >= threshold, OR
    2. Max iterations reached (if set)

    Plan is created once, then execute-review loops with feedback.
    """
    cfg = cfg or LoopConfig(parallel_reviewers=3, majority_required=2)
    log = log or logging.getLogger("fireteam")
    state = IterationState()

    # === PLAN (once at start) ===
    log.info("FULL mode: Planning phase")
    plan_prompt = build_prompt(
        phase=PhaseType.PLAN,
        goal=goal,
        context=context,
    )

    try:
        state.plan = await run_phase(PhaseType.PLAN, plan_prompt, project_dir)
        log.info("Planning complete")
    except Exception as e:
        log.error(f"Planning failed: {e}")
        return ExecutionResult(
            success=False,
            mode=ExecutionMode.FULL,
            error=f"Planning failed: {e}",
        )

    # === EXECUTE-REVIEW LOOP ===
    # Use infinite counter if max_iterations is None, otherwise bounded range
    counter = itertools.count(1) if cfg.max_iterations is None else range(1, cfg.max_iterations + 1)
    max_display = "∞" if cfg.max_iterations is None else cfg.max_iterations

    for iteration in counter:
        state.iteration = iteration
        log.info(f"FULL iteration {iteration}/{max_display}")

        # === EXECUTE ===
        exec_prompt = build_prompt(
            phase=PhaseType.EXECUTE,
            goal=goal,
            context=context,
            plan=state.plan,
            previous_feedback=state.accumulated_feedback if iteration > 1 else None,
        )

        try:
            state.execution_output = await run_phase(
                PhaseType.EXECUTE, exec_prompt, project_dir, hooks=hooks
            )
            log.info(f"Execution complete (iteration {iteration})")
        except Exception as e:
            log.error(f"Execution failed: {e}")
            return ExecutionResult(
                success=False,
                mode=ExecutionMode.FULL,
                error=f"Execution failed on iteration {iteration}: {e}",
                iterations=iteration,
                metadata={"plan": state.plan},
            )

        # === PARALLEL REVIEWS ===
        log.info(f"Running {cfg.parallel_reviewers} parallel reviewers")
        try:
            reviews = await run_parallel_reviews(
                goal,
                state,
                project_dir,
                num_reviewers=cfg.parallel_reviewers,
                threshold=cfg.completion_threshold,
                log=log,
            )
            state.add_review(reviews)

            for i, r in enumerate(reviews, 1):
                log.info(f"  Reviewer {i}: {r.completion_percentage}% {'PASS' if r.passed else 'FAIL'}")
        except Exception as e:
            log.warning(f"Review phase failed: {e}")
            continue

        # === CHECK MAJORITY COMPLETION ===
        passing = sum(1 for r in reviews if r.passed)
        avg_completion = sum(r.completion_percentage for r in reviews) // len(reviews)

        if check_completion(reviews, cfg):
            log.info(f"Majority completion ({passing}/{len(reviews)}) at iteration {iteration}")
            return ExecutionResult(
                success=True,
                mode=ExecutionMode.FULL,
                output=state.execution_output,
                completion_percentage=avg_completion,
                iterations=iteration,
                metadata={
                    "plan": state.plan,
                    "review_history": state.review_history,
                    "final_reviews": [
                        {"reviewer": i + 1, "completion": r.completion_percentage, "passed": r.passed}
                        for i, r in enumerate(reviews)
                    ],
                },
            )

    # Max iterations reached (only reachable if max_iterations is set)
    avg_completion = 0
    if state.review_history:
        last_reviews = state.review_history[-1].get("reviews", [])
        if last_reviews:
            avg_completion = sum(r.get("completion", 0) for r in last_reviews) // len(last_reviews)

    return ExecutionResult(
        success=False,
        mode=ExecutionMode.FULL,
        output=state.execution_output,
        error=f"Did not achieve majority completion after {cfg.max_iterations} iterations",
        completion_percentage=avg_completion,
        iterations=cfg.max_iterations or state.iteration,
        metadata={
            "plan": state.plan,
            "review_history": state.review_history,
        },
    )
