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

```bash
fireteam run -m single_turn
```

## MODERATE Mode

**For:** Tasks requiring verification but not extensive planning

**Behavior:**
- Execute phase with full tools
- Single review after execution
- Loops until reviewer says ≥95% complete
- Feedback from reviews flows to next iteration

```bash
fireteam run -m moderate
```

## FULL Mode

**For:** Complex tasks requiring planning and thorough validation

**Behavior:**
1. **Planning Phase**: Analyze goal, explore codebase, create implementation plan (once at start)
2. **Execution Phase**: Implement according to plan
3. **Review Phase**: 3 parallel reviewers assess completion
4. **Loop**: Continue until 2 of 3 reviewers say ≥95% complete

```bash
fireteam start -m full
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

```bash
fireteam start  # Mode auto-detected from task complexity
```

### Manual Override

Force a specific mode:

```bash
# Be thorough with a simple task
fireteam start -m full

# Be quick with a moderate task
fireteam start -m single_turn
```

## Iteration Limits

By default, MODERATE and FULL modes loop indefinitely until completion. Set a limit:

```bash
fireteam start --max-iterations 10
```

## Tool Access by Phase

| Phase | Tools Available |
|-------|-----------------|
| Planning | Glob, Grep, Read (read-only) |
| Execution | Read, Write, Edit, Bash, Glob, Grep |
| Review | Glob, Grep, Read (read-only) |

Planners and reviewers have read-only access to prevent unintended modifications during analysis phases.
