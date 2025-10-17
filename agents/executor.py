"""
Executor Agent - Responsible for executing planned tasks.
"""

from typing import Any
from .base import BaseAgent


class ExecutorAgent(BaseAgent):
    """Agent responsible for executing planned tasks."""

    def __init__(self, logger=None):
        super().__init__("executor", logger)

    def execute(
        self,
        project_dir: str,
        goal: str,
        plan: str,
        cycle_number: int
    ) -> dict[str, Any]:
        """
        Execute tasks according to the plan.

        Args:
            project_dir: Path to project directory
            goal: Project goal/objective
            plan: Current plan to execute
            cycle_number: Current cycle number

        Returns:
            Dict with success status and execution results
        """
        prompt = self._build_execution_prompt(goal, plan, cycle_number)

        # Execute via Claude CLI
        cmd = self._build_command(prompt, project_dir)
        result = self._execute_command(cmd, project_dir)

        if result["success"]:
            return {
                "success": True,
                "execution_result": result["output"],
                "raw_output": result["output"]
            }
        else:
            return {
                "success": False,
                "execution_result": None,
                "error": result["error"]
            }

    def _build_execution_prompt(self, goal: str, plan: str, cycle_number: int) -> str:
        """Build prompt for task execution."""
        return f"""You are an Executor Agent in an autonomous multi-agent system.

PROJECT GOAL:
{goal}

CYCLE NUMBER: {cycle_number}

CURRENT PLAN:
{plan}

YOUR TASK:
Execute the tasks outlined in the plan. You should:

1. Work through tasks systematically
2. Create/modify files as needed
3. Write clean, production-ready code
4. Test your implementations
5. Handle errors gracefully
6. Document your work

IMPORTANT:
- Focus on the NEXT actionable tasks from the plan
- Write actual, working code (not pseudocode)
- Test thoroughly before considering tasks complete
- If you encounter blockers, document them clearly
- Leave the codebase in a functional state

OUTPUT FORMAT:
Provide a summary of:
- What you accomplished
- What files you created/modified
- Any issues encountered
- What still needs to be done

Work efficiently and aim for quality. Do not leave placeholders or incomplete implementations."""
