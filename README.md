# Fireteam

Adaptive task execution using Claude Agent SDK with complexity-based routing and loop-until-complete behavior.

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
pip install fireteam
```

Requires Python 3.10+ and a valid `ANTHROPIC_API_KEY` environment variable.

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

complexity = await estimate_complexity(
    goal="Add logging to the auth module",
    context="Existing logging in other modules uses Python logging",
)

print(f"Estimated complexity: {complexity}")
# ComplexityLevel.SIMPLE -> routes to SINGLE_TURN mode
```

## Execution Modes

### SINGLE_TURN
For trivial and simple tasks. Single SDK call, no review loop.

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
    run_tests: bool = True,
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
) -> ComplexityLevel
```

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | (required) | API key for Claude |
| `FIRETEAM_MAX_ITERATIONS` | (none) | Max loop iterations. Unset = infinite. |
| `FIRETEAM_LOG_LEVEL` | INFO | Logging verbosity |

## Quality Hooks

Fireteam includes SDK hooks for quality enforcement:

- **QUALITY_HOOKS**: Run tests after edits, block user questions
- **AUTONOMOUS_HOOKS**: Block all user interaction
- **DEBUG_HOOKS**: Log all tool usage

```python
from fireteam import execute

result = await execute(
    project_dir="/path/to/project",
    goal="Add feature",
    run_tests=True,  # Enables QUALITY_HOOKS (default)
)
```

## Project Structure

```
fireteam/
├── .claude-plugin/
│   ├── plugin.json      # Claude Code plugin manifest
│   └── commands/
│       └── fireteam.md  # /fireteam command definition
├── src/
│   ├── __init__.py      # Public API exports
│   ├── api.py           # Core execute() function
│   ├── models.py        # Data models (ExecutionMode, ExecutionResult, etc.)
│   ├── loops.py         # Loop implementations (moderate_loop, full_loop)
│   ├── complexity.py    # Complexity estimation
│   ├── config.py        # Configuration
│   ├── hooks.py         # SDK hooks for quality
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
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"

# Run tests
pytest tests/ -v
```

## License

MIT License
