"""
Configuration settings for the Claude agent system.
"""

import os

# System paths
SYSTEM_DIR = "/home/claude/claude-agent-system"
STATE_DIR = os.path.join(SYSTEM_DIR, "state")
LOGS_DIR = os.path.join(SYSTEM_DIR, "logs")
CLI_DIR = os.path.join(SYSTEM_DIR, "cli")

# Claude CLI configuration
CLAUDE_CLI = "claude"  # Assumes claude is in PATH
DANGEROUSLY_SKIP_PERMISSIONS = "--dangerously-skip-permissions"

# Agent configuration
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds

# Completion thresholds
COMPLETION_THRESHOLD = 95  # percentage
VALIDATION_CHECKS_REQUIRED = 3  # consecutive checks needed

# Git configuration
GIT_USER_NAME = os.environ.get("GIT_USER_NAME", "Claude Agent System")
GIT_USER_EMAIL = os.environ.get("GIT_USER_EMAIL", "agent@claude.system")

# Logging
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
