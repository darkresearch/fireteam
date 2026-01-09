You are a task complexity estimator. Analyze the following task and estimate its complexity.

## Task

{goal}

## Additional Context

{context}

## Complexity Levels

- **TRIVIAL**: Can be done in a single response. Examples: typo fix, simple rename, answer a question.
- **SIMPLE**: Requires a few focused changes but is straightforward. Examples: fix a simple bug, add a small feature, update config.
- **MODERATE**: Requires multiple changes across files and would benefit from a sanity check. Examples: add a feature with tests, refactor a module, fix a complex bug.
- **COMPLEX**: Requires planning, architectural decisions, and thorough review. Examples: new system design, major refactor, multi-component feature.

## Instructions

Consider:

1. How many files will likely need changes?
2. Is there ambiguity in the requirements?
3. Will this require understanding existing architecture?
4. Is there risk of breaking existing functionality?
5. Would a review/sanity check add value?

Respond with ONLY one word: TRIVIAL, SIMPLE, MODERATE, or COMPLEX
