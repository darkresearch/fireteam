# Execution Modes

Fireteam uses different execution strategies based on task complexity. Each mode balances thoroughness against efficiency.

## Mode Overview

```
SINGLE_TURN  →  Execute (one-shot)
MODERATE     →  Execute → Review → loop until ≥95%
FULL         →  Plan → Execute → 3 Reviews → loop until 2/3 say ≥95%
```

## SINGLE_TURN Mode

**For:** Trivial and simple tasks like typo fixes, adding comments, simple bug fixes

**Behavior:**
- Single CLI call
- Full tool access
- No review phase
- Fastest execution

```python
from fireteam import execute, ExecutionMode

result = await execute(
    project_dir="/path/to/project",
    goal="Fix the typo in README.md",
    mode=ExecutionMode.SINGLE_TURN,
)
```

## MODERATE Mode

**For:** Tasks requiring verification but not extensive planning

**Behavior:**
- Execute phase with full tools
- Single review after execution
- Loops until reviewer says ≥95% complete
- Feedback from reviews flows to next iteration

```python
result = await execute(
    project_dir="/path/to/project",
    goal="Refactor the user service",
    mode=ExecutionMode.MODERATE,
)

# Result includes review info
print(result.completion_percentage)  # e.g., 96
print(result.iterations)             # Number of execute→review cycles
```

## FULL Mode

**For:** Complex tasks requiring planning and thorough validation

**Behavior:**
1. **Planning Phase**: Analyze goal, explore codebase, create implementation plan (once at start)
2. **Execution Phase**: Implement according to plan
3. **Review Phase**: 3 parallel reviewers assess completion
4. **Loop**: Continue until 2 of 3 reviewers say ≥95% complete

```python
result = await execute(
    project_dir="/path/to/project",
    goal="Redesign the authentication system",
    mode=ExecutionMode.FULL,
)

# Result includes all phases
print(result.metadata.get("plan"))  # Implementation plan
print(result.completion_percentage)  # Should be ≥95%
```

### Why 3 Parallel Reviewers?

Running 3 reviewers in parallel and requiring 2/3 agreement:
- Reduces false positives from a single biased review
- Provides diverse perspectives on completion
- Catches issues one reviewer might miss
- More robust than single-reviewer assessment

## Dual-Gate Exit

Fireteam uses a dual-gate system to determine when a task is complete:

1. **Reviewer Gate**: Reviewers must say ≥95% complete
2. **Executor Gate**: Executor can signal `WORK_COMPLETE: false` to continue even if reviewers are satisfied

This respects Claude's judgment - if the executor believes more work is needed, iteration continues.

## Mode Selection

### Automatic (Recommended)

Let Fireteam choose based on complexity estimation:

```python
result = await execute(
    project_dir="/path/to/project",
    goal="Your task here",
    # mode not specified - auto-detect
)

print(f"Used mode: {result.mode}")
```

### Manual Override

Force a specific mode:

```python
# Be thorough with a simple task
result = await execute(
    project_dir="/path/to/project",
    goal="Add a comment",
    mode=ExecutionMode.FULL,
)

# Be quick with a moderate task
result = await execute(
    project_dir="/path/to/project",
    goal="Refactor module",
    mode=ExecutionMode.SINGLE_TURN,
)
```

## Iteration Limits

By default, MODERATE and FULL modes loop indefinitely until completion. Set a limit:

```python
result = await execute(
    project_dir="/path/to/project",
    goal="Complex refactoring",
    max_iterations=10,  # Stop after 10 iterations
)

if not result.success and result.iterations >= 10:
    print("Hit iteration limit before completion")
```

## Tool Access by Phase

| Phase | Tools Available |
|-------|-----------------|
| Planning | Glob, Grep, Read (read-only) |
| Execution | Read, Write, Edit, Bash, Glob, Grep |
| Review | Glob, Grep, Read (read-only) |

Planners and reviewers have read-only access to prevent unintended modifications during analysis phases.
