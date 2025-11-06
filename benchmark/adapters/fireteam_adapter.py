"""Fireteam adapter for terminal-bench using AbstractInstalledAgent."""

import os
import shlex
from pathlib import Path

from dotenv import load_dotenv
from terminal_bench.agents.installed_agents.abstract_installed_agent import (
    AbstractInstalledAgent,
)
from terminal_bench.terminal.models import TerminalCommand

# Load .env file from Fireteam root if it exists
_fireteam_root = Path(__file__).parent.parent.parent
_env_file = _fireteam_root / ".env"
if _env_file.exists():
    load_dotenv(_env_file)


class FireteamAdapter(AbstractInstalledAgent):
    """
    Terminal-bench adapter for Fireteam.
    
    Fireteam is a multi-agent orchestrator that runs planning, execution, and review
    cycles until a project is complete. This adapter installs and runs Fireteam
    inside terminal-bench task containers.
    """

    @staticmethod
    def name() -> str:
        """Return the agent name for terminal-bench."""
        return "fireteam"
    
    @property
    def _env(self) -> dict[str, str]:
        """
        Environment variables for Fireteam execution.
        
        Returns:
            Dictionary of environment variables to set in the container
        """
        env_vars = {
            "ANTHROPIC_API_KEY": os.environ["ANTHROPIC_API_KEY"],
            "FIRETEAM_DIR": "/app",  # Use task directory for state/logs
            "ANTHROPIC_MODEL": os.environ.get(
                "ANTHROPIC_MODEL", 
                "claude-sonnet-4-20250514"
            ),
        }
        
        # Pass through LOG_LEVEL if set
        if "LOG_LEVEL" in os.environ:
            env_vars["LOG_LEVEL"] = os.environ["LOG_LEVEL"]
        
        return env_vars
    
    @property
    def _install_agent_script_path(self) -> Path:
        """
        Path to the installation script.
        
        Returns:
            Path to fireteam-setup.sh
        """
        return Path(__file__).parent / "fireteam-setup.sh"
    
    def _run_agent_commands(self, instruction: str) -> list[TerminalCommand]:
        """
        Commands to execute Fireteam with the task instruction.
        
        Args:
            instruction: The task description from terminal-bench
            
        Returns:
            List of terminal commands to run Fireteam
        """
        # Use base64 encoding to completely avoid quoting issues
        import base64
        
        # Build environment exports
        env_exports = [
            "export PYTHONPATH=/fireteam",
            "export PATH=/usr/local/bin:/usr/bin:/bin:$PATH",
            f"export ANTHROPIC_API_KEY='{os.environ['ANTHROPIC_API_KEY']}'",
            "export FIRETEAM_DIR='/app'",
            f"export ANTHROPIC_MODEL='{os.environ.get('ANTHROPIC_MODEL', 'claude-sonnet-4-20250514')}'"
        ]
        
        # Add LOG_LEVEL if set
        if "LOG_LEVEL" in os.environ:
            env_exports.append(f"export LOG_LEVEL='{os.environ['LOG_LEVEL']}'")
        
        run_script = (
            "#!/bin/bash\n"
            "cd /fireteam\n"
            # Set up environment
            + "\n".join(env_exports) + "\n"
            + f"python3 -u orchestrator.py --project-dir /app --goal {shlex.quote(instruction)}\n"
        )
        encoded_script = base64.b64encode(run_script.encode()).decode()
        
        return [
            # Set permissions for claude user to access /app and /fireteam
            TerminalCommand(
                command="chown -R claude:claude /app /fireteam",
                min_timeout_sec=0.0,
                max_timeout_sec=10.0,
                block=True,
                append_enter=True,
            ),
            # Write and run Fireteam as claude user (using base64 to avoid quoting)
            TerminalCommand(
                command=(
                    f"echo {encoded_script} | base64 -d > /tmp/run-fireteam.sh && "
                    f"chmod +x /tmp/run-fireteam.sh && "
                    f"su claude -c /tmp/run-fireteam.sh"
                ),
                min_timeout_sec=0.0,
                max_timeout_sec=float("inf"),  # Terminal-bench handles timeout
                block=True,
                append_enter=True,
            ),
        ]
    
    def perform_task(self, instruction, session, logging_dir):
        """
        Override to copy Fireteam code before setup.
        
        This copies the Fireteam codebase into the container at /fireteam
        before running the installation script and executing the task.
        
        Args:
            instruction: Task description
            session: TmuxSession for container interaction
            logging_dir: Directory for logs
            
        Returns:
            AgentResult with execution details
        """
        # Copy Fireteam code into container before running setup script
        fireteam_root = Path(__file__).parent.parent.parent
        
        # Create directory structure in container first
        session.container.exec_run(["mkdir", "-p", "/fireteam/agents", "/fireteam/state"])
        
        # Copy main files
        session.copy_to_container(
            paths=[fireteam_root / "orchestrator.py"],
            container_dir="/fireteam",
            container_filename="orchestrator.py"
        )
        session.copy_to_container(
            paths=[fireteam_root / "config.py"],
            container_dir="/fireteam",
            container_filename="config.py"
        )
        session.copy_to_container(
            paths=[fireteam_root / "__init__.py"],
            container_dir="/fireteam",
            container_filename="__init__.py"
        )
        
        # Copy agents module files
        for agent_file in (fireteam_root / "agents").glob("*.py"):
            session.copy_to_container(
                paths=[agent_file],
                container_dir="/fireteam/agents",
                container_filename=agent_file.name
            )
        
        # Copy state module files
        for state_file in (fireteam_root / "state").glob("*.py"):
            session.copy_to_container(
                paths=[state_file],
                container_dir="/fireteam/state",
                container_filename=state_file.name
            )
        
        # Run parent's setup and execution
        return super().perform_task(instruction, session, logging_dir)

