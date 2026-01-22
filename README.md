# Fireteam

Autonomous task execution with Claude. Give it a goal, let it run until complete.

## Installation

```bash
# Install as a CLI tool
pipx install fireteam
# or
uv tool install fireteam
```

Requires Python 3.12+ and [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) installed.

## Quick Start

1. Create a `PROMPT.md` file in your project:

```markdown
# Task

Fix the authentication bug where users can't log in after password reset.

## Context

@src/auth.py
@tests/test_auth.py
```

2. Run Fireteam:

```bash
# Start a background session (tmux)
fireteam start

# Or run in foreground
fireteam run
```

3. Monitor progress:

```bash
# List running sessions
fireteam list

# Attach to watch live
fireteam attach fireteam-myproject

# View logs
fireteam logs fireteam-myproject
```

## How It Works

Fireteam estimates task complexity and routes to the appropriate execution strategy:

| Complexity | Mode | Behavior |
|------------|------|----------|
| TRIVIAL | SINGLE_TURN | Direct execution, single pass |
| SIMPLE | SINGLE_TURN | Direct execution, single pass |
| MODERATE | MODERATE | Execute → review loop until ≥95% complete |
| COMPLEX | FULL | Plan once, then execute → 3 parallel reviews until 2/3 say ≥95% |

It loops until the task is complete—no babysitting required.

## CLI Reference

### `fireteam start`

Start a background session in tmux:

```bash
fireteam start                           # Use PROMPT.md in current directory
fireteam start -p /path/to/project       # Specify project directory
fireteam start -f task.md                # Use specific goal file
fireteam start -g "Fix the bug"          # Pass goal as string
fireteam start -m full                   # Force execution mode
fireteam start --max-iterations 10       # Limit iterations
```

### `fireteam run`

Run in foreground (blocking):

```bash
fireteam run                             # Use PROMPT.md in current directory
fireteam run -p /path/to/project         # Specify project directory
```

### `fireteam list`

List all running Fireteam sessions.

### `fireteam attach <session>`

Attach to a running session to watch progress. Detach with `Ctrl+B D`.

### `fireteam logs <session>`

View session logs:

```bash
fireteam logs fireteam-myproject         # Last 50 lines
fireteam logs fireteam-myproject -n 200  # Last 200 lines
```

### `fireteam kill <session>`

Terminate a running session.

## PROMPT.md Format

Fireteam auto-detects `PROMPT.md` (or `fireteam.prompt.md`, `prompt.md`) in your project directory. Use `@` syntax to include files:

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

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `FIRETEAM_MAX_ITERATIONS` | unlimited | Max loop iterations |
| `FIRETEAM_LOG_LEVEL` | INFO | Logging verbosity |

## Library Usage

Fireteam can also be used as a Python library:

```python
from fireteam import execute

result = await execute(
    project_dir="/path/to/project",
    goal="Fix the authentication bug",
)

if result.success:
    print(f"Completed in {result.iterations} iterations")
```

See [docs/](./docs/) for full API documentation.

## Development

```bash
git clone https://github.com/darkresearch/fireteam
cd fireteam
uv sync --extra dev
uv run pytest tests/ -v
```

## License

MIT License
