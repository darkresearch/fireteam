# CLI Reference

Fireteam includes a tmux-based runner for autonomous task execution. Start a task, detach, and come back later to check on progress.

## Requirements

- tmux installed (`brew install tmux` on macOS)
- Claude Code CLI installed

## Commands

### Start a Session

```bash
fireteam start                           # Use PROMPT.md in current directory
fireteam start -p /path/to/project       # Specify project directory
fireteam start -f task.md                # Use specific goal file
fireteam start -g "Fix the bug"          # Pass goal as string
fireteam start -m full                   # Force execution mode
fireteam start --max-iterations 10       # Limit iterations
```

Options:
- `-p, --project-dir` - Project directory (default: current directory)
- `-g, --goal` - Task goal string
- `-f, --goal-file` - Path to PROMPT.md file (default: auto-detect)
- `-m, --mode` - Execution mode: single_turn, moderate, full
- `-c, --context` - Additional context
- `--max-iterations` - Maximum iterations
- `-s, --session-name` - Custom session name

### Run in Foreground

```bash
fireteam run                             # Use PROMPT.md in current directory
fireteam run -p /path/to/project         # Specify project directory
```

Runs in the foreground without tmux. Useful for debugging or short tasks.

### List Sessions

```bash
fireteam list
```

Shows all running Fireteam sessions with their status.

### Attach to a Session

```bash
fireteam attach fireteam-myproject
```

Attaches to a running session to watch progress in real-time. Press `Ctrl+B D` to detach.

### View Logs

```bash
fireteam logs fireteam-myproject         # Last 50 lines
fireteam logs fireteam-myproject -n 200  # Last 200 lines
```

### Kill a Session

```bash
fireteam kill fireteam-myproject
```

Terminates a running session.

## Session Names

By default, session names are generated from the project directory:
- `/path/to/myproject` → `fireteam-myproject`

You can specify a custom name with `-s` or `--session-name`.

## Log Files

Logs are stored in `~/.fireteam/logs/` with timestamps:
```
~/.fireteam/logs/fireteam-myproject_20240115_143022.log
```

## State Files

Session state is stored in `~/.fireteam/`:
```
~/.fireteam/fireteam-myproject.json      # Session info
~/.fireteam/fireteam-myproject_prompt.md # Resolved prompt
```

## Example Workflow

```bash
# Create your PROMPT.md
cat > PROMPT.md << 'EOF'
# Task

Refactor the authentication system to use JWT tokens.

## Context

@src/auth/
@src/middleware/auth.py

## Requirements

- Replace session-based auth with JWT
- Add refresh token support
- Update all tests
EOF

# Start the task
fireteam start -m full

# Check on it later
fireteam list

# Watch progress
fireteam attach fireteam-myproject

# Detach with Ctrl+B D

# Check final logs
fireteam logs fireteam-myproject

# Clean up
fireteam kill fireteam-myproject
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FIRETEAM_MAX_ITERATIONS` | unlimited | Max loop iterations |
| `FIRETEAM_LOG_LEVEL` | INFO | Logging verbosity |
