# Introduction

Fireteam is a Python library for adaptive task execution using Claude Code CLI. It automatically estimates task complexity and selects the appropriate execution strategy, running tasks to completion with built-in review loops.

## Key Features

- **Adaptive Execution** - Automatically estimates task complexity and selects the best execution mode
- **Multi-Phase Workflow** - Plan, execute, and review phases for complex tasks
- **Loop Until Complete** - Continues iterating until reviewers confirm completion (≥95%)
- **Parallel Reviews** - Complex tasks get 3 parallel reviewers with majority consensus
- **Simple API** - One function to execute any task: `execute()`

## How It Works

When you call `execute()`, Fireteam:

1. **Estimates complexity** - Analyzes the goal to determine if it's trivial, simple, moderate, or complex
2. **Selects execution mode** - Maps complexity to the appropriate execution strategy
3. **Executes the task** - Runs the appropriate phases (plan, execute, review)
4. **Loops until complete** - For moderate/complex tasks, iterates until completion threshold is met
5. **Returns results** - Provides success status, output, and completion percentage

```python
from fireteam import execute

result = await execute(
    project_dir="/path/to/project",
    goal="Fix the authentication bug",
)

print(f"Success: {result.success}")
print(f"Completion: {result.completion_percentage}%")
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
- [Execution Modes](./concepts/execution-modes.md) - Learn about the different strategies
- [API Reference](./api/execute.md) - Full API documentation
