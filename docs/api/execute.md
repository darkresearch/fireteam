# execute()

The main function for executing tasks. Automatically estimates complexity and selects the appropriate execution strategy.

## Signature

```python
async def execute(
    project_dir: str | Path,
    goal: str | None = None,
    goal_file: str | Path | None = None,
    context: str = "",
    mode: ExecutionMode | None = None,
    max_iterations: int | None = None,
    session: CLISession | None = None,
    circuit_breaker: CircuitBreaker | None = None,
    logger: logging.Logger | None = None,
) -> ExecutionResult
```

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `project_dir` | `str \| Path` | required | Path to the project directory |
| `goal` | `str \| None` | `None` | The task to accomplish |
| `goal_file` | `str \| Path \| None` | `None` | Path to PROMPT.md file |
| `context` | `str` | `""` | Additional context for the task |
| `mode` | `ExecutionMode \| None` | `None` | Execution mode (auto-detect if None) |
| `max_iterations` | `int \| None` | `None` | Max loop iterations (None = infinite) |
| `session` | `CLISession \| None` | `None` | CLI session for continuity |
| `circuit_breaker` | `CircuitBreaker \| None` | `None` | Stuck loop detection |
| `logger` | `Logger \| None` | `None` | Custom logger |

**Note:** Either `goal` or `goal_file` must be provided, or a PROMPT.md file must exist in `project_dir`.

## Returns

Returns an `ExecutionResult`:

```python
@dataclass
class ExecutionResult:
    success: bool              # Whether the task completed successfully
    mode: ExecutionMode        # The execution mode used
    output: str | None         # Execution output
    error: str | None          # Error message if failed
    completion_percentage: int # 0-100 completion estimate
    iterations: int            # Number of iterations
    metadata: dict             # Additional info (plan, review, etc.)
```

## Examples

### Basic Usage

```python
from fireteam import execute

result = await execute(
    project_dir="/path/to/project",
    goal="Fix the login bug",
)

if result.success:
    print(f"Done! Output: {result.output}")
```

### With Context

```python
result = await execute(
    project_dir="/path/to/project",
    goal="Fix the authentication error",
    context="""
    Error from logs:
    TypeError: 'NoneType' object is not subscriptable
    at auth.py:42 in validate_token()
    """,
)
```

### Using PROMPT.md

```python
# With explicit file
result = await execute(
    project_dir="/path/to/project",
    goal_file="PROMPT.md",
)

# Auto-detect (looks for PROMPT.md, fireteam.prompt.md, etc.)
result = await execute(
    project_dir="/path/to/project",
)
```

### Specify Mode

```python
from fireteam import execute, ExecutionMode

result = await execute(
    project_dir="/path/to/project",
    goal="Refactor the user module",
    mode=ExecutionMode.FULL,
)
```

### Limit Iterations

```python
result = await execute(
    project_dir="/path/to/project",
    goal="Complex refactoring",
    max_iterations=10,
)
```

## Execution Flow

1. **Resolve Prompt** - Load goal from string, file, or auto-detect PROMPT.md
2. **Complexity Estimation** (if mode not specified)
   - Analyzes goal and context
   - Returns TRIVIAL, SIMPLE, MODERATE, or COMPLEX
3. **Mode Selection**
   - TRIVIAL/SIMPLE → SINGLE_TURN
   - MODERATE → MODERATE
   - COMPLEX → FULL
4. **Execution** (varies by mode)
   - SINGLE_TURN: Direct execution
   - MODERATE: Execute + review loop
   - FULL: Plan + execute + parallel reviews loop
5. **Result** - Returns ExecutionResult with success status, output, and metadata

## Error Handling

The function catches exceptions and returns them in the result:

```python
result = await execute(
    project_dir="/nonexistent/path",
    goal="Do something",
)

if not result.success:
    print(f"Error: {result.error}")
```
