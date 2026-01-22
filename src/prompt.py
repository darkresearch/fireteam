"""
Prompt handling for Fireteam.

Supports markdown prompts with inline file inclusion:
- @path/to/file.py     - Include single file
- @path/to/directory/  - Include all files in directory
- @path/**/*.py        - Include files matching glob pattern

Example PROMPT.md:
    # Goal
    Build a REST API for user management.

    ## Context
    Here's the existing user model:
    @src/models/user.py

    And the current routes:
    @src/routes/

    ## Requirements
    - Add CRUD endpoints
    - Include validation
"""

import os
import re
import glob as globlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable


# Pattern for inline file includes: @path/to/file or @path/to/dir/
INCLUDE_PATTERN = re.compile(r'@([^\s\n]+)')


@dataclass
class Prompt:
    """
    A prompt for Fireteam execution.

    Can be created from:
    - Simple string goal
    - Markdown file with inline file includes
    - Programmatic construction

    Attributes:
        goal: The main goal/task description
        context: Additional context (expanded file includes)
        raw_content: Original content before expansion
        source_file: Path to source file if loaded from file
        base_dir: Base directory for resolving relative paths
    """

    goal: str
    context: str = ""
    raw_content: str = ""
    source_file: Path | None = None
    base_dir: Path | None = None
    included_files: list[str] = field(default_factory=list)

    @classmethod
    def from_string(cls, goal: str, context: str = "") -> "Prompt":
        """Create a prompt from a simple string."""
        return cls(goal=goal, context=context, raw_content=goal)

    @classmethod
    def from_file(
        cls,
        path: str | Path,
        base_dir: str | Path | None = None,
    ) -> "Prompt":
        """
        Load a prompt from a markdown file.

        Expands inline file includes (@path/to/file).

        Args:
            path: Path to the prompt file
            base_dir: Base directory for resolving relative includes
                     (defaults to prompt file's directory)

        Returns:
            Prompt with expanded file includes
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Prompt file not found: {path}")

        raw_content = path.read_text()
        base_dir = Path(base_dir) if base_dir else path.parent

        prompt = cls(
            goal="",
            raw_content=raw_content,
            source_file=path,
            base_dir=base_dir,
        )
        prompt._expand_includes()
        return prompt

    @classmethod
    def from_editor(
        cls,
        base_dir: str | Path | None = None,
        initial_content: str = "",
    ) -> "Prompt":
        """
        Open an editor for the user to write a prompt.

        Uses $EDITOR or falls back to vim/nano.

        Args:
            base_dir: Base directory for resolving file includes
            initial_content: Initial content to show in editor

        Returns:
            Prompt from editor content
        """
        import subprocess
        import tempfile

        editor = os.environ.get("EDITOR", "vim")

        # Create temp file with initial content
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".md",
            delete=False,
        ) as f:
            if initial_content:
                f.write(initial_content)
            else:
                f.write(_PROMPT_TEMPLATE)
            temp_path = f.name

        try:
            # Open editor
            subprocess.run([editor, temp_path], check=True)

            # Read result
            content = Path(temp_path).read_text()

            # Check if user actually wrote something
            if not content.strip() or content.strip() == _PROMPT_TEMPLATE.strip():
                raise ValueError("No prompt provided - editor content was empty or unchanged")

            base_dir = Path(base_dir) if base_dir else Path.cwd()
            prompt = cls(
                goal="",
                raw_content=content,
                base_dir=base_dir,
            )
            prompt._expand_includes()
            return prompt

        finally:
            # Cleanup temp file
            Path(temp_path).unlink(missing_ok=True)

    @classmethod
    def auto_detect(cls, project_dir: str | Path) -> "Prompt | None":
        """
        Auto-detect a prompt file in the project.

        Looks for (in order):
        1. PROMPT.md
        2. .fireteam/prompt.md
        3. prompt.md
        4. prompt.txt

        Returns:
            Prompt if found, None otherwise
        """
        project_dir = Path(project_dir)
        candidates = [
            project_dir / "PROMPT.md",
            project_dir / ".fireteam" / "prompt.md",
            project_dir / "prompt.md",
            project_dir / "prompt.txt",
        ]

        for path in candidates:
            if path.exists():
                return cls.from_file(path, base_dir=project_dir)

        return None

    def _expand_includes(self) -> None:
        """Expand all @file includes in the raw content."""
        if not self.base_dir:
            self.base_dir = Path.cwd()

        expanded = self.raw_content
        included_files = []

        def replace_include(match: re.Match) -> str:
            include_path = match.group(1)
            full_path = self.base_dir / include_path

            # Handle different include types
            if "**" in include_path or "*" in include_path:
                # Glob pattern
                return self._expand_glob(include_path, included_files)
            elif include_path.endswith("/"):
                # Directory
                return self._expand_directory(full_path, included_files)
            else:
                # Single file
                return self._expand_file(full_path, included_files)

        expanded = INCLUDE_PATTERN.sub(replace_include, expanded)

        self.goal = expanded
        self.included_files = included_files

    def _expand_file(self, path: Path, included: list[str]) -> str:
        """Expand a single file include."""
        if not path.exists():
            return f"[File not found: {path}]"

        if path.is_dir():
            return self._expand_directory(path, included)

        try:
            content = path.read_text()
            included.append(str(path))
            rel_path = path.relative_to(self.base_dir) if self.base_dir else path
            return f"\n```{_guess_language(path)}\n# {rel_path}\n{content}\n```\n"
        except Exception as e:
            return f"[Error reading {path}: {e}]"

    def _expand_directory(self, path: Path, included: list[str]) -> str:
        """Expand a directory include (all files)."""
        if not path.exists() or not path.is_dir():
            return f"[Directory not found: {path}]"

        result = []
        for file_path in sorted(path.rglob("*")):
            if file_path.is_file() and not _should_skip(file_path):
                result.append(self._expand_file(file_path, included))

        return "\n".join(result)

    def _expand_glob(self, pattern: str, included: list[str]) -> str:
        """Expand a glob pattern include."""
        if not self.base_dir:
            return f"[No base directory for glob: {pattern}]"

        full_pattern = str(self.base_dir / pattern)
        matches = sorted(globlib.glob(full_pattern, recursive=True))

        if not matches:
            return f"[No files matched: {pattern}]"

        result = []
        for match in matches:
            path = Path(match)
            if path.is_file() and not _should_skip(path):
                result.append(self._expand_file(path, included))

        return "\n".join(result)

    def render(self) -> str:
        """
        Render the final prompt string.

        Returns the expanded goal with all file includes resolved.
        """
        parts = [self.goal]
        if self.context:
            parts.append(f"\n\n## Additional Context\n{self.context}")
        return "\n".join(parts)

    def __str__(self) -> str:
        return self.render()


def _guess_language(path: Path) -> str:
    """Guess the language for syntax highlighting."""
    ext_map = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".tsx": "tsx",
        ".jsx": "jsx",
        ".rs": "rust",
        ".go": "go",
        ".rb": "ruby",
        ".java": "java",
        ".c": "c",
        ".cpp": "cpp",
        ".h": "c",
        ".hpp": "cpp",
        ".cs": "csharp",
        ".swift": "swift",
        ".kt": "kotlin",
        ".scala": "scala",
        ".sh": "bash",
        ".bash": "bash",
        ".zsh": "zsh",
        ".fish": "fish",
        ".sql": "sql",
        ".md": "markdown",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".toml": "toml",
        ".xml": "xml",
        ".html": "html",
        ".css": "css",
        ".scss": "scss",
        ".less": "less",
    }
    return ext_map.get(path.suffix.lower(), "")


def _should_skip(path: Path) -> bool:
    """Check if a file should be skipped during directory expansion."""
    skip_patterns = [
        "__pycache__",
        ".git",
        ".svn",
        "node_modules",
        ".venv",
        "venv",
        ".env",
        ".DS_Store",
        "*.pyc",
        "*.pyo",
        "*.so",
        "*.dylib",
        "*.dll",
        "*.exe",
        "*.o",
        "*.a",
        "*.class",
    ]

    path_str = str(path)
    for pattern in skip_patterns:
        if pattern.startswith("*"):
            if path.suffix == pattern[1:]:
                return True
        elif pattern in path_str:
            return True

    return False


_PROMPT_TEMPLATE = """# Goal

