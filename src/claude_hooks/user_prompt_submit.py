"""
Claude Code hook that intercepts user prompts when fireteam mode is enabled.

When fireteam mode is ON:
1. Reads the user's task from stdin
2. Invokes fireteam.execute() with the task
3. Returns the result to Claude Code
"""
import asyncio
import json
import sys
from pathlib import Path
from typing import Any


def is_fireteam_enabled() -> bool:
    """Check session state for fireteam mode."""
    state_file = Path.home() / ".claude" / "fireteam_state.json"
    if state_file.exists():
        try:
            state: dict[str, Any] = json.loads(state_file.read_text())
            enabled = state.get("enabled", False)
            return bool(enabled)
        except (OSError, json.JSONDecodeError):
            return False
    return False


async def main() -> None:
    """Main hook entry point."""
    input_data: dict[str, Any] = json.loads(sys.stdin.read())

    if not is_fireteam_enabled():
        # Fireteam mode is OFF - pass through normally
        print(json.dumps({}))
        return

    # Fireteam mode is ON - inject orchestration context
    user_prompt: str = input_data.get("prompt", "")
    cwd: str = input_data.get("cwd", ".")

    # Import and run fireteam (use relative import)
    from ..api import execute

    result = await execute(
        project_dir=cwd,
        goal=user_prompt,
    )

    # Return result to Claude Code
    output: dict[str, Any] = {
        "hookSpecificOutput": {
            "additionalContext": f"Fireteam completed with {result.completion_percentage}% completion.\n\nResult:\n{result.output}",
        }
    }

    if not result.success:
        output["hookSpecificOutput"]["additionalContext"] += f"\n\nError: {result.error}"

    print(json.dumps(output))


if __name__ == "__main__":
    asyncio.run(main())
