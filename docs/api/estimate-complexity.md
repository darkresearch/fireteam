# estimate_complexity()

Estimates the complexity of a task. Used internally by `execute()` when no mode is specified, but can also be called directly.

## Signature

```python
async def estimate_complexity(
    goal: str,
    context: str = "",
    project_dir: str | Path | None = None,
) -> ComplexityLevel
```

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `goal` | `str` | required | The task to analyze |
| `context` | `str` | `""` | Additional context about the task |
| `project_dir` | `str \| Path \| None` | `None` | Project directory for codebase exploration |

## Returns

Returns a `ComplexityLevel` enum value:

```python
class ComplexityLevel(Enum):
    TRIVIAL = "trivial"    # Single-line changes
    SIMPLE = "simple"      # Self-contained tasks
    MODERATE = "moderate"  # Multi-file changes
    COMPLEX = "complex"    # Architectural changes
```

## Examples

### Basic Usage

```python
from fireteam import estimate_complexity

complexity = await estimate_complexity(
    goal="Fix the typo in README.md",
)
# Returns: ComplexityLevel.TRIVIAL
```

### With Context

```python
complexity = await estimate_complexity(
    goal="Add user authentication",
    context="Using FastAPI with existing User model and database",
)
# Returns: ComplexityLevel.MODERATE
```

### With Codebase Exploration

When `project_dir` is provided, Claude can explore the codebase to make a more accurate estimate:

```python
complexity = await estimate_complexity(
    goal="Refactor the authentication system",
    project_dir="/path/to/project",
)
# Claude uses Glob, Grep, Read to understand the project
# Returns: ComplexityLevel.COMPLEX
```

### Use Result for Mode Selection

```python
from fireteam import estimate_complexity, execute, ExecutionMode, ComplexityLevel

complexity = await estimate_complexity(goal="Implement new feature")

# Custom mode selection logic
if complexity == ComplexityLevel.COMPLEX:
    mode = ExecutionMode.FULL
else:
    mode = ExecutionMode.MODERATE

result = await execute(
    project_dir="/path/to/project",
    goal="Implement new feature",
    mode=mode,
)
```

## Complexity Guidelines

### TRIVIAL
- Fix typos
- Add comments
- Simple formatting

### SIMPLE
- Single function implementation
- Add logging
- Fix obvious bugs

### MODERATE
- Refactor a module
- Add feature with tests
- Fix complex bug

### COMPLEX
- Architectural changes
- New subsystems
- Major refactoring

## Implementation Notes

- When `project_dir` is provided, Claude uses read-only tools (Glob, Grep, Read) to explore
- Response is parsed to extract complexity level from the last line
- Defaults to MODERATE if response is unclear
- Handles case-insensitive responses
