#!/bin/bash
set -e

# Install Python 3.12+ and pip
if command -v apk &> /dev/null; then
    # Alpine Linux
    apk add --no-cache python3 py3-pip git
elif command -v apt-get &> /dev/null; then
    # Debian/Ubuntu
    apt-get update
    apt-get install -y python3 python3-pip python3-venv git curl
else
    echo "Unsupported distribution" >&2
    exit 1
fi

# Install uv for fast package management
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

# Install fireteam from GitHub (or local if mounted)
if [ -d "/fireteam" ]; then
    cd /fireteam
    uv pip install --system -e .
else
    uv pip install --system git+https://github.com/darkresearch/fireteam.git
fi

echo "Fireteam installed successfully"