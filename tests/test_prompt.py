"""Unit tests for prompt parsing and file inclusion."""

from pathlib import Path

import pytest

from fireteam.prompt import Prompt, _guess_language, _should_skip, resolve_prompt


class TestPromptFromString:
    """Tests for Prompt.from_string()."""

    def test_creates_prompt_from_goal(self):
        """Creates a simple prompt from a goal string."""
        prompt = Prompt.from_string("Fix the bug in auth.py")
        assert prompt.goal == "Fix the bug in auth.py"
        assert prompt.context == ""

    def test_includes_context_when_provided(self):
        """Includes context in the prompt."""
        prompt = Prompt.from_string("Fix bug", context="Error: NullPointer")
        assert prompt.goal == "Fix bug"
        assert prompt.context == "Error: NullPointer"

    def test_render_returns_goal(self):
        """Render returns the goal."""
        prompt = Prompt.from_string("Do something")
        assert prompt.render() == "Do something"

    def test_render_includes_context(self):
        """Render includes context when present."""
        prompt = Prompt.from_string("Do something", context="Extra info")
        rendered = prompt.render()
        assert "Do something" in rendered
        assert "Extra info" in rendered
        assert "Additional Context" in rendered


class TestPromptFromFile:
    """Tests for Prompt.from_file()."""

    def test_loads_simple_markdown(self, tmp_path):
        """Loads a simple markdown file."""
        prompt_file = tmp_path / "PROMPT.md"
        prompt_file.write_text("# Goal\nBuild a REST API")

        prompt = Prompt.from_file(prompt_file)
        assert "Build a REST API" in prompt.goal

    def test_raises_on_missing_file(self, tmp_path):
        """Raises FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError):
            Prompt.from_file(tmp_path / "nonexistent.md")

    def test_expands_single_file_include(self, tmp_path):
        """Expands @path/to/file includes."""
        # Create source file
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "auth.py").write_text("def login(): pass")

        # Create prompt file
        prompt_file = tmp_path / "PROMPT.md"
        prompt_file.write_text("# Goal\nFix the auth module\n@src/auth.py")

        prompt = Prompt.from_file(prompt_file, base_dir=tmp_path)
        assert "def login(): pass" in prompt.goal
        assert "auth.py" in prompt.goal
        assert str(src_dir / "auth.py") in prompt.included_files

    def test_expands_directory_include(self, tmp_path):
        """Expands @path/to/dir/ includes."""
        # Create source files
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "a.py").write_text("file_a = 1")
        (src_dir / "b.py").write_text("file_b = 2")

        # Create prompt file
        prompt_file = tmp_path / "PROMPT.md"
        prompt_file.write_text("# Goal\nRefactor these files\n@src/")

        prompt = Prompt.from_file(prompt_file, base_dir=tmp_path)
        assert "file_a = 1" in prompt.goal
        assert "file_b = 2" in prompt.goal
        assert len(prompt.included_files) == 2

    def test_expands_glob_pattern(self, tmp_path):
        """Expands glob pattern includes."""
        # Create source files
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "a.py").write_text("python_a")
        (src_dir / "b.py").write_text("python_b")
        (src_dir / "c.js").write_text("javascript_c")

        # Create prompt file
        prompt_file = tmp_path / "PROMPT.md"
        prompt_file.write_text("# Goal\nCheck these\n@src/*.py")

        prompt = Prompt.from_file(prompt_file, base_dir=tmp_path)
        assert "python_a" in prompt.goal
        assert "python_b" in prompt.goal
        assert "javascript_c" not in prompt.goal

    def test_handles_missing_include_gracefully(self, tmp_path):
        """Shows error message for missing includes."""
        prompt_file = tmp_path / "PROMPT.md"
        prompt_file.write_text("# Goal\n@nonexistent/file.py")

        prompt = Prompt.from_file(prompt_file, base_dir=tmp_path)
        assert "[File not found:" in prompt.goal

    def test_uses_prompt_dir_as_default_base(self, tmp_path):
        """Uses prompt file's directory as default base_dir."""
        subdir = tmp_path / "prompts"
        subdir.mkdir()
        (subdir / "data.txt").write_text("some data")

        prompt_file = subdir / "PROMPT.md"
        prompt_file.write_text("Include: @data.txt")

        prompt = Prompt.from_file(prompt_file)
        assert "some data" in prompt.goal


