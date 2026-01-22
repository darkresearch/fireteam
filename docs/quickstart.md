# Quickstart

Get started with Fireteam in 5 minutes.

## Installation

Install Fireteam using uv or pip:

```bash
uv add fireteam
# or
pip install fireteam
```

**Requirements:**
- Python 3.12+
- Claude Code CLI installed

## Basic Usage

### Execute a Task

The simplest way to use Fireteam is with the `execute()` function:

```python
import asyncio
from fireteam import execute

async def main():
    result = await execute(
        project_dir="/path/to/your/project",
        goal="Fix the bug in auth.py where users can't log in",
    )

    if result.success:
        print(f"Task completed!")
        print(f"Output: {result.output}")
        print(f"Completion: {result.completion_percentage}%")
    else:
        print(f"Task failed: {result.error}")

asyncio.run(main())
```

### Add Context

Provide additional context to help Claude understand the task:

```python
result = await execute(
    project_dir="/path/to/project",
    goal="Fix the authentication bug",
    context="""
    Error logs show:
    - NullPointerException at auth.py:42
    - Users report login failures after password reset
    """,
)
```

### Specify Execution Mode

Force a specific execution mode instead of auto-detection:

```python
from fireteam import execute, ExecutionMode

# Use full plan+execute+review cycle for complex tasks
result = await execute(
    project_dir="/path/to/project",
    goal="Refactor the entire authentication module",
    mode=ExecutionMode.FULL,
)

# Use single-turn for trivial tasks
result = await execute(
    project_dir="/path/to/project",
    goal="Add a comment explaining the login function",
    mode=ExecutionMode.SINGLE_TURN,
)
```

### Limit Iterations

By default, Fireteam loops until completion. Set a maximum:

```python
result = await execute(
    project_dir="/path/to/project",
    goal="Refactor the user service",
    max_iterations=10,  # Stop after 10 iterations if not complete
)
```

## Using PROMPT.md Files

Instead of passing a goal string, you can use a PROMPT.md file with inline file includes:

```markdown
# Task

Fix the authentication bug.

## Context

@src/auth.py
@tests/test_auth.py

## Requirements

- Users should be able to log in after password reset
- All existing tests must pass
```

Then execute:

```python
result = await execute(
    project_dir="/path/to/project",
    goal_file="PROMPT.md",  # or auto-detected if present
)
```

## Complexity Estimation

Use `estimate_complexity()` to understand how Fireteam will handle a task:

```python
from fireteam import estimate_complexity, ComplexityLevel

complexity = await estimate_complexity(
    goal="Add user authentication with OAuth",
    context="Using FastAPI and existing user model",
)

print(f"Complexity: {complexity}")
# ComplexityLevel.MODERATE
```

## Understanding Results

The `ExecutionResult` contains:

```python
result = await execute(project_dir=".", goal="Fix bug")

# Check success
if result.success:
    print(result.output)              # Execution output
    print(result.completion_percentage)  # 0-100
    print(result.iterations)          # Number of iterations
    print(result.metadata)            # Additional info
else:
    print(result.error)               # Error message

# Always available
print(result.mode)  # ExecutionMode used
```

## CLI Runner

For long-running autonomous tasks, use the tmux-based runner:

```bash
# Start a background session
python -m fireteam.runner start --project-dir /path/to/project --goal "Complete the feature"

# List running sessions
python -m fireteam.runner list

# Attach to watch progress
python -m fireteam.runner attach fireteam-myproject

# View logs
python -m fireteam.runner logs fireteam-myproject
```

See [CLI Runner](./cli-runner.md) for more details.

## Next Steps

- [Execution Modes](./concepts/execution-modes.md) - Learn about the different execution strategies
- [Complexity Estimation](./concepts/complexity.md) - Understand how tasks are classified
- [API Reference](./api/execute.md) - Full API documentation
