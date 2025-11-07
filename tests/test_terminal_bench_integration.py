"""
Integration test with terminal-bench.
Verifies Fireteam achieves 100% accuracy on terminal-bench hello-world task.
"""

import pytest
import subprocess
import shutil
import sys
from pathlib import Path

# Add parent to path for helpers
sys.path.insert(0, str(Path(__file__).parent))
from helpers import TerminalBenchParser


@pytest.mark.integration
@pytest.mark.slow
class TestTerminalBenchIntegration:
    """Integration test with terminal-bench."""
    
    def test_hello_world_task(self):
        """Test Fireteam achieves 100% on terminal-bench hello-world."""
        
        # Check if tb is installed
        if not shutil.which('tb'):
            pytest.skip("terminal-bench (tb) not installed")
        
        # Run terminal-bench via subprocess
        cmd = [
            'tb', 'run',
            '--agent-import-path', 'benchmark.adapters.fireteam_adapter:FireteamAdapter',
            '--dataset', 'terminal-bench-core==0.1.1',
            '--task-id', 'hello-world',
            '--global-agent-timeout-sec', '600',
            '--log-level', 'info'
        ]
        
        print("\n🚀 Running terminal-bench hello-world task...")
        print(f"Command: {' '.join(cmd)}\n")
        
        # Capture output
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=700
            )
        except subprocess.TimeoutExpired:
            pytest.fail("Terminal-bench timed out after 700s")
        except FileNotFoundError:
            pytest.skip("terminal-bench (tb) command not found")
        
        # Parse terminal-bench output
        tb_result = TerminalBenchParser.parse_output(result.stdout, 'hello-world')
        
        # Print structured results
        print(tb_result)
        
        # Check return code
        assert result.returncode == 0, (
            f"Terminal-bench failed with return code {result.returncode}.\n"
            f"Result: {tb_result}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
        
        # Assert structured results
        assert tb_result.passed, (
            f"Task did not pass.\n"
            f"{tb_result}\n"
            f"Full output:\n{result.stdout}"
        )
        
        # Verify 100% accuracy
        assert tb_result.accuracy == 1.0, (
            f"Expected 100% accuracy, got {tb_result.accuracy * 100:.1f}%\n"
            f"{tb_result}"
        )
        
        print(f"\n✅ Terminal-bench hello-world task completed successfully!")
        print(f"   Accuracy: {tb_result.accuracy * 100:.1f}%")

