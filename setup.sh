#!/bin/bash
# Setup script for Fireteam

set -e

echo "=========================================="
echo "Fireteam Setup"
echo "=========================================="
echo ""

SYSTEM_DIR="/home/claude/fireteam"
BIN_DIR="/home/claude/.local/bin"

# Create bin directory if it doesn't exist
mkdir -p "$BIN_DIR"

# Add to PATH if not already there
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo "Adding $BIN_DIR to PATH..."
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
    export PATH="$BIN_DIR:$PATH"
fi

# Create symlinks for CLI commands
echo "Creating CLI command symlinks..."
ln -sf "$SYSTEM_DIR/cli/start-agent" "$BIN_DIR/start-agent"
ln -sf "$SYSTEM_DIR/cli/stop-agent" "$BIN_DIR/stop-agent"
ln -sf "$SYSTEM_DIR/cli/agent-progress" "$BIN_DIR/agent-progress"

# Ensure all scripts are executable
chmod +x "$SYSTEM_DIR/cli/"*
chmod +x "$SYSTEM_DIR/src/orchestrator.py"

# Create necessary directories
mkdir -p "$SYSTEM_DIR/logs"
mkdir -p "$SYSTEM_DIR/state"

# Check for Python 3.12+
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3.12+ is required but not found"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
if [[ "$(echo -e "3.12\n$PYTHON_VERSION" | sort -V | head -n1)" != "3.12" ]]; then
    echo "Error: Python 3.12+ is required, but found Python $PYTHON_VERSION"
    exit 1
fi

echo "Python: $(python3 --version)"

# Install uv if not present
if ! command -v uv &> /dev/null; then
    echo "Installing uv package manager..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

# Install Python dependencies using uv
echo "Installing Python dependencies with uv..."
cd "$SYSTEM_DIR"
uv sync --quiet
echo "✓ Python dependencies installed"

# Claude CLI no longer required - using Agent SDK
echo "✓ Using Claude Agent SDK (CLI not required)"

# Check for git
if ! command -v git &> /dev/null; then
    echo "Error: Git is required but not found"
    exit 1
fi

echo "Git: $(git --version)"

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Available commands:"
echo "  start-agent --project-dir <dir> --prompt \"<goal>\""
echo "  stop-agent"
echo "  agent-progress"
echo ""
echo "Example:"
echo "  start-agent --project-dir /home/claude/my-project --prompt \"Build a Python calculator\""
echo ""
echo "Note: You may need to restart your shell or run:"
echo "  source ~/.bashrc"
echo "  (or: export PATH=\"\$HOME/.local/bin:\$PATH\")"
echo ""
