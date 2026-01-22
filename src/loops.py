"""
Execution implementations for fireteam.

SINGLE_TURN: direct CLI call, no loop
MODERATE: execute → review loop until complete
FULL: plan → execute → parallel reviews loop until complete

Uses Claude Code CLI for execution, piggybacking on user's session.
"""

import asyncio
import itertools
import logging
import re
from pathlib import Path

from . import config
from .circuit_breaker import CircuitBreaker, IterationMetrics, create_circuit_breaker
from .claude_cli import CLIResult, CLISession, run_cli_query
from .models import (
    ExecutionMode,
    ExecutionResult,
    IterationState,
    LoopConfig,
    PhaseType,
    ReviewResult,
)
from .prompts.builder import build_prompt
from .rate_limiter import RateLimiter, get_rate_limiter


async def single_turn(
    project_dir: Path,
    goal: str,
    context: str = "",
    session: CLISession | None = None,
    rate_limiter: RateLimiter | None = None,
    log: logging.Logger | None = None,
) -> ExecutionResult:
    """
    SINGLE_TURN mode: direct CLI call, no loop.

    For trivial and simple tasks that don't need iteration.
    """
    log = log or logging.getLogger("fireteam")
    log.info("SINGLE_TURN: Direct CLI call")

    # Rate limiting
    limiter = rate_limiter or get_rate_limiter()
    await limiter.acquire()

    prompt = build_prompt(
        phase=PhaseType.EXECUTE,
        goal=goal,
        context=context,
    )

    result = await run_cli_query(
        prompt=prompt,
        phase=PhaseType.EXECUTE,
        cwd=project_dir,
        session=session,
        model=config.SDK_MODEL,
        log=log,
    )

    if not result.success:
        log.error(f"Single turn failed: {result.error}")
        return ExecutionResult(
            success=False,
            mode=ExecutionMode.SINGLE_TURN,
            error=result.error,
        )

    return ExecutionResult(
        success=True,
        mode=ExecutionMode.SINGLE_TURN,
        output=result.output,
        completion_percentage=100,
        iterations=1,
        metadata={"session_id": result.session_id},
    )


async def run_phase(
    phase: PhaseType,
    prompt: str,
    project_dir: Path,
    session: CLISession | None = None,
    rate_limiter: RateLimiter | None = None,
) -> CLIResult:
    """
    Run a single CLI query for a phase.

    Each phase gets appropriate tool permissions:
    - PLAN: read-only (Glob, Grep, Read)
    - EXECUTE: full access
    - REVIEW: read-only + Bash for tests
    """
    limiter = rate_limiter or get_rate_limiter()
    await limiter.acquire()

    return await run_cli_query(
        prompt=prompt,
        phase=phase,
        cwd=project_dir,
        session=session,
        model=config.SDK_MODEL,
    )


