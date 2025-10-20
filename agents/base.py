"""
Base agent class for Claude sub-agents.
Provides common functionality for invoking Claude Agent SDK with specialized prompts.
"""

import logging
import time
import os
import asyncio
from typing import Any
import config


class BaseAgent:
    """Base class for all specialized agents using Claude Agent SDK."""

    def __init__(self, agent_type: str, logger: logging.Logger | None = None):
        self.agent_type = agent_type
        self.logger = logger or logging.getLogger(f"agent.{agent_type}")
        self.max_retries = config.MAX_RETRIES
        self.retry_delay = config.RETRY_DELAY
        self.timeout = config.AGENT_TIMEOUTS.get(agent_type, 600)  # Default 10 min if not specified

    async def _execute_with_sdk(self, prompt: str, project_dir: str) -> dict[str, Any]:
        """Execute prompt using Claude Agent SDK."""
        try:
            # Import SDK here to avoid issues if not installed
            from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

            # Configure SDK options
            # Note: API key is read from ANTHROPIC_API_KEY environment variable
            options = ClaudeAgentOptions(
                allowed_tools=config.SDK_ALLOWED_TOOLS,
                permission_mode=config.SDK_PERMISSION_MODE,
                model=config.SDK_MODEL,
                system_prompt=f"You are a {self.agent_type} agent. Work in the project directory: {project_dir}"
            )

            # Execute with SDK
            async with ClaudeSDKClient(options=options) as client:
                # Set working directory
                os.chdir(project_dir)

                # Execute the prompt
                response = await client.query(prompt)

                # Extract text from response
                # SDK response might be a dict, string, or object
                if response is None:
                    output_text = ""
                elif isinstance(response, str):
                    output_text = response
                elif isinstance(response, dict):
                    # Try common response keys
                    output_text = response.get('content') or response.get('text') or str(response)
                elif hasattr(response, 'content'):
                    output_text = response.content
                else:
                    output_text = str(response)

                return {
                    "success": True,
                    "output": output_text,
                    "error": None
                }

        except Exception as e:
            self.logger.error(f"SDK execution error: {str(e)}")
            return {
                "success": False,
                "output": None,
                "error": str(e)
            }

    def _execute_command(self, prompt: str, project_dir: str) -> dict[str, Any]:
        """Execute Claude Agent SDK with retry logic."""
        for attempt in range(self.max_retries):
            try:
                self.logger.info(f"Executing {self.agent_type} (attempt {attempt + 1}/{self.max_retries})")

                # Run async SDK call in sync context
                result = asyncio.run(self._execute_with_sdk(prompt, project_dir))

                if result["success"]:
                    self.logger.info(f"{self.agent_type} completed successfully")
                    return result
                else:
                    self.logger.warning(f"{self.agent_type} failed")
                    self.logger.warning(f"error: {result['error']}")

                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay)
                        continue
                    else:
                        return result

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
