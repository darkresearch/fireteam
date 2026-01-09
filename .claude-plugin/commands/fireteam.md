# /fireteam

Multi-phase autonomous task execution with complexity-based routing.

## Usage

```
/fireteam <goal>
```

## Configuration

Set these environment variables to configure fireteam behavior:

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | (required) | API key for Claude |
| `FIRETEAM_MAX_ITERATIONS` | (none/infinite) | Maximum loop iterations. Leave unset for infinite. |
| `FIRETEAM_LOG_LEVEL` | INFO | Logging verbosity (DEBUG, INFO, WARNING, ERROR) |

## Examples

```
/fireteam Fix the authentication bug in auth.py
/fireteam Refactor the user module to use dependency injection
/fireteam Add comprehensive tests for the payment service
```

## How It Works

1. **Complexity Estimation**: Analyzes your goal and estimates complexity (TRIVIAL, SIMPLE, MODERATE, COMPLEX)
2. **Mode Selection**: Routes to appropriate execution strategy:
   - TRIVIAL/SIMPLE → SINGLE_TURN (one-shot execution)
   - MODERATE → Execute → Review loop until >95% complete
   - COMPLEX → Plan → Execute → 3 Parallel Reviews loop until 2/3 majority says >95%
3. **Loop Until Complete**: MODERATE and FULL modes loop continuously until the task is complete or max_iterations is reached (if set)

## Configuration via Code

When using fireteam as a library:

```python
from fireteam import execute, ExecutionMode

# Infinite iterations (default)
result = await execute(
    project_dir="/path/to/project",
    goal="Implement feature X",
)

# Limited iterations
result = await execute(
    project_dir="/path/to/project",
    goal="Implement feature X",
    max_iterations=10,  # Stop after 10 iterations if not complete
)

# Force a specific mode
result = await execute(
    project_dir="/path/to/project",
    goal="Implement feature X",
    mode=ExecutionMode.FULL,
    max_iterations=5,
)
```
