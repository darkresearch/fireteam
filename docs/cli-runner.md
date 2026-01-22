# CLI Runner

Fireteam includes a tmux-based runner for long-running autonomous tasks. This allows you to start a task, detach, and come back later to check on progress.

## Requirements

- tmux installed (`brew install tmux` on macOS)
- Claude Code CLI installed

## Commands

### Start a Session

```bash
python -m fireteam.runner start \
    --project-dir /path/to/project \
    --goal "Complete the feature implementation"
```

Options:
- `--project-dir` - Project directory (required)
- `--goal` - Task goal string
- `--goal-file` - Path to PROMPT.md file (alternative to --goal)
- `--mode` - Execution mode: single_turn, moderate, full (optional)
- `--context` - Additional context (optional)
- `--max-iterations` - Maximum iterations (optional)
- `--session-name` - Custom session name (optional)

### List Sessions

```bash
python -m fireteam.runner list
```

Shows all running Fireteam sessions with their status.

### Attach to a Session

```bash
python -m fireteam.runner attach fireteam-myproject
```

Attaches to a running session to watch progress in real-time. Press `Ctrl+B D` to detach.

### View Logs

```bash
python -m fireteam.runner logs fireteam-myproject

# Show more lines
python -m fireteam.runner logs fireteam-myproject -n 200

# Follow (like tail -f)
python -m fireteam.runner logs fireteam-myproject -f
```

### Kill a Session

```bash
python -m fireteam.runner kill fireteam-myproject
```

Terminates a running session.

### Run Directly (Blocking)

```bash
python -m fireteam.runner run \
    --project-dir /path/to/project \
    --goal "Fix the bug"
```

Runs in the foreground without tmux. Useful for debugging or short tasks.

## Session Names

By default, session names are generated from the project directory:
- `/path/to/myproject` → `fireteam-myproject`

You can specify a custom name with `--session-name`.

## Log Files

Logs are stored in `~/.fireteam/logs/` with timestamps:
```
~/.fireteam/logs/fireteam-myproject_20240115_143022.log
```

## State Files

Session state is stored in `~/.fireteam/`:
```
~/.fireteam/fireteam-myproject.json   # Session info
~/.fireteam/fireteam-myproject_prompt.md  # Resolved prompt
```

## Example Workflow

```bash
# Start a long-running task
python -m fireteam.runner start \
    --project-dir ~/projects/myapp \
    --goal-file PROMPT.md \
    --mode full

# Check on it later
python -m fireteam.runner list

# Watch progress
python -m fireteam.runner attach fireteam-myapp

# Detach with Ctrl+B D

# Check final logs
python -m fireteam.runner logs fireteam-myapp

# Clean up
python -m fireteam.runner kill fireteam-myapp
```

## Using with PROMPT.md

Create a `PROMPT.md` file with your task and file includes:

```markdown
# Task

Refactor the authentication system to use JWT tokens.

## Current Implementation

@src/auth/
@src/middleware/auth.py

## Requirements

- Replace session-based auth with JWT
- Maintain backward compatibility for 1 week
- Add refresh token support
- Update all tests
```

Then start:

```bash
python -m fireteam.runner start \
    --project-dir ~/projects/myapp \
    --goal-file PROMPT.md
```

## Programmatic Usage

You can also use the runner functions from Python:

```python
from fireteam import start_session, list_sessions, attach_session, kill_session

# Start a session
info = start_session(
    project_dir="/path/to/project",
    goal="Complete the feature",
    mode=ExecutionMode.FULL,
)
print(f"Started: {info.session_name}")

# List sessions
for session in list_sessions():
    print(f"{session.session_name}: {session.status}")

# Kill a session
kill_session("fireteam-myproject")
```
