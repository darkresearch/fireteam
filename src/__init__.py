"""
Fireteam - Adaptive task execution using Claude Code CLI.

Uses Claude Code CLI for execution, piggybacking on the user's
existing session and credits. No separate API key required.

Features:
- Complexity estimation (auto-select execution mode)
- Circuit breaker (warns on stuck loops)
- Rate limiting (API budget management)
- Dual-gate exit (executor + reviewer consensus)
- Session continuity via Claude Code
- Tmux-based autonomous execution

Usage (programmatic):
    from fireteam import execute, ExecutionMode

    result = await execute(
        project_dir="/path/to/project",
        goal="Fix the bug in auth.py",
    )

Usage (CLI - autonomous):
    fireteam start --project-dir /path/to/project --goal "Fix all bugs"
    fireteam list
    fireteam attach fireteam-project
    fireteam logs fireteam-project
    fireteam kill fireteam-project
"""

from .api import execute
from .models import ExecutionMode, ExecutionResult
from .complexity import ComplexityLevel, estimate_complexity
from .claude_cli import CLISession, CLIResult, ClaudeCLI
from .circuit_breaker import CircuitBreaker, CircuitState, IterationMetrics, create_circuit_breaker
from .rate_limiter import RateLimiter, RateLimitExceeded, get_rate_limiter, reset_rate_limiter
from .runner import start_session, attach_session, kill_session, list_sessions, SessionInfo

__all__ = [
    # Main API
    "execute",
    # Models
    "ExecutionMode",
    "ExecutionResult",
    # Complexity
    "ComplexityLevel",
    "estimate_complexity",
    # CLI
    "CLISession",
    "CLIResult",
    "ClaudeCLI",
    # Circuit Breaker
    "CircuitBreaker",
    "CircuitState",
    "IterationMetrics",
    "create_circuit_breaker",
    # Rate Limiter
    "RateLimiter",
    "RateLimitExceeded",
    "get_rate_limiter",
    "reset_rate_limiter",
    # Runner (tmux-based autonomous execution)
    "start_session",
    "attach_session",
    "kill_session",
    "list_sessions",
    "SessionInfo",
]