async def run_single_review(
    goal: str,
    state: IterationState,
    project_dir: Path,
    session: CLISession | None = None,
    rate_limiter: RateLimiter | None = None,
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

    result = await run_phase(
        PhaseType.REVIEW,
        prompt,
        project_dir,
        session=session,
        rate_limiter=rate_limiter,
    )

    if not result.success:
        return ReviewResult(
            completion_percentage=0,
            feedback=f"Review failed: {result.error}",
            issues=["Reviewer encountered an error"],
            passed=False,
        )

    return ReviewResult.from_output(result.output, threshold=threshold)


async def run_parallel_reviews(
    goal: str,
    state: IterationState,
    project_dir: Path,
    session: CLISession | None = None,
    rate_limiter: RateLimiter | None = None,
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
        run_single_review(
            goal, state, project_dir,
            session=session,
            rate_limiter=rate_limiter,
            reviewer_id=i + 1,
            threshold=threshold,
        )
        for i in range(num_reviewers)
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    processed: list[ReviewResult] = []
    for i, result in enumerate(results):
        if isinstance(result, BaseException):
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
            # result is ReviewResult after the exception check
            processed.append(result)

    return processed


def check_completion(
    reviews: list[ReviewResult],
    cfg: LoopConfig,
    executor_signals_complete: bool = True,
) -> bool:
    """
    Check if completion criteria is met.

    Uses dual-gate logic:
    1. Majority of reviewers must pass
    2. Executor must not signal incomplete (dual-gate)
    """
    passing = sum(1 for r in reviews if r.passed)
    reviewer_pass = passing >= cfg.majority_required

    # Dual-gate: both conditions must be met
    return reviewer_pass and executor_signals_complete


def extract_executor_signal(output: str) -> bool:
    """
    Extract executor's completion signal from output.

    Looks for WORK_COMPLETE: true/false pattern.
    Defaults to True if not found (backwards compatible).
    """
    match = re.search(r'WORK_COMPLETE:\s*(true|false)', output, re.IGNORECASE)
    if match:
        return match.group(1).lower() == "true"
    return True  # Default: assume complete if not specified


def count_files_changed(output: str) -> int:
    """
    Estimate files changed from execution output.

    Looks for patterns indicating file modifications.
    """
    patterns = [
        r'(?:wrote|created|modified|updated|edited)\s+["\']?([^"\']+)["\']?',
        r'(?:Write|Edit)\s+tool.*?([^\s]+\.\w+)',
    ]

    files = set()
    for pattern in patterns:
        for match in re.finditer(pattern, output, re.IGNORECASE):
            files.add(match.group(1))

    return len(files)


async def moderate_loop(
    project_dir: Path,
    goal: str,
    context: str = "",
    session: CLISession | None = None,
    rate_limiter: RateLimiter | None = None,
    circuit_breaker: CircuitBreaker | None = None,
    cfg: LoopConfig | None = None,
    log: logging.Logger | None = None,
) -> ExecutionResult:
    """
    MODERATE mode: execute → review loop until complete.

    Loop continues until:
    1. Single reviewer says >= threshold AND executor signals complete, OR
    2. Max iterations reached (if set)

    Features:
    - Session continuity via Claude Code CLI
    - Circuit breaker warnings for stuck loops
    - Rate limiting for API budget
    - Dual-gate exit (reviewer + executor)
    """
    cfg = cfg or LoopConfig(parallel_reviewers=1, majority_required=1)
    log = log or logging.getLogger("fireteam")
    state = IterationState()
    session = session or CLISession()
    limiter = rate_limiter or get_rate_limiter()
    breaker = circuit_breaker or create_circuit_breaker()

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
            exec_result = await run_phase(
                PhaseType.EXECUTE, exec_prompt, project_dir,
                session=session, rate_limiter=limiter,
            )

            if not exec_result.success:
                log.error(f"Execution failed: {exec_result.error}")
                return ExecutionResult(
                    success=False,
                    mode=ExecutionMode.MODERATE,
                    error=f"Execution failed on iteration {iteration}: {exec_result.error}",
                    iterations=iteration,
                )

            state.execution_output = exec_result.output
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
                goal, state, project_dir,
                session=session,
                rate_limiter=limiter,
                threshold=cfg.completion_threshold,
            )
            state.add_review([review])
            log.info(f"Review: {review.completion_percentage}% {'PASS' if review.passed else 'FAIL'}")
        except Exception as e:
            log.warning(f"Review failed: {e}")
            # Record circuit breaker metrics even on review failure
            breaker.record_iteration(IterationMetrics(
                iteration=iteration,
                files_changed=0,
                output_length=len(state.execution_output or ""),
                error_hash=IterationMetrics.hash_error(str(e)),
            ))
            continue

        # === CIRCUIT BREAKER ===
        files_changed = count_files_changed(state.execution_output or "")
        breaker.record_iteration(IterationMetrics(
            iteration=iteration,
            files_changed=files_changed,
            output_length=len(state.execution_output or ""),
            completion_percentage=review.completion_percentage,
        ))

        # === CHECK COMPLETION (DUAL-GATE) ===
        executor_complete = extract_executor_signal(state.execution_output or "")
        if check_completion([review], cfg, executor_complete):
            log.info(f"Completion threshold met at iteration {iteration}")
            return ExecutionResult(
                success=True,
                mode=ExecutionMode.MODERATE,
                output=state.execution_output,
                completion_percentage=review.completion_percentage,
                iterations=iteration,
                metadata={
                    "review_history": state.review_history,
                    "session_id": session.session_id,
                    "circuit_breaker": breaker.get_status(),
                    "rate_limiter": limiter.get_status(),
                },
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
        metadata={
            "review_history": state.review_history,
            "session_id": session.session_id,
            "circuit_breaker": breaker.get_status(),
            "rate_limiter": limiter.get_status(),
        },
    )


async def full_loop(
    project_dir: Path,
    goal: str,
    context: str = "",
    session: CLISession | None = None,
    rate_limiter: RateLimiter | None = None,
    circuit_breaker: CircuitBreaker | None = None,
    cfg: LoopConfig | None = None,
    log: logging.Logger | None = None,
) -> ExecutionResult:
    """
    FULL mode: plan → execute → parallel reviews loop until complete.

    Loop continues until:
    1. Majority (2 of 3) reviewers say >= threshold AND executor signals complete, OR
    2. Max iterations reached (if set)

    Plan is created once, then execute-review loops with feedback.

    Features:
    - Session continuity via Claude Code CLI
    - Circuit breaker warnings for stuck loops
    - Rate limiting for API budget
    - Dual-gate exit (reviewer + executor)
    """
    cfg = cfg or LoopConfig(parallel_reviewers=3, majority_required=2)
    log = log or logging.getLogger("fireteam")
    state = IterationState()
    session = session or CLISession()
    limiter = rate_limiter or get_rate_limiter()
    breaker = circuit_breaker or create_circuit_breaker()

    # === PLAN (once at start) ===
    log.info("FULL mode: Planning phase")
    plan_prompt = build_prompt(
        phase=PhaseType.PLAN,
        goal=goal,
        context=context,
    )

    try:
        plan_result = await run_phase(
            PhaseType.PLAN, plan_prompt, project_dir,
            session=session, rate_limiter=limiter,
        )

        if not plan_result.success:
            log.error(f"Planning failed: {plan_result.error}")
            return ExecutionResult(
                success=False,
                mode=ExecutionMode.FULL,
                error=f"Planning failed: {plan_result.error}",
            )

        state.plan = plan_result.output
        log.info("Planning complete")

    except Exception as e:
        log.error(f"Planning failed: {e}")
        return ExecutionResult(
            success=False,
            mode=ExecutionMode.FULL,
            error=f"Planning failed: {e}",
        )

    # === EXECUTE-REVIEW LOOP ===
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
            exec_result = await run_phase(
                PhaseType.EXECUTE, exec_prompt, project_dir,
                session=session, rate_limiter=limiter,
            )

            if not exec_result.success:
                log.error(f"Execution failed: {exec_result.error}")
                return ExecutionResult(
                    success=False,
                    mode=ExecutionMode.FULL,
                    error=f"Execution failed on iteration {iteration}: {exec_result.error}",
                    iterations=iteration,
                    metadata={"plan": state.plan},
                )

            state.execution_output = exec_result.output
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
                session=session,
                rate_limiter=limiter,
                num_reviewers=cfg.parallel_reviewers,
                threshold=cfg.completion_threshold,
                log=log,
            )
            state.add_review(reviews)

            for i, r in enumerate(reviews, 1):
                log.info(f"  Reviewer {i}: {r.completion_percentage}% {'PASS' if r.passed else 'FAIL'}")

        except Exception as e:
            log.warning(f"Review phase failed: {e}")
            breaker.record_iteration(IterationMetrics(
                iteration=iteration,
                files_changed=0,
                output_length=len(state.execution_output or ""),
                error_hash=IterationMetrics.hash_error(str(e)),
            ))
            continue

        # === CIRCUIT BREAKER ===
        files_changed = count_files_changed(state.execution_output or "")
        avg_completion = sum(r.completion_percentage for r in reviews) // len(reviews)
        breaker.record_iteration(IterationMetrics(
            iteration=iteration,
            files_changed=files_changed,
            output_length=len(state.execution_output or ""),
            completion_percentage=avg_completion,
        ))

        # === CHECK MAJORITY COMPLETION (DUAL-GATE) ===
        passing = sum(1 for r in reviews if r.passed)
        executor_complete = extract_executor_signal(state.execution_output or "")

        if check_completion(reviews, cfg, executor_complete):
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
                    "session_id": session.session_id,
                    "circuit_breaker": breaker.get_status(),
                    "rate_limiter": limiter.get_status(),
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
            "session_id": session.session_id,
            "circuit_breaker": breaker.get_status(),
            "rate_limiter": limiter.get_status(),
        },
    )
