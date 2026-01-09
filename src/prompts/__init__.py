"""
Prompt loading utilities.

Loads prompts from markdown files in this directory.
"""

from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent


def load_prompt(name: str) -> str:
    """
    Load a prompt from a markdown file.

    Args:
        name: Prompt name (without .md extension)

    Returns:
        Prompt content as string
    """
    prompt_file = _PROMPTS_DIR / f"{name}.md"
    return prompt_file.read_text().strip()


# Pre-load prompts for convenience
EXECUTOR_PROMPT = load_prompt("executor")
REVIEWER_PROMPT = load_prompt("reviewer")
PLANNER_PROMPT = load_prompt("planner")
COMPLEXITY_PROMPT = load_prompt("complexity")
