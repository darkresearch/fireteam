# Complexity Estimation

Fireteam automatically estimates task complexity to select the appropriate execution strategy.

## Complexity Levels

| Level | Description | Examples |
|-------|-------------|----------|
| **TRIVIAL** | Single-line changes | Typo fixes, adding comments |
| **SIMPLE** | Self-contained changes | Single-file modifications, simple bug fixes |
| **MODERATE** | Multi-file changes | Refactoring a module, adding a feature with tests |
| **COMPLEX** | Architectural changes | Major refactoring, new subsystems |

## How It Works

When you run `fireteam start` or `fireteam run` without specifying a mode, Fireteam:

1. Sends your goal and context to Claude
2. Claude analyzes the scope using read-only tools (Glob, Grep, Read)
3. Returns a complexity level based on the analysis
4. Fireteam maps the complexity to an execution mode

```bash
# Let Fireteam auto-detect complexity
fireteam start

# Force a specific mode
fireteam start -m full
```

## Complexity to Mode Mapping

| Complexity | Mode | Behavior |
|------------|------|----------|
| TRIVIAL | SINGLE_TURN | Single CLI call, no review |
| SIMPLE | SINGLE_TURN | Single CLI call, no review |
| MODERATE | MODERATE | Execute + review loop until ≥95% |
| COMPLEX | FULL | Plan + execute + 3 parallel reviews until 2/3 say ≥95% |

## Classification Guidelines

### TRIVIAL Tasks

- Fix typos
- Add/remove comments
- Rename a single variable
- Simple formatting changes

### SIMPLE Tasks

- Implement a single function
- Add logging to existing code
- Fix a straightforward bug
- Update configuration values

### MODERATE Tasks

- Refactor a module
- Add a new feature with tests
- Fix a bug requiring investigation
- Update multiple related files

### COMPLEX Tasks

- Major architectural changes
- Implement new subsystems
- Large-scale refactoring
- Cross-cutting concerns

## Manual Override

You can bypass complexity estimation by specifying the mode directly:

```bash
# Force FULL mode for thorough execution
fireteam start -m full

# Force SINGLE_TURN for quick execution
fireteam start -m single_turn
```

## Codebase Exploration

Fireteam explores the codebase using read-only tools to make accurate complexity estimates. Providing relevant files in your PROMPT.md helps with this:

```markdown
# Task

Add logging to the auth module.

## Context

@src/auth/
```

The included files give Claude context for a more accurate complexity assessment.
