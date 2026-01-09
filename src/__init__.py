"""
Fireteam - Adaptive task execution using Claude Agent SDK.

Minimal layer on top of SDK that adds:
- Complexity estimation (auto-select execution mode)
- Quality hooks (auto-run tests after code changes)

Usage:
    from fireteam import execute, ExecutionMode

    result = await execute(
        project_dir="/path/to/project",
        goal="Fix the bug in auth.py",
    )
"""

from .api import execute
from .models import ExecutionMode, ExecutionResult
from .complexity import ComplexityLevel, estimate_complexity
from .hooks import QUALITY_HOOKS, AUTONOMOUS_HOOKS, create_test_hooks

__all__ = [
    "execute",
    "ExecutionMode",
    "ExecutionResult",
    "ComplexityLevel",
    "estimate_complexity",
    "QUALITY_HOOKS",
    "AUTONOMOUS_HOOKS",
    "create_test_hooks",
]
