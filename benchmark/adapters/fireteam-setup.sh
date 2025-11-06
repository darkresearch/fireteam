#!/bin/bash
set -e

echo "Installing Fireteam dependencies..."

# Use non-interactive mode to avoid prompts
export DEBIAN_FRONTEND=noninteractive

# Install system dependencies (curl, git, Node.js for Claude Code)
if ! command -v curl &> /dev/null || ! command -v git &> /dev/null || ! command -v node &> /dev/null; then
    echo "Installing system dependencies (this may take 1-2 minutes)..."
    apt-get update -qq
    apt-get install -y -qq curl git nodejs npm sudo
    echo "System dependencies installed"
fi

# Create claude user if it doesn't exist (needed for --dangerously-skip-permissions)
if ! id -u claude &> /dev/null; then
    echo "Creating claude user..."
    useradd -m -s /bin/bash claude
    # Give claude user sudo access without password (now that sudo is installed)
    echo "claude ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers
fi

# Install Claude Code CLI
if ! command -v claude &> /dev/null; then
    echo "Installing Claude Code CLI (this may take 30-60 seconds)..."
    npm install -g @anthropic-ai/claude-code
    echo "Claude Code CLI installed"
fi

# Install uv if not present
if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    echo "uv installed"
fi

# Add uv to PATH (it installs to $HOME/.local/bin)
export PATH="$HOME/.local/bin:$PATH"

# Install Python dependencies using uv
echo "Installing Python dependencies..."
uv pip install --system \
    claude-agent-sdk>=0.1.4 \
    python-dotenv>=1.0.0
echo "Python dependencies installed"

echo "Fireteam installation complete"

