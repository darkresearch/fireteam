"""
Claude Code hooks for fireteam plugin.

These hooks integrate fireteam with Claude Code's hook system,
enabling the /fireteam on|off mode toggle.
"""

from .user_prompt_submit import is_fireteam_enabled

__all__ = ["is_fireteam_enabled"]
