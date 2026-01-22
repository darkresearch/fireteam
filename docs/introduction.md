# Introduction

Fireteam is a CLI tool for autonomous task execution using Claude. Give it a goal, let it run until complete. It automatically estimates task complexity and selects the appropriate execution strategy, looping until reviewers confirm completion.

## Key Features

- **Autonomous Execution** - Define a task in PROMPT.md, run `fireteam start`, and walk away
- **Adaptive Complexity** - Automatically estimates task complexity and selects the best execution mode
- **Multi-Phase Workflow** - Plan, execute, and review phases for complex tasks
- **Loop Until Complete** - Continues iterating until reviewers confirm completion (≥95%)
- **Parallel Reviews** - Complex tasks get 3 parallel reviewers with majority consensus
- **Background Sessions** - Uses tmux for detached execution with live monitoring

## How It Works

When you run `fireteam start` or `fireteam run`:

1. **Reads your PROMPT.md** - Loads the task goal and any included files
2. **Estimates complexity** - Analyzes the goal to determine if it's trivial, simple, moderate, or complex
3. **Selects execution mode** - Maps complexity to the appropriate execution strategy
4. **Executes the task** - Runs the appropriate phases (plan, execute, review)
5. **Loops until complete** - For moderate/complex tasks, iterates until completion threshold is met

```bash
# Create your PROMPT.md
cat > PROMPT.md << 'EOF'
# Task

Fix the authentication bug where users can't log in after password reset.

## Context

@src/auth.py
@tests/test_auth.py
EOF

# Start autonomous execution
fireteam start

# Monitor progress
fireteam logs fireteam-myproject
```

## Execution Modes

| Complexity | Mode | Phases |
|------------|------|--------|
| TRIVIAL | SINGLE_TURN | Direct execution |
| SIMPLE | SINGLE_TURN | Direct execution |
| MODERATE | MODERATE | Execute + review loop |
| COMPLEX | FULL | Plan + execute + 3 parallel reviews loop |

## When to Use Fireteam

Fireteam is ideal for:

- **Autonomous task execution** - Let Claude complete tasks without constant supervision
- **Complex refactoring** - Multi-file changes with validation
- **Feature implementation** - Plan, implement, and verify new features
- **Bug fixing** - Analyze, fix, and confirm resolution

## Architecture

Fireteam wraps the Claude Code CLI, piggybacking on your existing Claude Code session and credits. This means:

- No separate API key required
- Uses your existing Claude Code billing
- Inherits Claude Code's tool permissions and safety features

## Next Steps

- [Quickstart](./quickstart.md) - Get started in 5 minutes
- [CLI Reference](./cli-runner.md) - Full command documentation
- [Execution Modes](./concepts/execution-modes.md) - Learn about the different strategies
