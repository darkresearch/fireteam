"""
Configuration settings for Fireteam.

Minimal configuration - most behavior comes from SDK defaults and CLAUDE.md.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_file = Path(__file__).parent.parent / ".env"
if env_file.exists():
    load_dotenv(env_file)

# Claude Agent SDK configuration
SDK_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-5-20251101")
SDK_ALLOWED_TOOLS = ["Read", "Write", "Bash", "Edit", "Grep", "Glob"]
# Note: bypassPermissions fails as root user, use "default" in containers
SDK_PERMISSION_MODE = os.getenv("FIRETEAM_PERMISSION_MODE", "bypassPermissions")
SDK_SETTING_SOURCES = ["project"]  # Auto-load CLAUDE.md

# Completion validation
COMPLETION_THRESHOLD = 95  # percentage required
VALIDATION_CHECKS_REQUIRED = 3  # consecutive reviews needed

# Loop configuration
# None = infinite iterations (default), set via FIRETEAM_MAX_ITERATIONS env var
_max_iter = os.getenv("FIRETEAM_MAX_ITERATIONS")
MAX_ITERATIONS: int | None = int(_max_iter) if _max_iter else None

# Logging
LOG_LEVEL = os.getenv("FIRETEAM_LOG_LEVEL", "INFO").upper()
