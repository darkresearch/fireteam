# Fireteam Agent Principles

These principles are automatically loaded by the Claude Agent SDK and guide all fireteam operations.

## Testing

- Write tests as you implement (not as an afterthought)
- Run tests after every code change
- Don't consider a task complete until tests pass
- If tests fail, fix them before moving on

## Quality Gates

- All CI checks must pass locally before completion
- Run linting, type checking, and tests before considering work done
- If any quality check fails, address it immediately

## Progress Checkpoints

- After significant progress, step back and reassess
- Ask yourself: How are we doing? What's left? Is this more complex than expected?
- Update your todo list to reflect current understanding
- If the task has grown beyond the original estimate, flag it for re-evaluation

## Escalation

- If stuck after 3 attempts on the same issue, consider a different approach
- If a task turns out to be more complex than estimated, communicate this
- Don't silently struggle - surface blockers early

## Code Quality

- Write clean, readable code with clear intent
- Follow existing patterns in the codebase
- Add comments only where the logic isn't self-evident
- Don't over-engineer - solve the problem at hand

## Minimal Changes

- Make the smallest change that solves the problem
- Don't refactor unrelated code
- Don't add features that weren't requested
- Keep diffs focused and reviewable
