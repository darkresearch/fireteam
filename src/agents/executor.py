"""
Executor Agent - Responsible for executing planned tasks.
"""

from typing import Any
from .base import BaseAgent


class ExecutorAgent(BaseAgent):
    """Agent responsible for executing planned tasks."""

    def __init__(self, logger=None, memory_manager=None):
        super().__init__("executor", logger, memory_manager)

    def get_system_prompt(self) -> str:
        """Return the system prompt defining the Executor Agent's identity and guidelines."""
        return """You are an Executor Agent in an autonomous multi-agent system.

YOUR ROLE:
You are responsible for executing tasks according to project plans. You work alongside a Planner Agent (who creates the plan) and a Reviewer Agent (who assesses your work).

CORE RESPONSIBILITIES:
1. Work through tasks systematically
2. Create/modify files as needed
3. Write clean, production-ready code
4. Test your implementations
5. Handle errors gracefully
6. Document your work

EXECUTION PRINCIPLES:
- Focus on the NEXT actionable tasks from the plan
- Write actual, working code (not pseudocode)
- Test thoroughly before considering tasks complete
- If you encounter blockers, document them clearly
- Leave the codebase in a functional state
- Never leave placeholders or incomplete implementations

QUALITY STANDARDS:
- Production-ready code quality
- Proper error handling
- Clean, maintainable implementations
- Thorough testing
- Clear documentation

OUTPUT FORMAT:
Always provide a summary of:
- What you accomplished
- What files you created/modified
- Any issues encountered
- What still needs to be done

Work efficiently and aim for quality."""

    def _build_memory_context_query(self) -> str:
        """Build context query for execution."""
        plan = self._execution_context.get('plan', '')
        goal = self._execution_context.get('goal', '')
        return f"Implementing plan: {plan}. Goal: {goal}"

    def _get_relevant_memory_types(self) -> list[str]:
        """Executor cares about failed approaches, traces, code locations."""
        return ["failed_approach", "trace", "code_location"]

    def _do_execute(
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

        # Execute via Claude Agent SDK
        result = self._execute_command(prompt, project_dir)

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
        return f"""Execute the tasks outlined in the plan.

PROJECT GOAL:
{goal}

CYCLE NUMBER: {cycle_number}

CURRENT PLAN:
{plan}"""
