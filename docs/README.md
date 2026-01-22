# Fireteam Documentation

Fireteam is a CLI tool for autonomous task execution using Claude. Give it a goal, let it run until complete.

## Contents

- [Introduction](./introduction.md) - Overview and key concepts
- [Quickstart](./quickstart.md) - Get started in 5 minutes
- [CLI Reference](./cli-runner.md) - Command-line interface
- [Concepts](./concepts/) - Deep dives into core concepts
  - [Complexity Estimation](./concepts/complexity.md)
  - [Execution Modes](./concepts/execution-modes.md)
- [API Reference](./api/) - Python library documentation
  - [execute()](./api/execute.md)
  - [estimate_complexity()](./api/estimate-complexity.md)
  - [Types](./api/types.md)

## Quick Example

```bash
# Create a PROMPT.md with your task
fireteam start
```

Or run in foreground:

```bash
fireteam run
```

## Execution Modes

| Complexity | Mode | Behavior |
|------------|------|----------|
| TRIVIAL | SINGLE_TURN | Direct execution, single pass |
| SIMPLE | SINGLE_TURN | Direct execution, single pass |
| MODERATE | MODERATE | Execute → review loop until ≥95% complete |
| COMPLEX | FULL | Plan once, then execute → 3 parallel reviews until 2/3 say ≥95% |
