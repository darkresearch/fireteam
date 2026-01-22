# Fireteam Documentation

Fireteam is a Python library for adaptive task execution using Claude. It automatically estimates task complexity and selects the appropriate execution strategy.

## Contents

- [Introduction](./introduction.md) - Overview and key concepts
- [Quickstart](./quickstart.md) - Get started in 5 minutes
- [Concepts](./concepts/) - Deep dives into core concepts
  - [Complexity Estimation](./concepts/complexity.md)
  - [Execution Modes](./concepts/execution-modes.md)
- [API Reference](./api/) - Full API documentation
  - [execute()](./api/execute.md)
  - [estimate_complexity()](./api/estimate-complexity.md)
  - [Types](./api/types.md)
- [CLI Runner](./cli-runner.md) - tmux-based autonomous execution

## Quick Example

```python
from fireteam import execute

result = await execute(
    project_dir="/path/to/project",
    goal="Fix the authentication bug",
)

if result.success:
    print(f"Completed: {result.completion_percentage}%")
```

## Execution Modes

| Complexity | Mode | Behavior |
|------------|------|----------|
| TRIVIAL | SINGLE_TURN | Direct execution, single pass |
| SIMPLE | SINGLE_TURN | Direct execution, single pass |
| MODERATE | MODERATE | Execute → review loop until >95% complete |
| COMPLEX | FULL | Plan once, then execute → 3 parallel reviews until 2/3 say >95% |
