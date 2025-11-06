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

    def __init__(self, agent_type: str, logger: logging.Logger | None = None, memory_manager=None):
        self.agent_type = agent_type
        self.logger = logger or logging.getLogger(f"agent.{agent_type}")
        self.memory = memory_manager  # Injected by orchestrator
        self.max_retries = config.MAX_RETRIES
        self.retry_delay = config.RETRY_DELAY
        self.timeout = config.AGENT_TIMEOUTS.get(agent_type, 600)  # Default 10 min if not specified
        self._execution_context = {}  # Store for memory retrieval

    def get_system_prompt(self) -> str:
        """
        Get the system prompt for this agent.
        Must be implemented by subclasses to define agent identity and core guidelines.
        """
        raise NotImplementedError("Subclasses must implement get_system_prompt()")

    async def _execute_with_sdk(self, prompt: str, project_dir: str) -> dict[str, Any]:
        """Execute prompt using Claude Agent SDK, automatically injecting memories into system prompt."""
        try:
            # Import SDK and error types
            from claude_agent_sdk import (
                ClaudeSDKClient, 
                ClaudeAgentOptions,
                CLINotFoundError,
                CLIConnectionError,
                ProcessError
            )

            # Get base system prompt
            base_system_prompt = self.get_system_prompt()
            
            # Automatic memory retrieval (happens silently to agent)
            memory_context = self._retrieve_and_format_memories()
            
            # Inject memories into system prompt
            enhanced_system_prompt = base_system_prompt
            if memory_context:
                enhanced_system_prompt += "\n" + memory_context
                self.logger.debug(f"[{self.agent_type.upper()}] System prompt enhanced with memories")

            # Configure SDK options
            # Note: API key is read from ANTHROPIC_API_KEY environment variable
            options = ClaudeAgentOptions(
                allowed_tools=config.SDK_ALLOWED_TOOLS,
                permission_mode=config.SDK_PERMISSION_MODE,
                model=config.SDK_MODEL,
                cwd=project_dir,  # Set working directory for Claude Code
                system_prompt=enhanced_system_prompt  # Enhanced with memories
            )

            # Execute with SDK
            async with ClaudeSDKClient(options=options) as client:
                # Set working directory
                os.chdir(project_dir)

                # Send the query
                await client.query(prompt)
                self.logger.debug(f"Prompt has kicked off: {prompt!r}")

                output_text = ""
                async for message in client.receive_response():
                    self.logger.info(f"Received SDK message: {message!r}")

                    # Collect all text from the response
                    if hasattr(message, 'content'):
                        if isinstance(message.content, str):
                            output_text += message.content
                        elif isinstance(message.content, list):
                            for block in message.content:
                                if hasattr(block, 'text'):
                                    output_text += block.text
                                elif isinstance(block, dict) and 'text' in block:
                                    output_text += block['text']
                    elif isinstance(message, str):
                        output_text += message
                    elif isinstance(message, dict):
                        # Try common keys
                        output_text += message.get('content', '') or message.get('text', '')

                # Validate we got actual output
                if not output_text or len(output_text.strip()) == 0:
                    error_msg = "SDK returned empty output - Claude may have failed silently"
                    self.logger.error(error_msg)
                    return {
                        "success": False,
                        "output": None,
                        "error": error_msg
                    }

                return {
                    "success": True,
                    "output": output_text,
                    "error": None
                }

        except Exception as e:
            # Try to import error types for better error messages
            try:
                from claude_agent_sdk import CLINotFoundError, CLIConnectionError, ProcessError
                
                if isinstance(e, CLINotFoundError):
                    self.logger.error("Claude Code CLI not found - check that 'claude' is in PATH")
                elif isinstance(e, CLIConnectionError):
                    self.logger.error("Failed to connect to Claude Code CLI - check if CLI is responsive")
                elif isinstance(e, ProcessError):
                    self.logger.error(f"Claude Code CLI process error: {str(e)}")
                else:
                    self.logger.error(f"SDK execution error: {str(e)}")
            except ImportError:
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

    def _build_memory_context_query(self) -> str:
        """
        Build context query for semantic search.
        Override in subclasses to customize based on agent type.
        Access self._execution_context for execute() parameters.
        """
        return ""

    def _get_relevant_memory_types(self) -> list[str]:
        """
        Return memory types relevant to this agent.
        Override in subclasses.
        """
        return []  # All types by default

    def _retrieve_and_format_memories(self) -> str:
        """Automatically retrieve and format relevant memories."""
        if not self.memory:
            return ""
        
        # Build context query
        context_query = self._build_memory_context_query()
        if not context_query:
            return ""
        
        self.logger.info(f"[{self.agent_type.upper()}] Retrieving memories...")
        start_time = time.time()
        
        # Semantic search
        memories = self.memory.search(
            query=context_query,
            limit=config.MEMORY_SEARCH_LIMIT,
            memory_types=self._get_relevant_memory_types() or None
        )
        
        elapsed = time.time() - start_time
        self.logger.info(f"[{self.agent_type.upper()}] Retrieved {len(memories)} memories in {elapsed:.2f}s")
        
        if not memories:
            self.logger.info(f"[{self.agent_type.upper()}] No relevant memories found")
            return ""
        
        # Format for injection (cleaner template)
        memory_lines = []
        for mem in memories:
            mem_type = mem.get('type', 'learning').replace('_', ' ').title()
            content = mem.get('content', '')
            cycle = mem.get('cycle', '?')
            memory_lines.append(f"• {mem_type} (Cycle {cycle}): {content}")
        
        memory_text = f"""
---
BACKGROUND KNOWLEDGE FROM PREVIOUS WORK:
(You have access to these learnings from earlier cycles)

{"\n".join(memory_lines)}

Use this background knowledge naturally. Don't explicitly reference cycles.
---
"""
        
        return memory_text

    def execute(self, **kwargs) -> dict[str, Any]:
        """
        Template method - handles memory injection automatically.
        Subclasses should NOT override this - override _do_execute instead.
        """
        # Store execution context for memory retrieval
        self._execution_context = kwargs
        
        # Call subclass implementation
        return self._do_execute(**kwargs)

    def _do_execute(self, **kwargs) -> dict[str, Any]:
        """
        Subclass implementation of execute logic.
        Subclasses override this instead of execute().
        """
        raise NotImplementedError("Subclasses must implement _do_execute()")
