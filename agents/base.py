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
            self.logger.info(f"[{self.agent_type}] Initializing ClaudeSDKClient...")
            async with ClaudeSDKClient(options=options) as client:
                # Set working directory
                original_dir = os.getcwd()
                os.chdir(project_dir)
                self.logger.info(f"[{self.agent_type}] Changed working directory to: {project_dir}")

                # Execute the prompt - send query first
                self.logger.info(f"[{self.agent_type}] Sending query to Claude SDK...")
                start_time = time.time()
                await client.query(prompt)
                query_time = time.time() - start_time
                self.logger.info(f"[{self.agent_type}] Query sent in {query_time:.2f}s, now receiving response...")
                
                # Then receive messages from the response
                messages = []
                message_count = 0
                async for message in client.receive_response():
                    message_count += 1
                    messages.append(message)
                    msg_type = type(message).__name__
                    self.logger.info(f"[{self.agent_type}] Received message #{message_count}: {msg_type}")
                    
                response_time = time.time() - start_time
                self.logger.info(f"[{self.agent_type}] Received {len(messages)} messages total in {response_time:.2f}s")
                
                # Restore original directory
                os.chdir(original_dir)
                
                # Extract text from messages
                # Collect all text blocks from assistant messages
                output_text = ""
                for msg in messages:
                    if hasattr(msg, 'content'):
                        # Message has content blocks
                        for block in msg.content:
                            if hasattr(block, 'text'):
                                output_text += block.text + "\n"
                            elif isinstance(block, dict) and 'text' in block:
                                output_text += block['text'] + "\n"
                            elif isinstance(block, str):
                                output_text += block + "\n"
                    elif isinstance(msg, str):
                        output_text += msg + "\n"
                    elif isinstance(msg, dict):
                        output_text += str(msg) + "\n"
                    else:
                        output_text += str(msg) + "\n"

                if not output_text.strip():
                    error_msg = f"Received {len(messages)} messages but no extractable text content. Messages: {[type(m).__name__ for m in messages]}"
                    self.logger.warning(f"[{self.agent_type}] {error_msg}")
                    output_text = error_msg

                output_length = len(output_text)
                self.logger.info(f"[{self.agent_type}] Extracted {output_length} characters of output")
                if output_length > 200:
                    self.logger.info(f"[{self.agent_type}] Output preview: {output_text[:200]}...")
                else:
                    self.logger.info(f"[{self.agent_type}] Full output: {output_text}")

                return {
                    "success": True,
                    "output": output_text.strip(),
                    "error": None
                }

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            self.logger.error(f"[{self.agent_type}] SDK execution error: {str(e)}")
            self.logger.error(f"[{self.agent_type}] Traceback:\n{error_details}")
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
