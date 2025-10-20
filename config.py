"""
Configuration settings for Fireteam.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    load_dotenv(env_file)

# System paths
SYSTEM_DIR = "/home/claude/fireteam"
STATE_DIR = os.path.join(SYSTEM_DIR, "state")
LOGS_DIR = os.path.join(SYSTEM_DIR, "logs")
CLI_DIR = os.path.join(SYSTEM_DIR, "cli")

# Claude Agent SDK configuration
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    raise ValueError("ANTHROPIC_API_KEY environment variable must be set")

# SDK options
SDK_ALLOWED_TOOLS = ["Read", "Write", "Bash", "Edit", "Grep", "Glob"]
SDK_PERMISSION_MODE = "bypassPermissions"  # Autonomous operation
SDK_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

# Agent configuration
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds

# Agent timeouts (in seconds)
AGENT_TIMEOUTS = {
    "planner": 600,      # 10 minutes (complex planning, analysis)
    "reviewer": 600,     # 10 minutes (code review + test runs)
    "executor": 1800     # 30 minutes (complex builds, installations, test suites)
}

# Completion thresholds
COMPLETION_THRESHOLD = 95  # percentage
VALIDATION_CHECKS_REQUIRED = 3  # consecutive checks needed

# Git configuration
GIT_USER_NAME = os.environ.get("GIT_USER_NAME", "fireteam")
GIT_USER_EMAIL = os.environ.get("GIT_USER_EMAIL", "fireteam@darkresearch.ai")

# Logging
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Sudo password for system operations (optional)
# Set in .env file: SUDO_PASSWORD=your_password_here
SUDO_PASSWORD = os.getenv("SUDO_PASSWORD", None)

def has_sudo_access():
    """Check if sudo password is available."""
    return SUDO_PASSWORD is not None
