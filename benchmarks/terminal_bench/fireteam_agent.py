"""
Fireteam agent implementation for Terminal Bench.

This module implements the AbstractInstalledAgent interface to integrate Fireteam
with Terminal Bench's evaluation harness. It ensures Fireteam runs with full
capabilities (multi-cycle execution, validation system, git integration) without
artificial limitations.

Key Design Principles:
1. Call orchestrator.py directly - no wrapper that limits functionality
2. Full 48-hour timeout to enable perpetual execution
3. Proper permissions setup (fireteam-user with sudo)
4. State isolation between tasks
"""

import os
from pathlib import Path

from terminal_bench.agents.installed_agents.abstract_installed_agent import AbstractInstalledAgent
from terminal_bench.terminal.models import TerminalCommand


class FireteamAgent(AbstractInstalledAgent):
    """
    Terminal Bench agent adapter for Fireteam.

    This adapter exposes Fireteam to Terminal Bench's evaluation harness while
    maintaining full Fireteam capabilities. Each task runs Fireteam's complete
    orchestrator with multi-cycle execution and validation system.
    """

    @staticmethod
    def name() -> str:
        """Return the agent name for Terminal Bench leaderboard."""
        return "fireteam"

    @property
    def _install_agent_script_path(self) -> Path:
        """
        Return path to installation script.

        The installation script sets up Fireteam inside Terminal Bench's Docker
        containers with proper user permissions (fireteam-user with sudo).
        """
        # Path relative to benchmarks/terminal_bench/
        return Path(__file__).parent / "install_fireteam.sh"

    @property
    def _env(self) -> dict[str, str]:
        """
        Return environment variables required by Fireteam.

        Critical environment setup:
        - CLAUDE_CREDENTIALS_PATH: Path to host .claude directory (for OAuth)
        - ANTHROPIC_API_KEY: Optional API key (fallback if OAuth not available)
        - FIRETEAM_HOME: Installation directory
        - PATH: Ensure CLI tools accessible
        - FIRETEAM_BENCHMARK_MODE: Signal we're in benchmark mode
        """
        env = {
            # Fireteam paths
            "FIRETEAM_HOME": "/home/claude/fireteam",

            # Ensure Claude CLI and other tools accessible
            "PATH": "/home/claude/.local/bin:/usr/local/bin:/usr/bin:/bin",

            # Signal benchmark mode (for any specialized logging/behavior)
            "FIRETEAM_BENCHMARK_MODE": "terminal-bench",

            # User context
            "USER": "claude",
            "HOME": "/home/claude",
        }

        # Pass Claude credentials for OAuth session authentication
        # We encode the .claude directory as base64 tarball to transfer into container
        claude_dir = os.path.expanduser("~/.claude")
        if os.path.exists(claude_dir):
            import subprocess
            import base64
            try:
                # Create tarball of .claude directory
                tar_bytes = subprocess.check_output(
                    ["tar", "-czf", "-", "-C", os.path.expanduser("~"), ".claude"],
                    stderr=subprocess.DEVNULL
                )
                # Base64 encode for environment variable
                env["CLAUDE_CREDENTIALS_TAR_GZ_BASE64"] = base64.b64encode(tar_bytes).decode('ascii')
            except Exception as e:
                # If encoding fails, fall back to API key requirement
                print(f"Warning: Could not encode Claude credentials: {e}")

        # Pass local Fireteam directory (with SDK changes) into container
        # This ensures the container uses our latest code instead of cloning from GitHub
        fireteam_dir = Path(__file__).parent.parent.parent  # Go up to /home/claude/fireteam
        if fireteam_dir.exists():
            import subprocess
            import base64
            try:
                # Create tarball of fireteam directory
                # Exclude .git, benchmarks, logs, state to reduce size
                tar_bytes = subprocess.check_output(
                    [
                        "tar", "-czf", "-",
                        "-C", str(fireteam_dir.parent),
                        "--exclude=.git",
                        "--exclude=benchmarks/terminal_bench/.venv",
                        "--exclude=benchmarks/terminal_bench/reports",
                        "--exclude=logs",
                        "--exclude=state",
                        "--exclude=__pycache__",
                        "--exclude=*.pyc",
                        fireteam_dir.name
                    ],
                    stderr=subprocess.DEVNULL
                )
                # Base64 encode for environment variable
                env["FIRETEAM_SOURCE_TAR_GZ_BASE64"] = base64.b64encode(tar_bytes).decode('ascii')
                print(f"Encoded Fireteam source ({len(tar_bytes)} bytes)")
            except Exception as e:
                print(f"Warning: Could not encode Fireteam source: {e}")
                print("Will fall back to cloning from GitHub")

        # Also pass API key if set (fallback authentication)
        if "ANTHROPIC_API_KEY" in os.environ:
            env["ANTHROPIC_API_KEY"] = os.environ["ANTHROPIC_API_KEY"]

        return env

    def _run_agent_commands(self, task_description: str) -> list[TerminalCommand]:
        """
        Return commands to execute Fireteam on the task.

        CRITICAL: This calls Fireteam's full orchestrator with ALL capabilities:
        - Multi-cycle execution (infinite loop until validation)
        - Validation system (3 consecutive 95%+ reviews)
        - Git integration (commits each cycle)
        - State management (isolated per task)

        No artificial constraints or wrappers - this is Fireteam's real performance.

        Args:
            task_description: English description of the task from Terminal Bench

        Returns:
            List containing single TerminalCommand that runs Fireteam orchestrator
            with 48-hour timeout to enable perpetual execution
        """
        # Escape quotes in task description for shell
        escaped_description = task_description.replace('"', '\\"')

        # Run Fireteam's orchestrator directly
        # - Works in /app (Terminal Bench working directory)
        # - Full orchestrator capabilities
        # - Must run as claude user (not root) for Claude Code CLI security
        # - Run in background and explicitly wait to ensure command doesn't return early
        command = (
            f'cd /app && '
            f'su claude -c "cd /app && python3 /home/claude/fireteam/orchestrator.py '
            f'--project-dir /app '
            f'--goal \\"{escaped_description}\\"" & '
            f'PID=$! && wait $PID'
        )

        return [
            TerminalCommand(
                command=command,
                timeout=172800,  # 48 hours in seconds - Fireteam's long-horizon advantage
            )
        ]


# Export for Terminal Bench harness
__all__ = ["FireteamAgent"]
