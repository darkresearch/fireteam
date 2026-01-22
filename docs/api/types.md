# Types

Type definitions for Fireteam.

## ExecutionMode

Enum for execution strategies.

```python
from fireteam import ExecutionMode

class ExecutionMode(Enum):
    SINGLE_TURN = "single_turn"  # Direct execution, no review
    MODERATE = "moderate"        # Execute + review loop
    FULL = "full"                # Plan + execute + parallel reviews loop
```

### Values

| Value | Description |
|-------|-------------|
| `SINGLE_TURN` | Direct execution for trivial/simple tasks |
| `MODERATE` | Execute with single reviewer loop |
| `FULL` | Plan + execute + 3 parallel reviewers loop |

## ComplexityLevel

Enum for task complexity classification.

```python
from fireteam import ComplexityLevel

class ComplexityLevel(Enum):
    TRIVIAL = "trivial"    # Single-line changes
    SIMPLE = "simple"      # Self-contained tasks
    MODERATE = "moderate"  # Multi-file changes
    COMPLEX = "complex"    # Architectural changes
```

### Mapping to ExecutionMode

| ComplexityLevel | ExecutionMode |
|-----------------|---------------|
| `TRIVIAL` | `SINGLE_TURN` |
| `SIMPLE` | `SINGLE_TURN` |
| `MODERATE` | `MODERATE` |
| `COMPLEX` | `FULL` |

## ExecutionResult

Dataclass containing execution results.

```python
from dataclasses import dataclass, field
from fireteam import ExecutionMode

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

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `success` | `bool` | Whether the task completed successfully |
| `mode` | `ExecutionMode` | The execution mode that was used |
| `output` | `str \| None` | Execution output/result text |
| `error` | `str \| None` | Error message if failed |
| `completion_percentage` | `int` | 0-100 completion estimate |
| `iterations` | `int` | Number of execute-review iterations |
| `metadata` | `dict` | Additional info (plan, review, etc.) |

### Example

```python
from fireteam import execute

result = await execute(
    project_dir="/path/to/project",
    goal="Fix the bug",
)

print(result.success)              # True
print(result.mode)                 # ExecutionMode.MODERATE
print(result.output)               # "Fixed the null pointer exception..."
print(result.completion_percentage) # 96
print(result.iterations)           # 2
print(result.metadata)             # {"plan": "...", "reviews": [...]}
```

## CLISession

Tracks a Claude Code CLI session for continuity.

```python
from fireteam import CLISession

@dataclass
class CLISession:
    session_id: str          # Unique session identifier
    is_first_call: bool      # Whether this is the first call in session
```

Used internally to maintain session state across multiple CLI calls.

## CircuitBreaker

Detects stuck execution loops.

```python
from fireteam import CircuitBreaker, create_circuit_breaker

breaker = create_circuit_breaker(
    no_progress_threshold=3,      # Warn after 3 iterations with no file changes
    repeated_error_threshold=5,   # Warn after 5 identical errors
    output_decline_threshold=0.7, # Warn on 70% output length decline
)
```

The circuit breaker warns (but doesn't halt) when patterns indicate the loop is stuck.

## Prompt

Represents a parsed PROMPT.md file with inline includes.

```python
from fireteam import Prompt, resolve_prompt

# Auto-detect and load
prompt = resolve_prompt(project_dir="/path/to/project")

# Or from explicit file
prompt = resolve_prompt(goal_file="PROMPT.md", project_dir="/path/to/project")

# Or from string
prompt = resolve_prompt(goal="Fix the bug", project_dir="/path/to/project")

# Access properties
print(prompt.goal)           # The task goal
print(prompt.raw_content)    # Original content
print(prompt.included_files) # List of included file paths
print(prompt.render())       # Expanded content with file includes
```

## SessionInfo

Information about a running tmux session.

```python
from fireteam import SessionInfo

@dataclass
class SessionInfo:
    session_name: str
    project_dir: str
    goal: str
    started_at: str
    pid: int | None
    log_file: str | None
    status: Literal["running", "completed", "failed", "unknown"]
```

Used by the CLI runner to track background sessions.
