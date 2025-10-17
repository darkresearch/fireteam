"""
Base agent class for Claude sub-agents.
Provides common functionality for invoking Claude CLI with specialized prompts.
"""

import subprocess
import logging
import time
import os
from typing import Any
import config


class BaseAgent:
    """Base class for all specialized agents."""

    def __init__(self, agent_type: str, logger: logging.Logger | None = None):
        self.agent_type = agent_type
        self.logger = logger or logging.getLogger(f"agent.{agent_type}")
        self.max_retries = config.MAX_RETRIES
        self.retry_delay = config.RETRY_DELAY
        self.timeout = config.AGENT_TIMEOUTS.get(agent_type, 600)  # Default 10 min if not specified

    def _build_command(self, prompt: str, project_dir: str) -> list:
        """Build Claude CLI command with sub-agent prompt."""
        return [
            config.CLAUDE_CLI,
            "--print",
            config.DANGEROUSLY_SKIP_PERMISSIONS,
            prompt
        ]

    def _execute_command(self, cmd: list, project_dir: str) -> dict[str, Any]:
        """Execute Claude CLI command with retry logic."""
        for attempt in range(self.max_retries):
            try:
                self.logger.info(f"Executing {self.agent_type} (attempt {attempt + 1}/{self.max_retries})")

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,  # Configurable timeout from config.py
                    cwd=project_dir
                )

                if result.returncode == 0:
                    self.logger.info(f"{self.agent_type} completed successfully")
                    return {
                        "success": True,
                        "output": result.stdout,
                        "error": None
                    }
                else:
                    self.logger.warning(f"{self.agent_type} failed with return code {result.returncode}")
                    self.logger.warning(f"stderr: {result.stderr}")

                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay)
                        continue
                    else:
                        return {
                            "success": False,
                            "output": result.stdout,
                            "error": result.stderr
                        }

            except subprocess.TimeoutExpired:
                self.logger.error(f"{self.agent_type} timed out")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
                else:
                    return {
                        "success": False,
                        "output": None,
                        "error": "Command timed out"
                    }

            except Exception as e:
                self.logger.error(f"{self.agent_type} error: {str(e)}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
                else:
                    return {
                        "success": False,
                        "output": None,
                        "error": str(e)
                    }

        return {
            "success": False,
            "output": None,
            "error": f"Failed after {self.max_retries} attempts"
        }

    def execute(self, **kwargs) -> dict[str, Any]:
        """Execute the agent. Must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement execute()")
