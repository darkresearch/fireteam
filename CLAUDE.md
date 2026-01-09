# Claude AI Assistant Rules for Fireteam

## Python Version Requirements
- **REQUIRED**: Use Python 3.12 or higher for all operations
- **NEVER** use Python 3.9, 3.10, or 3.11
- When checking Python version, ensure it's 3.12+: `python3.12 --version`

## Dependency Management
- **REQUIRED**: Use `uv` for all Python dependency management
- **NEVER** use `pip`, `pip3`, or standard pip commands
- `uv` is a fast, modern Python package installer and resolver

### Common Operations
```bash
# Install all dependencies (creates venv and uses uv.lock)
uv sync

# Install with dev dependencies
uv sync --extra dev

# Add a new dependency
uv add <package-name>

# Add a dev dependency
uv add --dev <package-name>

# Update lockfile after changing pyproject.toml
uv lock

# Run a command in the virtual environment
uv run python script.py
uv run pytest
```

## Why These Rules?
- Python 3.12+: Required by `claude-agent-sdk>=0.1.4` and provides better performance
- `uv`: 10-100x faster than pip, better dependency resolution, production-ready
