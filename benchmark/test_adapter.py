#!/usr/bin/env python3
"""Test Fireteam adapter locally before running in terminal-bench."""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Check if terminal_bench is installed
try:
    import terminal_bench
    TERMINAL_BENCH_AVAILABLE = True
except ImportError:
    print("Warning: terminal_bench is not installed.")
    print("This is expected for local testing - only basic validation will be performed.")
    print("\nTo install terminal-bench: uv tool install terminal-bench")
    print("Then run with terminal-bench's Python environment.")
    print()
    TERMINAL_BENCH_AVAILABLE = False

# Only import adapter if terminal_bench is available
if TERMINAL_BENCH_AVAILABLE:
    from adapters.fireteam_adapter import FireteamAdapter


def test_adapter():
    """Validate adapter configuration."""
    if not TERMINAL_BENCH_AVAILABLE:
        print("\n" + "=" * 50)
        print("Performing basic file structure validation...")
        print("=" * 50)
        
        # Just validate file structure
        adapter_file = Path(__file__).parent / "adapters" / "fireteam_adapter.py"
        setup_script = Path(__file__).parent / "adapters" / "fireteam-setup.sh"
        pyproject = Path(__file__).parent / "pyproject.toml"
        
        print(f"✓ Adapter file exists: {adapter_file.exists()}")
        assert adapter_file.exists()
        
        print(f"✓ Setup script exists: {setup_script.exists()}")
        assert setup_script.exists()
        
        print(f"✓ Setup script is executable: {os.access(setup_script, os.X_OK)}")
        assert os.access(setup_script, os.X_OK)
        
        print(f"✓ pyproject.toml exists: {pyproject.exists()}")
        assert pyproject.exists()
        
        print("\n" + "=" * 50)
        print("✅ Basic structure validation passed!")
        print("\nTo run full tests, use terminal-bench's Python environment:")
        print("  uv tool run --from terminal-bench python3 test_adapter.py")
        return
    
    # Full tests with terminal_bench available
    # Set required env var for testing
    os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
    
    print("Testing Fireteam Terminal-Bench Adapter")
    print("=" * 50)
    
    # Create adapter instance
    adapter = FireteamAdapter()
    
    # Test 1: Name
    print(f"✓ Agent name: {adapter.name()}")
    assert adapter.name() == "fireteam"
    
    # Test 2: Environment
    env = adapter._env
    print(f"✓ Environment variables:")
    for key, value in env.items():
        masked = value if key != "ANTHROPIC_API_KEY" else "***"
        print(f"    {key}: {masked}")
    assert "ANTHROPIC_API_KEY" in env
    assert env["FIRETEAM_DIR"] == "/app"
    
    # Test 3: Install script
    install_script = adapter._install_agent_script_path
    print(f"✓ Install script: {install_script}")
    assert install_script.name == "fireteam-setup.sh"
    assert install_script.exists(), f"Setup script not found: {install_script}"
    
    # Test 4: Command generation
    instruction = "Create hello.py with print('Hello, World!')"
    commands = adapter._run_agent_commands(instruction)
    print(f"✓ Generated command:")
    print(f"    {commands[0].command}")
    assert len(commands) == 1
    assert "/fireteam/orchestrator.py" in commands[0].command
    assert "--project-dir /app" in commands[0].command
    
    print("\n" + "=" * 50)
    print("✅ All tests passed!")


if __name__ == "__main__":
    test_adapter()

