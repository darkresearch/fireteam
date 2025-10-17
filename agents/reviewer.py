"""
Reviewer Agent - Responsible for assessing project status and completion.
"""

import re
from typing import Any
from .base import BaseAgent


class ReviewerAgent(BaseAgent):
    """Agent responsible for reviewing progress and estimating completion."""

    def __init__(self, logger=None):
        super().__init__("reviewer", logger)

    def execute(
        self,
        project_dir: str,
        goal: str,
        plan: str,
        execution_result: str,
        cycle_number: int,
        is_validation: bool = False
    ) -> dict[str, Any]:
        """
        Review project progress and estimate completion percentage.

        Args:
            project_dir: Path to project directory
            goal: Project goal/objective
            plan: Current plan
            execution_result: Result from last execution
            cycle_number: Current cycle number
            is_validation: Whether this is a validation check

        Returns:
            Dict with success status, review, and completion percentage
        """
        prompt = self._build_review_prompt(
            goal, plan, execution_result, cycle_number, is_validation
        )

        # Execute via Claude CLI
        cmd = self._build_command(prompt, project_dir)
        result = self._execute_command(cmd, project_dir)

        if result["success"]:
            # Extract completion percentage from output
            completion_pct = self._extract_completion_percentage(result["output"])
            return {
                "success": True,
                "review": result["output"],
                "completion_percentage": completion_pct,
                "raw_output": result["output"]
            }
        else:
            return {
                "success": False,
                "review": None,
                "completion_percentage": 0,
                "error": result["error"]
            }

    def _build_review_prompt(
        self,
        goal: str,
        plan: str,
        execution_result: str,
        cycle_number: int,
        is_validation: bool
    ) -> str:
        """Build prompt for project review."""
        validation_note = ""
        if is_validation:
            validation_note = """
VALIDATION MODE:
This is a validation check. The system believes the project is >95% complete.
Be CRITICAL and thorough. Check for:
- Edge cases that might not be handled
- Missing error handling
- Incomplete features
- Testing gaps
- Production-readiness issues

Only confirm high completion if truly production-ready.
"""

        return f"""You are a Reviewer Agent in an autonomous multi-agent system.

PROJECT GOAL:
{goal}

CYCLE NUMBER: {cycle_number}

CURRENT PLAN:
{plan}

LATEST EXECUTION RESULT:
{execution_result}

{validation_note}

YOUR TASK:
Review the project's current state and assess progress. You should:

1. Examine the codebase thoroughly
2. Check what has been implemented vs. planned
3. Test functionality where possible
4. Identify gaps, issues, or incomplete work
5. Assess production-readiness
6. Provide an honest completion estimate

COMPLETION CRITERIA:
- 0%: Nothing started
- 25%: Basic structure in place
- 50%: Core functionality implemented
- 75%: Most features working, needs polish
- 90%: Feature complete, needs testing
- 95%: Production-ready with comprehensive testing
- 100%: Perfect, nothing more needed

OUTPUT FORMAT:
Your response MUST include a completion percentage in this exact format:
COMPLETION: XX%

Then provide:
- Summary of current state
- What's working well
- What's incomplete or broken
- What needs to be done next
- Whether ready for production

Be honest and critical. Don't inflate percentages."""

    def _extract_completion_percentage(self, output: str) -> int:
        """Extract completion percentage from review output."""
        # Look for "COMPLETION: XX%" pattern
        match = re.search(r'COMPLETION:\s*(\d+)%', output, re.IGNORECASE)
        if match:
            return int(match.group(1))

        # Fallback: look for any percentage
        match = re.search(r'(\d+)%', output)
        if match:
            return int(match.group(1))

        # Default to 0 if no percentage found
        self.logger.warning("Could not extract completion percentage from review")
        return 0
