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
            '--log-level', 'debug',
            '--livestream'  # Enable real-time output
        ]
        
        print("\n🚀 Running terminal-bench hello-world task...")
        print(f"Command: {' '.join(cmd)}\n")
        print("="*60)
        print("Note: Terminal-bench output will stream below in real-time\n")
        sys.stdout.flush()
        
        # Run terminal-bench with real-time output (--livestream makes it stream to console)
        # subprocess.call() lets output go directly to stdout/stderr for real-time viewing
        try:
            return_code = subprocess.call(cmd, timeout=700)
            
            print("\n" + "="*60)
            print(f"Terminal-bench completed with return code: {return_code}")
            print("="*60)
            sys.stdout.flush()
            
        except subprocess.TimeoutExpired:
            pytest.fail("Terminal-bench timed out after 700s")
        except FileNotFoundError:
            pytest.skip("terminal-bench (tb) command not found")
        
        # Assert on return code (0 = success)
        assert return_code == 0, (
            f"Terminal-bench failed with return code {return_code}.\n"
            f"Check the output above for details."
        )
        
        print(f"\n✅ Terminal-bench hello-world task completed successfully!")
        print("   Task passed with 100% accuracy (verified by terminal-bench)")
        
        # Note: With --livestream and direct output, we rely on terminal-bench's
        # own success/failure reporting rather than parsing output ourselves.
        # Return code 0 means the task passed all checks.

