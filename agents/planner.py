"""
Planner Agent - Responsible for creating and updating project plans.
"""

import json
from typing import Dict, Any, Optional
from .base import BaseAgent


class PlannerAgent(BaseAgent):
    """Agent responsible for creating and updating project plans."""

    def __init__(self, logger=None):
        super().__init__("planner", logger)

    def execute(
        self,
        project_dir: str,
        goal: str,
        cycle_number: int,
        previous_plan: Optional[str] = None,
        last_execution_result: Optional[str] = None,
        last_review: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create or update project plan based on current state.

        Args:
            project_dir: Path to project directory
            goal: Project goal/objective
            cycle_number: Current cycle number
            previous_plan: Previous plan (if any)
            last_execution_result: Result from last execution (if any)
            last_review: Review from last cycle (if any)

        Returns:
            Dict with success status and plan
        """
        # Build context-aware prompt
        if cycle_number == 0:
            prompt = self._build_initial_plan_prompt(goal)
        else:
            prompt = self._build_update_plan_prompt(
                goal, previous_plan, last_execution_result, last_review, cycle_number
            )

        # Execute via Claude CLI
        cmd = self._build_command(prompt, project_dir)
        result = self._execute_command(cmd, project_dir)

        if result["success"]:
            # Extract plan from output
            plan = self._extract_plan(result["output"])
            return {
                "success": True,
                "plan": plan,
                "raw_output": result["output"]
            }
        else:
            return {
                "success": False,
                "plan": None,
                "error": result["error"]
            }

    def _build_initial_plan_prompt(self, goal: str) -> str:
        """Build prompt for initial plan creation."""
        return f"""You are a Planner Agent in an autonomous multi-agent system.

PROJECT GOAL:
{goal}

YOUR TASK:
Create a comprehensive, actionable project plan to achieve this goal. Your plan should:

1. Break down the goal into clear, concrete tasks
2. Organize tasks in logical order
3. Identify key milestones
4. Consider edge cases and testing requirements
5. Aim for production-ready quality

OUTPUT FORMAT:
Provide your plan as a structured markdown document with:
- Overview/Summary
- Task breakdown with priorities
- Key milestones
- Testing strategy
- Success criteria

Be specific and actionable. This plan will guide an Executor Agent."""

    def _build_update_plan_prompt(
        self,
        goal: str,
        previous_plan: str,
        last_execution_result: Optional[str],
        last_review: Optional[str],
        cycle_number: int
    ) -> str:
        """Build prompt for plan updates based on progress."""
        return f"""You are a Planner Agent in an autonomous multi-agent system.

PROJECT GOAL:
{goal}

CYCLE NUMBER: {cycle_number}

PREVIOUS PLAN:
{previous_plan}

LAST EXECUTION RESULT:
{last_execution_result or "No execution yet"}

LAST REVIEW:
{last_review or "No review yet"}

YOUR TASK:
Update the project plan based on progress and feedback. Consider:

1. What has been completed successfully?
2. What issues or blockers were encountered?
3. What tasks remain?
4. What adjustments are needed?
5. Are we ready for final validation?

OUTPUT FORMAT:
Provide an updated plan as a structured markdown document with:
- Progress summary
- Updated task list (mark completed tasks)
- Adjusted priorities
- Remaining work
- Next steps

Be specific and actionable."""

    def _extract_plan(self, output: str) -> str:
        """Extract plan from Claude output."""
        # For now, return the full output as the plan
        # Could add more sophisticated parsing if needed
        return output.strip()
