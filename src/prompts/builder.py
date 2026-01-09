"""
Prompt builder for fireteam phases.

Builds prompts by combining base templates with:
- Goal and context
- Plan (for execute phase)
- Previous feedback (for iteration loops)
"""

from ..models import PhaseType
from . import EXECUTOR_PROMPT, REVIEWER_PROMPT, PLANNER_PROMPT


def build_prompt(
    phase: PhaseType,
    goal: str,
    context: str = "",
    plan: str | None = None,
    execution_output: str | None = None,
    previous_feedback: str | None = None,
    reviewer_id: int | None = None,
    iteration: int | None = None,
) -> str:
    """
    Build a phase-specific prompt with accumulated context.

    Args:
        phase: The execution phase (PLAN, EXECUTE, REVIEW)
        goal: The task goal
        context: Additional context (crash logs, etc.)
        plan: Implementation plan (for EXECUTE phase)
        execution_output: Output from execution (for REVIEW phase)
        previous_feedback: Feedback from previous iteration
        reviewer_id: Reviewer number (for parallel reviews)
        iteration: Current iteration number

    Returns:
        Complete prompt string
    """
    if phase == PhaseType.PLAN:
        return _build_plan_prompt(goal, context)
    elif phase == PhaseType.EXECUTE:
        return _build_execute_prompt(goal, context, plan, previous_feedback)
    elif phase == PhaseType.REVIEW:
        return _build_review_prompt(
            goal, execution_output, plan, previous_feedback, reviewer_id, iteration
        )
    else:
        raise ValueError(f"Unknown phase: {phase}")


def _build_plan_prompt(goal: str, context: str) -> str:
    """Build planning phase prompt."""
    parts = [PLANNER_PROMPT, "", f"Goal: {goal}"]

    if context:
        parts.extend(["", f"Context:\n{context}"])

    return "\n".join(parts)


def _build_execute_prompt(
    goal: str,
    context: str,
    plan: str | None,
    previous_feedback: str | None,
) -> str:
    """Build execution phase prompt with optional plan and feedback."""
    parts = [EXECUTOR_PROMPT, "", f"Goal: {goal}"]

    if context:
        parts.extend(["", f"Context:\n{context}"])

    if plan:
        parts.extend(["", f"Plan:\n{plan}"])

    if previous_feedback:
        parts.extend([
            "",
            "IMPORTANT - Address this feedback from the previous iteration:",
            previous_feedback,
        ])

    return "\n".join(parts)


def _build_review_prompt(
    goal: str,
    execution_output: str | None,
    plan: str | None,
    previous_feedback: str | None,
    reviewer_id: int | None,
    iteration: int | None,
) -> str:
    """Build review phase prompt."""
    parts = [REVIEWER_PROMPT]

    # Add context about which reviewer this is
    if reviewer_id is not None or iteration is not None:
        context_parts = []
        if reviewer_id:
            context_parts.append(f"Reviewer #{reviewer_id}")
        if iteration:
            context_parts.append(f"Iteration {iteration}")
        parts.extend(["", f"[{' - '.join(context_parts)}]"])

    parts.extend(["", f"Goal: {goal}"])

    if plan:
        # Truncate long plans
        plan_text = plan[:1500] + "..." if len(plan) > 1500 else plan
        parts.extend(["", f"Implementation plan:\n{plan_text}"])

    if execution_output:
        # Truncate long outputs
        output_text = execution_output[:2000] + "..." if len(execution_output) > 2000 else execution_output
        parts.extend(["", f"Execution output:\n{output_text}"])

    if previous_feedback:
        parts.extend(["", f"Previous review feedback:\n{previous_feedback}"])

    return "\n".join(parts)
