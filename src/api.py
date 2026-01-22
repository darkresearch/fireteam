"""
Public API for fireteam library.

Provides adaptive task execution using Claude Code CLI.
Piggybacks on user's Claude Code session for unified billing.

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

from . import config
from .circuit_breaker import CircuitBreaker, create_circuit_breaker
from .claude_cli import CLISession
from .complexity import ComplexityLevel, estimate_complexity
from .loops import full_loop, moderate_loop, single_turn
from .models import ExecutionMode, ExecutionResult, LoopConfig
from .rate_limiter import get_rate_limiter

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
    max_iterations: int | None = None,
    calls_per_hour: int | None = None,
    session: CLISession | None = None,
    circuit_breaker: CircuitBreaker | None = None,
    logger: logging.Logger | None = None,
) -> ExecutionResult:
    """
    Execute a task with appropriate complexity handling.

    Uses Claude Code CLI, piggybacking on the user's existing
    session and credits. No separate API key required.

    Args:
        project_dir: Path to the project directory
        goal: Task description
        mode: Execution mode (None = auto-detect from complexity)
        context: Additional context (crash logs, etc.)
        max_iterations: Maximum loop iterations for MODERATE/FULL modes (None = infinite)
        calls_per_hour: Rate limit for API calls (default: 100)
        session: Optional CLI session for continuity across calls
        circuit_breaker: Optional circuit breaker for stuck loop detection
        logger: Optional logger

    Returns:
        ExecutionResult with success status and output

    Features:
        - Claude Code session piggybacking (unified billing)
        - Adaptive complexity routing
        - Circuit breaker warnings for stuck loops
        - Rate limiting for API budget
        - Dual-gate exit detection
        - Session continuity via Claude Code
    """
    project_dir = Path(project_dir).resolve()
    log = logger or logging.getLogger("fireteam")

    # Initialize session for continuity
    session = session or CLISession()

    # Initialize rate limiter
    rate_limiter = get_rate_limiter(calls_per_hour=calls_per_hour)

    # Initialize circuit breaker
    breaker = circuit_breaker or create_circuit_breaker()

    # Auto-detect mode if not specified
    if mode is None:
        log.info("Estimating task complexity...")
        complexity = await estimate_complexity(
            goal, context, project_dir=project_dir, session=session
        )
        mode = COMPLEXITY_TO_MODE[complexity]
        log.info(f"Complexity: {complexity.value} -> Mode: {mode.value}")

    # Use config default if max_iterations not explicitly provided
    effective_max_iterations = max_iterations if max_iterations is not None else config.MAX_ITERATIONS

    # Dispatch based on mode
    if mode == ExecutionMode.SINGLE_TURN:
        return await single_turn(
            project_dir, goal, context,
            session=session,
            rate_limiter=rate_limiter,
            log=log,
        )

    elif mode == ExecutionMode.MODERATE:
        cfg = LoopConfig(
            max_iterations=effective_max_iterations,
            parallel_reviewers=1,
            majority_required=1,
        )
        return await moderate_loop(
            project_dir, goal, context,
            session=session,
            rate_limiter=rate_limiter,
            circuit_breaker=breaker,
            cfg=cfg,
            log=log,
        )

    elif mode == ExecutionMode.FULL:
        cfg = LoopConfig(
            max_iterations=effective_max_iterations,
            parallel_reviewers=3,
            majority_required=2,
        )
        return await full_loop(
            project_dir, goal, context,
            session=session,
            rate_limiter=rate_limiter,
            circuit_breaker=breaker,
            cfg=cfg,
            log=log,
        )

    else:
        return ExecutionResult(success=False, mode=mode, error=f"Unknown mode: {mode}")
