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
SDK_PERMISSION_MODE = "bypassPermissions"
SDK_SETTING_SOURCES = ["project"]  # Auto-load CLAUDE.md

# Completion validation
COMPLETION_THRESHOLD = 95  # percentage required
VALIDATION_CHECKS_REQUIRED = 3  # consecutive reviews needed

# Logging
LOG_LEVEL = os.getenv("FIRETEAM_LOG_LEVEL", "INFO").upper()