class TestPromptAutoDetect:
    """Tests for Prompt.auto_detect()."""

    def test_detects_prompt_md(self, tmp_path):
        """Detects PROMPT.md in project root."""
        (tmp_path / "PROMPT.md").write_text("# Goal\nDo something")

        prompt = Prompt.auto_detect(tmp_path)
        assert prompt is not None
        assert "Do something" in prompt.goal

    def test_detects_fireteam_prompt(self, tmp_path):
        """Detects .fireteam/prompt.md."""
        fireteam_dir = tmp_path / ".fireteam"
        fireteam_dir.mkdir()
        (fireteam_dir / "prompt.md").write_text("# Goal\nFireteam prompt")

        prompt = Prompt.auto_detect(tmp_path)
        assert prompt is not None
        assert "Fireteam prompt" in prompt.goal

    def test_detects_lowercase_prompt_md(self, tmp_path):
        """Detects prompt.md."""
        (tmp_path / "prompt.md").write_text("# Goal\nLowercase prompt")

        prompt = Prompt.auto_detect(tmp_path)
        assert prompt is not None
        assert "Lowercase prompt" in prompt.goal

    def test_returns_none_when_no_prompt(self, tmp_path):
        """Returns None when no prompt file found."""
        prompt = Prompt.auto_detect(tmp_path)
        assert prompt is None

    def test_priority_order(self, tmp_path):
        """PROMPT.md takes priority over .fireteam/prompt.md."""
        (tmp_path / "PROMPT.md").write_text("Root prompt")
        fireteam_dir = tmp_path / ".fireteam"
        fireteam_dir.mkdir()
        (fireteam_dir / "prompt.md").write_text("Fireteam prompt")

        prompt = Prompt.auto_detect(tmp_path)
        assert "Root prompt" in prompt.goal


class TestResolvePrompt:
    """Tests for resolve_prompt()."""

    def test_explicit_goal_takes_priority(self, tmp_path):
        """Explicit goal string takes priority."""
        (tmp_path / "PROMPT.md").write_text("File prompt")

        prompt = resolve_prompt(goal="Explicit goal", project_dir=tmp_path)
        assert prompt.goal == "Explicit goal"

    def test_goal_file_when_no_goal(self, tmp_path):
        """Uses goal_file when no explicit goal."""
        goal_file = tmp_path / "my-goal.md"
        goal_file.write_text("# My Goal\nDo this thing")

        prompt = resolve_prompt(goal_file=goal_file, project_dir=tmp_path)
        assert "Do this thing" in prompt.goal

    def test_auto_detect_when_no_goal_or_file(self, tmp_path):
        """Auto-detects when no goal or file provided."""
        (tmp_path / "PROMPT.md").write_text("Auto-detected goal")

        prompt = resolve_prompt(project_dir=tmp_path)
        assert "Auto-detected goal" in prompt.goal

    def test_raises_when_no_source(self, tmp_path):
        """Raises ValueError when no prompt source available."""
        with pytest.raises(ValueError) as exc_info:
            resolve_prompt(project_dir=tmp_path, edit=False)

        assert "No prompt provided" in str(exc_info.value)


class TestGuessLanguage:
    """Tests for _guess_language()."""

    def test_python_files(self):
        """Recognizes Python files."""
        assert _guess_language(Path("test.py")) == "python"

    def test_javascript_files(self):
        """Recognizes JavaScript files."""
        assert _guess_language(Path("app.js")) == "javascript"

    def test_typescript_files(self):
        """Recognizes TypeScript files."""
        assert _guess_language(Path("app.ts")) == "typescript"
        assert _guess_language(Path("component.tsx")) == "tsx"

    def test_rust_files(self):
        """Recognizes Rust files."""
        assert _guess_language(Path("main.rs")) == "rust"

    def test_unknown_extension(self):
        """Returns empty string for unknown extensions."""
        assert _guess_language(Path("file.xyz")) == ""


class TestShouldSkip:
    """Tests for _should_skip()."""

    def test_skips_pycache(self):
        """Skips __pycache__ directories."""
        assert _should_skip(Path("/project/__pycache__/module.pyc"))

    def test_skips_git(self):
        """Skips .git directories."""
        assert _should_skip(Path("/project/.git/config"))

    def test_skips_node_modules(self):
        """Skips node_modules directories."""
        assert _should_skip(Path("/project/node_modules/package/index.js"))

    def test_skips_pyc_files(self):
        """Skips .pyc files."""
        assert _should_skip(Path("/project/module.pyc"))

    def test_allows_normal_files(self):
        """Allows normal source files."""
        assert not _should_skip(Path("/project/src/main.py"))
        assert not _should_skip(Path("/project/src/app.js"))


class TestPromptRender:
    """Tests for Prompt.render()."""

    def test_render_with_file_includes(self, tmp_path):
        """Render shows expanded file content."""
        (tmp_path / "code.py").write_text("print('hello')")
        prompt_file = tmp_path / "PROMPT.md"
        prompt_file.write_text("# Task\nCheck this:\n@code.py")

        prompt = Prompt.from_file(prompt_file, base_dir=tmp_path)
        rendered = prompt.render()

        assert "Check this" in rendered
        assert "print('hello')" in rendered
        assert "```python" in rendered

    def test_str_returns_render(self):
        """__str__ returns render()."""
        prompt = Prompt.from_string("Test goal")
        assert str(prompt) == prompt.render()