Describe what you want Fireteam to accomplish.

## Context

Include any relevant context. You can include files inline:
- @src/path/to/file.py     (single file)
- @src/path/to/directory/  (all files in directory)
- @src/**/*.py             (glob pattern)

## Requirements

- List specific requirements
- Be as detailed as needed

## Constraints

- Any constraints or limitations
- Things to avoid
"""


def resolve_prompt(
    goal: str | None = None,
    goal_file: str | Path | None = None,
    project_dir: str | Path | None = None,
    edit: bool = False,
) -> Prompt:
    """
    Resolve a prompt from various sources.

    Priority order:
    1. Explicit goal string
    2. Goal file path
    3. Auto-detected project prompt file
    4. Interactive editor (if edit=True)

    Args:
        goal: Explicit goal string
        goal_file: Path to goal file
        project_dir: Project directory for auto-detection
        edit: Open editor if no other source

    Returns:
        Resolved Prompt

    Raises:
        ValueError: If no prompt source available
    """
    project_dir = Path(project_dir) if project_dir else Path.cwd()

    # 1. Explicit goal string
    if goal:
        return Prompt.from_string(goal)

    # 2. Goal file
    if goal_file:
        return Prompt.from_file(goal_file, base_dir=project_dir)

    # 3. Auto-detect
    auto_prompt = Prompt.auto_detect(project_dir)
    if auto_prompt:
        return auto_prompt

    # 4. Interactive editor
    if edit:
        return Prompt.from_editor(base_dir=project_dir)

    raise ValueError(
        "No prompt provided. Use --goal, --goal-file, create PROMPT.md, or use --edit"
    )
