#!/bin/bash
#
# Fireteam installation script for Terminal Bench Docker containers
#
# This script installs Fireteam with proper user permissions:
# - Creates fireteam-user (NOT root, but with passwordless sudo)
# - Installs system dependencies
# - Installs Claude CLI
# - Installs Fireteam
# - Verifies installation
#
# Claude Code security requirement: Cannot run as root, but needs sudo for installs
# Solution: fireteam-user with NOPASSWD sudo access

set -e  # Exit on error
set -u  # Exit on undefined variable

echo "================================================"
echo "Installing Fireteam in Terminal Bench container"
echo "================================================"

# Configuration
FIRETEAM_USER="claude"
FIRETEAM_HOME="/home/${FIRETEAM_USER}/fireteam"
FIRETEAM_REPO="${FIRETEAM_REPO:-https://github.com/darkresearch/fireteam.git}"
FIRETEAM_VERSION="${FIRETEAM_VERSION:-main}"

# ===== STEP 1: Create claude user with sudo permissions =====
echo ""
echo "[1/7] Creating ${FIRETEAM_USER} user with sudo permissions..."

if ! id -u "${FIRETEAM_USER}" > /dev/null 2>&1; then
    # Create user with home directory
    useradd -m -s /bin/bash "${FIRETEAM_USER}"
    echo "✓ Created user: ${FIRETEAM_USER}"

    # Add to sudo group
    usermod -aG sudo "${FIRETEAM_USER}"

    # Configure passwordless sudo (required for package installation)
    echo "${FIRETEAM_USER} ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers
    echo "✓ Granted sudo permissions to ${FIRETEAM_USER}"
else
    echo "✓ User ${FIRETEAM_USER} already exists"
fi

# ===== STEP 2: Install Claude Code credentials (OAuth session) =====
echo ""
echo "[2/7] Installing Claude Code credentials..."

if [ -n "${CLAUDE_CREDENTIALS_TAR_GZ_BASE64:-}" ]; then
    # Decode and extract credentials for claude user
    echo "${CLAUDE_CREDENTIALS_TAR_GZ_BASE64}" | base64 -d | \
        tar -xzf - -C /home/${FIRETEAM_USER}/
    chown -R ${FIRETEAM_USER}:${FIRETEAM_USER} /home/${FIRETEAM_USER}/.claude
    echo "✓ Claude Code OAuth credentials installed"
else
    echo "✓ Authentication will be provided via ANTHROPIC_API_KEY at runtime"
fi

# ===== STEP 3: Install system dependencies =====
echo ""
echo "[3/7] Installing system dependencies..."

apt-get update -qq > /dev/null 2>&1
apt-get install -y -qq \
    python3 \
    python3-venv \
    python3-pip \
    git \
    curl \
    wget \
    build-essential \
    2>&1 | grep -v "^debconf:" || true

# Verify curl is installed
if ! command -v curl &> /dev/null; then
    echo "✗ Error: curl failed to install"
    exit 1
fi

echo "✓ System dependencies installed"

# Install UV (modern Python package manager) - not strictly required
curl -LsSf https://astral.sh/uv/install.sh | sh > /dev/null 2>&1 || {
    echo "⚠ Warning: UV installation failed (not critical)"
}

# ===== STEP 4: Install Python dependencies =====
echo ""
echo "[4/7] Installing Python dependencies..."

# Install pip if needed
if ! command -v pip3 &> /dev/null; then
    apt-get install -y -qq python3-pip > /dev/null 2>&1
fi

echo "✓ Python pip available"

# Install Claude Agent SDK (required for Fireteam)
# Do this as claude user to avoid permission issues
echo "  Installing Claude Agent SDK..."
su - "${FIRETEAM_USER}" -c "pip3 install --user --quiet claude-agent-sdk>=0.1.4 python-dotenv>=1.0.0" && {
    echo "✓ Claude Agent SDK installed"
} || {
    echo "⚠ Warning: Claude Agent SDK installation failed"
}

# ===== STEP 5: Install Fireteam as claude user =====
echo ""
echo "[5/7] Installing Fireteam..."

# Check if we have base64-encoded Fireteam source from host
if [ -n "${FIRETEAM_SOURCE_TAR_GZ_BASE64:-}" ]; then
    echo "  Extracting Fireteam from base64-encoded source..."
    # Decode and extract as claude user
    su - "${FIRETEAM_USER}" << EOF
set -e
echo "${FIRETEAM_SOURCE_TAR_GZ_BASE64}" | base64 -d | tar -xzf - -C \${HOME}
EOF
    echo "  ✓ Using local Fireteam with SDK changes"
else
    # Fallback: Clone from repository
    echo "  No local source provided, cloning from repository..."
    su - "${FIRETEAM_USER}" << EOF
set -e

if [ ! -d "\${HOME}/fireteam" ]; then
    echo "  Cloning Fireteam from ${FIRETEAM_REPO}..."
    git clone ${FIRETEAM_REPO} \${HOME}/fireteam
else
    echo "  Fireteam directory already exists"
fi

cd \${HOME}/fireteam
git fetch origin
git checkout ${FIRETEAM_VERSION}
EOF
    echo "  ✓ Using Fireteam version: ${FIRETEAM_VERSION} from GitHub"
fi

# Run Fireteam setup as claude user
su - "${FIRETEAM_USER}" << 'EOF'
set -e
cd \${HOME}/fireteam

# Run Fireteam setup
echo "  Running Fireteam setup..."
bash setup.sh

# Verify CLI tools installed
if [ -x "\${HOME}/.local/bin/start-agent" ]; then
    echo "  ✓ Fireteam CLI tools installed"
else
    echo "  ⚠ Warning: Fireteam CLI tools may not be installed correctly"
fi
EOF

echo "✓ Fireteam installed in ${FIRETEAM_HOME}"

# ===== STEP 6: Configure environment =====
echo ""
echo "[6/7] Configuring environment..."

# Ensure .local/bin in PATH for fireteam-user
su - "${FIRETEAM_USER}" << 'EOF'
if ! grep -q ".local/bin" ~/.bashrc 2>/dev/null; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
fi
EOF

echo "✓ Environment configured"

# ===== STEP 7: Verify installation =====
echo ""
echo "[7/7] Verifying installation..."

# Test orchestrator is accessible
su - "${FIRETEAM_USER}" -c "python3 ~/fireteam/orchestrator.py --help > /dev/null 2>&1" && {
    echo "✓ Fireteam orchestrator verified"
} || {
    echo "✗ Error: Fireteam orchestrator not working"
    exit 1
}

# Test CLI tools
su - "${FIRETEAM_USER}" -c "command -v start-agent > /dev/null 2>&1" && {
    echo "✓ Fireteam CLI tools verified"
} || {
    echo "⚠ Warning: Fireteam CLI tools not in PATH"
}

# ===== Installation Complete =====
echo ""
echo "================================================"
echo "✓ Fireteam installation complete!"
echo "================================================"
echo ""
echo "Installation summary:"
echo "  User: ${FIRETEAM_USER}"
echo "  Home: /home/${FIRETEAM_USER}"
echo "  Fireteam: ${FIRETEAM_HOME}"
echo "  Version: ${FIRETEAM_VERSION}"
echo "  Sudo: Enabled (passwordless)"
echo ""
echo "Fireteam will run as ${FIRETEAM_USER} user with sudo access."
echo "================================================"
