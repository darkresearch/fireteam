# Fireteam

Adaptive task execution using Claude Code CLI with complexity-based routing and loop-until-complete behavior.

## Overview

Fireteam estimates task complexity and routes to the appropriate execution strategy:

| Complexity | Mode | Behavior |
|------------|------|----------|
| TRIVIAL | SINGLE_TURN | Direct execution, single pass |
| SIMPLE | SINGLE_TURN | Direct execution, single pass |
| MODERATE | MODERATE | Execute -> review loop until >95% complete |
| COMPLEX | FULL | Plan once, then execute -> 3 parallel reviews loop until 2/3 say >95% |

## Installation

```bash
uv add fireteam
```

Requires Python 3.12+ and Claude Code CLI installed.

## Usage

### Basic Usage

```python
from fireteam import execute

result = await execute(
    project_dir="/path/to/project",
    goal="Fix the bug in auth.py",
    context="Error logs: NullPointerException at line 42",
)

if result.success:
    print(f"Completed in {result.iterations} iterations")
    print(f"Completion: {result.completion_percentage}%")
else:
    print(f"Failed: {result.error}")
```

### Specify Execution Mode

```python
from fireteam import execute, ExecutionMode

# Force full mode with planning and parallel reviews
# Loops infinitely until complete (default)
result = await execute(
    project_dir="/path/to/project",
    goal="Refactor the authentication module",
    mode=ExecutionMode.FULL,
)

# Or limit iterations if needed
result = await execute(
    project_dir="/path/to/project",
    goal="Refactor the authentication module",
    mode=ExecutionMode.FULL,
    max_iterations=10,  # Stop after 10 iterations if not complete
)
```

### Complexity Estimation

```python
from fireteam import estimate_complexity, ComplexityLevel

# Quick estimation (no codebase access)
complexity = await estimate_complexity(
    goal="Add logging to the auth module",
    context="Existing logging in other modules uses Python logging",
)

# Accurate estimation with codebase exploration
# Claude uses Glob, Grep, Read to understand the project
complexity = await estimate_complexity(
    goal="Refactor the authentication system",
    project_dir="/path/to/project",
)

print(f"Estimated complexity: {complexity}")
# ComplexityLevel.MODERATE -> routes to MODERATE mode
```

## Execution Modes

### SINGLE_TURN
For trivial and simple tasks. Single CLI call, no review loop.

### MODERATE
For moderate tasks requiring validation:
```
while not complete:
    execute()
    completion = review()
    if completion >= 95%:
        complete = True
```
Loops **indefinitely** until a single reviewer says >95% complete. Set `max_iterations` to limit.

### FULL
For complex tasks requiring planning and consensus:
```
plan()  # Once at start
while not complete:
    execute()
    reviews = run_3_parallel_reviewers()
    if 2 of 3 say >= 95%:
        complete = True
```
Plans once, then loops **indefinitely** until majority (2/3) consensus. Set `max_iterations` to limit.

## API Reference

### `execute()`

```python
async def execute(
    project_dir: str | Path,
    goal: str,
    context: str = "",
    mode: ExecutionMode | None = None,  # Auto-detect if None
    max_iterations: int | None = None,  # None = infinite (default)
) -> ExecutionResult
```

### `ExecutionResult`

```python
@dataclass
class ExecutionResult:
    success: bool
    mode: ExecutionMode
    output: str | None = None
    error: str | None = None
    completion_percentage: int = 0
    iterations: int = 0
    metadata: dict = field(default_factory=dict)
```

### `estimate_complexity()`

```python
async def estimate_complexity(
    goal: str,
    context: str = "",
    project_dir: str | Path | None = None,  # Enables codebase exploration
) -> ComplexityLevel
```

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `FIRETEAM_MAX_ITERATIONS` | (none) | Max loop iterations. Unset = infinite. |
| `FIRETEAM_LOG_LEVEL` | INFO | Logging verbosity |

## Project Structure

```
fireteam/
├── .claude-plugin/
│   └── plugin.json      # Claude Code plugin manifest
├── commands/
│   └── fireteam.md      # /fireteam command definition
├── hooks/
│   └── hooks.json       # Claude Code hooks configuration
├── src/
│   ├── __init__.py      # Public API exports
│   ├── api.py           # Core execute() function
│   ├── models.py        # Data models (ExecutionMode, ExecutionResult, etc.)
│   ├── loops.py         # Loop implementations (moderate_loop, full_loop)
│   ├── claude_cli.py    # Claude Code CLI wrapper
│   ├── complexity.py    # Complexity estimation
│   ├── circuit_breaker.py # Stuck loop detection
│   ├── rate_limiter.py  # API call budget management
│   ├── runner.py        # tmux-based autonomous execution
│   ├── prompt.py        # PROMPT.md parsing with file includes
│   ├── config.py        # Configuration
│   ├── claude_hooks/    # Claude Code hook handlers
│   └── prompts/
│       ├── __init__.py  # Prompt loader
│       ├── builder.py   # Prompt building with feedback injection
│       ├── executor.md  # Executor agent prompt
│       ├── reviewer.md  # Reviewer agent prompt
│       ├── planner.md   # Planner agent prompt
│       └── complexity.md # Complexity estimation prompt
├── tests/
└── pyproject.toml
```

## Development

```bash
# Clone and install dev dependencies
git clone https://github.com/darkresearch/fireteam
cd fireteam
uv sync --extra dev

# Run tests
uv run pytest tests/ -v
```

## License

MIT License
