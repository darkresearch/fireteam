# Fireteam

Multi-phase autonomous task execution with complexity estimation, planning, execution, and review.

## Overview

Fireteam provides adaptive task execution using Claude Agent SDK. It automatically estimates task complexity and selects the appropriate execution strategy:

| Complexity | Mode | Phases |
|------------|------|--------|
| TRIVIAL | SINGLE_TURN | Direct execution, minimal tools |
| SIMPLE | SIMPLE | Execute only |
| MODERATE | MODERATE | Execute + single review |
| COMPLEX | FULL | Plan + execute + validation reviews |

## Installation

```bash
pip install fireteam
```

Requires Python 3.10+ and a valid `ANTHROPIC_API_KEY` environment variable.

## Usage

### Basic Usage

```python
import asyncio
from fireteam import execute

result = await execute(
    project_dir="/path/to/project",
    goal="Fix the bug in auth.py",
    context="Error logs: NullPointerException at line 42",
)

if result.success:
    print(f"Completed: {result.output}")
    print(f"Completion: {result.completion_percentage}%")
else:
    print(f"Failed: {result.error}")
```

### Specify Execution Mode

```python
from fireteam import execute, ExecutionMode

# Force a specific mode
result = await execute(
    project_dir="/path/to/project",
    goal="Refactor the authentication module",
    mode=ExecutionMode.FULL,  # Use full plan+execute+review cycle
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
# ComplexityLevel.SIMPLE
```

## Execution Modes

### SINGLE_TURN
For trivial tasks like fixing typos or adding comments. Single SDK call with minimal tools.

### SIMPLE
For simple tasks. Execute only, no review phase.

### MODERATE
For moderate tasks. Execute + single review to assess completion.

### FULL
For complex tasks. Full cycle:
1. **Planning**: Analyze goal and create implementation plan
2. **Execution**: Implement the plan
3. **Validation**: Multiple reviews until 3 consecutive >95% completion ratings

## API Reference

### `execute()`

```python
async def execute(
    project_dir: str | Path,
    goal: str,
    context: str | None = None,
    mode: ExecutionMode | None = None,  # Auto-detect if None
    run_tests: bool = True,
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
    metadata: dict = field(default_factory=dict)
```

### `estimate_complexity()`

```python
async def estimate_complexity(
    goal: str,
    context: str | None = None,
) -> ComplexityLevel
```

## Configuration

Configure via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | (required) | API key for Claude |
| `FIRETEAM_LOG_LEVEL` | INFO | Logging verbosity |
| `FIRETEAM_COMPLETION_THRESHOLD` | 95 | Minimum completion % for FULL mode |
| `FIRETEAM_VALIDATION_CHECKS` | 3 | Consecutive checks needed in FULL mode |

## Quality Hooks

Fireteam includes SDK hooks for quality enforcement:

- **QUALITY_HOOKS**: Run tests after edits, block user questions
- **AUTONOMOUS_HOOKS**: Block all user interaction
- **DEBUG_HOOKS**: Log all tool usage

```python
from fireteam import execute, QUALITY_HOOKS

result = await execute(
    project_dir="/path/to/project",
    goal="Add feature",
    run_tests=True,  # Enables QUALITY_HOOKS
)
```

## Project Structure

```
fireteam/
├── src/
│   ├── __init__.py      # Public API exports
│   ├── api.py           # Core execute() function
│   ├── complexity.py    # Complexity estimation
│   ├── config.py        # Configuration
│   └── hooks.py         # SDK hooks for quality
├── tests/
│   ├── test_api.py      # API tests
│   ├── test_complexity.py
│   ├── test_hooks.py
│   └── test_integration.py
└── pyproject.toml
```

## Development

```bash
# Clone and install dev dependencies
git clone https://github.com/darkresearch/fireteam
cd fireteam
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Run tests
pytest tests/ -v
```

## License

MIT License
