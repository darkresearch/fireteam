# Quickstart

Get started with Fireteam in 5 minutes.

## Installation

```bash
# Install as a CLI tool
pipx install fireteam
# or
uv tool install fireteam
```

**Requirements:**
- Python 3.12+
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) installed

## Basic Usage

### 1. Create a PROMPT.md

In your project directory, create a `PROMPT.md` file:

```markdown
# Task

Fix the bug in auth.py where users can't log in.

## Context

@src/auth.py
@tests/test_auth.py

## Requirements

- Users should be able to log in after password reset
- All existing tests must pass
```

### 2. Start Fireteam

```bash
# Start a background session (tmux)
fireteam start

# Or run in foreground
fireteam run
```

### 3. Monitor Progress

```bash
# List running sessions
fireteam list

# Attach to watch live
fireteam attach fireteam-myproject

# View logs
fireteam logs fireteam-myproject
```

## CLI Options

### Specify a Goal Directly

```bash
fireteam start -g "Fix the authentication bug"
```

### Use a Different Project Directory

```bash
fireteam start -p /path/to/project
```

### Force an Execution Mode

```bash
# Use full plan+execute+review cycle for complex tasks
fireteam start -m full

# Use single-turn for trivial tasks
fireteam start -m single_turn
```

### Limit Iterations

```bash
fireteam start --max-iterations 10
```

## PROMPT.md Format

Use `@` syntax to include files in your prompt:

```markdown
# Task

Refactor the authentication system to use JWT tokens.

## Current Implementation

@src/auth/
@src/middleware/auth.py

## Requirements

- Replace session-based auth with JWT
- Add refresh token support
- Update all tests

## Additional Context

@docs/auth-spec.md
```

Include patterns:
- `@path/to/file.py` - Single file
- `@path/to/directory/` - All files in directory
- `@src/**/*.py` - Glob pattern

## Complexity Estimation

Fireteam automatically estimates task complexity:

| Complexity | Mode | Behavior |
|------------|------|----------|
| TRIVIAL | SINGLE_TURN | Direct execution, single pass |
| SIMPLE | SINGLE_TURN | Direct execution, single pass |
| MODERATE | MODERATE | Execute → review loop until ≥95% complete |
| COMPLEX | FULL | Plan once, then execute → 3 parallel reviews until 2/3 say ≥95% |

## Library Usage

Fireteam can also be used as a Python library:

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

See [API Reference](./api/execute.md) for full library documentation.

## Next Steps

- [CLI Reference](./cli-runner.md) - Full command documentation
- [Execution Modes](./concepts/execution-modes.md) - Learn about the different execution strategies
- [Complexity Estimation](./concepts/complexity.md) - Understand how tasks are classified
