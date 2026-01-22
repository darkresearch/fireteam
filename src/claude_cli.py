"""
Claude Code CLI wrapper for fireteam.

Executes prompts via the `claude` CLI, piggybacking on the user's
existing Claude Code session and credits. This replaces direct
claude-agent-sdk API calls.
"""

import asyncio
import json
import logging
import subprocess
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import AsyncIterator

from .models import PhaseType


# Tool permission sets per phase
PHASE_TOOLS = {
    PhaseType.PLAN: ["Glob", "Grep", "Read"],
    PhaseType.EXECUTE: ["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
    PhaseType.REVIEW: ["Read", "Glob", "Grep", "Bash"],
}

PHASE_PERMISSIONS = {
    PhaseType.PLAN: "plan",
    PhaseType.EXECUTE: "bypassPermissions",
    PhaseType.REVIEW: "plan",
}


@dataclass
class CLIResult:
    """Result from a Claude CLI invocation."""
    success: bool
    output: str
    session_id: str | None = None
    error: str | None = None
    cost_usd: float = 0.0
    duration_ms: int = 0
    raw_json: dict = field(default_factory=dict)


@dataclass
class CLISession:
    """Tracks a Claude Code session for continuity."""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    is_first_call: bool = True

    def mark_used(self):
        """Mark that this session has been used."""
        self.is_first_call = False


class ClaudeCLI:
    """
    Wrapper for Claude Code CLI.

    Uses subprocess to invoke `claude` CLI with structured prompts,
    piggybacking on the user's existing session and credits.
    """

    def __init__(
        self,
        cwd: str | Path,
        model: str = "opus",
        session: CLISession | None = None,
        log: logging.Logger | None = None,
    ):
        self.cwd = Path(cwd)
        self.model = model
        self.session = session or CLISession()
        self.log = log or logging.getLogger("fireteam.cli")

    async def query(
        self,
        prompt: str,
        phase: PhaseType,
        timeout_seconds: int = 600,
    ) -> CLIResult:
        """
        Execute a prompt via Claude CLI.

        Args:
            prompt: The prompt to send
            phase: Phase type (determines tool permissions)
            timeout_seconds: Timeout for the CLI call

        Returns:
            CLIResult with output and metadata
        """
        cmd = self._build_command(prompt, phase)
        self.log.debug(f"Executing CLI: {' '.join(cmd[:5])}...")

        try:
            result = await asyncio.wait_for(
                self._run_subprocess(cmd),
                timeout=timeout_seconds,
            )
            self.session.mark_used()
            return result

        except asyncio.TimeoutError:
            self.log.error(f"CLI timeout after {timeout_seconds}s")
            return CLIResult(
                success=False,
                output="",
                error=f"Timeout after {timeout_seconds} seconds",
                session_id=self.session.session_id,
            )

    def _build_command(self, prompt: str, phase: PhaseType) -> list[str]:
        """Build the claude CLI command."""
        tools = PHASE_TOOLS.get(phase, PHASE_TOOLS[PhaseType.EXECUTE])
        permission_mode = PHASE_PERMISSIONS.get(phase, "default")

        cmd = [
            "claude",
            "--print",  # Non-interactive mode
            "--output-format", "json",  # Structured output
            "--model", self.model,
            "--permission-mode", permission_mode,
            "--allowedTools", ",".join(tools),
        ]

        # Session continuity
        if self.session.is_first_call:
            cmd.extend(["--session-id", self.session.session_id])
        else:
            cmd.extend(["--resume", self.session.session_id])

        # Add prompt
        cmd.extend(["-p", prompt])

        return cmd

    async def _run_subprocess(self, cmd: list[str]) -> CLIResult:
        """Run the subprocess and parse output."""
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.cwd,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                error_msg = stderr.decode("utf-8", errors="replace").strip()
                self.log.error(f"CLI failed: {error_msg}")
                return CLIResult(
                    success=False,
                    output="",
                    error=error_msg or f"Exit code {proc.returncode}",
                    session_id=self.session.session_id,
                )

            return self._parse_output(stdout.decode("utf-8", errors="replace"))

        except FileNotFoundError:
            return CLIResult(
                success=False,
                output="",
                error="Claude CLI not found. Is Claude Code installed?",
            )
        except Exception as e:
            self.log.error(f"Subprocess error: {e}")
            return CLIResult(
                success=False,
                output="",
                error=str(e),
                session_id=self.session.session_id,
            )

    def _parse_output(self, raw: str) -> CLIResult:
        """Parse JSON output from CLI."""
        try:
            data = json.loads(raw)

            # Extract text content from response
            output = ""
            if isinstance(data, dict):
                # Handle different JSON output formats
                if "result" in data:
                    output = data["result"]
                elif "content" in data:
                    content = data["content"]
                    if isinstance(content, str):
                        output = content
                    elif isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict) and "text" in block:
                                output += block["text"]
                elif "message" in data:
                    output = data.get("message", "")

                return CLIResult(
                    success=True,
                    output=output,
                    session_id=data.get("session_id", self.session.session_id),
                    cost_usd=data.get("cost_usd", 0.0),
                    duration_ms=data.get("duration_ms", 0),
                    raw_json=data,
                )
            else:
                # Raw string output
                return CLIResult(
                    success=True,
                    output=str(data),
                    session_id=self.session.session_id,
                )

        except json.JSONDecodeError:
            # If not JSON, treat as plain text
            return CLIResult(
                success=True,
                output=raw.strip(),
                session_id=self.session.session_id,
            )


async def run_cli_query(
    prompt: str,
    phase: PhaseType,
    cwd: str | Path,
    session: CLISession | None = None,
    model: str = "opus",
    timeout_seconds: int = 600,
    log: logging.Logger | None = None,
) -> CLIResult:
    """
    Convenience function to run a single CLI query.

    Args:
        prompt: The prompt to send
        phase: Phase type (determines tool permissions)
        cwd: Working directory
        session: Optional session for continuity
        model: Model to use
        timeout_seconds: Timeout
        log: Logger

    Returns:
        CLIResult with output and metadata
    """
    cli = ClaudeCLI(cwd=cwd, model=model, session=session, log=log)
    return await cli.query(prompt, phase, timeout_seconds)
