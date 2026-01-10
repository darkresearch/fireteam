"""Harbor adapter for running fireteam as a benchmark agent."""

import json
import os
import shlex
from pathlib import Path

from harbor.agents.installed.base import BaseInstalledAgent, ExecInput
from harbor.models.agent.context import AgentContext


class FireteamAgent(BaseInstalledAgent):
    """Fireteam agent for Harbor benchmarks."""

    @staticmethod
    def name() -> str:
        return "fireteam"

    @property
    def _install_agent_template_path(self) -> Path:
        return Path(__file__).parent / "install-fireteam.sh.j2"

    def create_run_agent_commands(self, instruction: str) -> list[ExecInput]:
        """Create commands to run fireteam on the task."""
        import base64

        # Base64 encode the instruction to avoid shell escaping issues
        instruction_b64 = base64.b64encode(instruction.encode()).decode()

        env = {
            "ANTHROPIC_API_KEY": os.environ.get("ANTHROPIC_API_KEY", ""),
            "FIRETEAM_INSTRUCTION_B64": instruction_b64,
            # Use "default" permission mode since "bypassPermissions" fails as root
            "FIRETEAM_PERMISSION_MODE": "default",
        }

        # Remove empty values (except instruction which we need)
        env = {k: v for k, v in env.items() if v or k == "FIRETEAM_INSTRUCTION_B64"}

        if self.model_name:
            env["ANTHROPIC_MODEL"] = self.model_name.split("/")[-1]
        elif "ANTHROPIC_MODEL" in os.environ:
            env["ANTHROPIC_MODEL"] = os.environ["ANTHROPIC_MODEL"]

        # Create inline Python script to run fireteam
        python_script = '''
import asyncio
import base64
import json
import os
import sys
from pathlib import Path

# Add fireteam to path if needed
sys.path.insert(0, "/fireteam/src")

try:
    from fireteam import execute
    from fireteam.models import ExecutionMode
except ImportError:
    import fireteam
    from fireteam.api import execute
    from fireteam.models import ExecutionMode

async def main():
    # Decode instruction from base64
    instruction_b64 = os.environ.get("FIRETEAM_INSTRUCTION_B64", "")
    instruction = base64.b64decode(instruction_b64).decode()

    project_dir = Path("/app")

    print(f"Running fireteam on: {project_dir}")
    print(f"Instruction: {instruction[:200]}...")

    result = await execute(
        project_dir=project_dir,
        goal=instruction,
        context="",
        mode=None,  # Auto-detect complexity
        run_tests=True,
        max_iterations=5,
    )

    # Write result to log file
    result_data = {
        "success": result.success,
        "mode": result.mode.value if result.mode else None,
        "output": result.output,
        "error": result.error,
        "completion_percentage": result.completion_percentage,
    }

    with open("/logs/agent/fireteam-result.json", "w") as f:
        json.dump(result_data, f, indent=2)

    print(f"\\nResult: {'success' if result.success else 'failed'}")
    print(f"Completion: {result.completion_percentage}%")

    if result.error:
        print(f"Error: {result.error}")

    return result.success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
'''

        return [
            ExecInput(
                command="mkdir -p /logs/agent",
                env=env,
            ),
            ExecInput(
                command=f"run-fireteam -c {shlex.quote(python_script)} 2>&1 | tee /logs/agent/fireteam.txt",
                env=env,
                cwd="/app",
            ),
        ]

    def populate_context_post_run(self, context: AgentContext) -> None:
        """Parse fireteam results and populate the agent context."""
        result_path = self.logs_dir / "command-1" / "stdout.txt"
        json_result_path = self.logs_dir.parent / "agent" / "fireteam-result.json"

        # Try to read the JSON result
        if json_result_path.exists():
            try:
                with open(json_result_path) as f:
                    result_data = json.load(f)
                print(f"Fireteam result: {result_data}")
            except Exception as e:
                print(f"Failed to parse fireteam result: {e}")
        else:
            print(f"No fireteam result file found at {json_result_path}")

        # For now, we don't have token tracking from fireteam
        # This could be enhanced later
        context.n_input_tokens = 0
        context.n_output_tokens = 0
        context.cost_usd = None
