"""
End-to-end test for Fireteam completing a real task.
Spawns actual Fireteam subprocess and validates task completion.
"""

import pytest
import subprocess
import sys
from pathlib import Path

# Add parent to path for helpers
sys.path.insert(0, str(Path(__file__).parent))
from helpers import FireteamTestRunner


@pytest.mark.e2e
@pytest.mark.slow
class TestHelloWorldEndToEnd:
    """End-to-end test of Fireteam completing a simple task."""
    
    def test_hello_world_completion(self, isolated_tmp_dir, isolated_system_dirs):
        """Test Fireteam completes hello world task."""
        project_dir = isolated_tmp_dir / "project"
        project_dir.mkdir()
        
        runner = FireteamTestRunner(project_dir, isolated_system_dirs)
        
        result = runner.run(
            goal="Create a file called hello_world.py that prints 'Hello, World!' when run",
            timeout=300,
            keep_memory=True  # Keep for debugging on failure
        )
        
        # Print result summary for observability
        print(f"\n{result}")
        
        # Use structured assertions with helpful error messages
        assert result.success, (
            f"Fireteam failed to complete task.\n"
            f"Return code: {result.returncode}\n"
            f"Last 30 log lines:\n" + "\n".join(result.logs.splitlines()[-30:])
        )
        
        # Verify file was created
        hello_file = project_dir / "hello_world.py"
        assert hello_file.exists(), (
            f"hello_world.py not found in {project_dir}\n"
            f"Files created: {result.files_created}"
        )
        
        # Verify output
        output = subprocess.run(
            [sys.executable, "hello_world.py"],
            cwd=project_dir,
            capture_output=True,
            text=True
        )
        assert "Hello, World!" in output.stdout, (
            f"Unexpected output: {output.stdout}\n"
            f"stderr: {output.stderr}"
        )
        
        # Verify git history
        assert result.git_commits > 0, "No git commits found"
        
        # Verify reasonable metrics
        assert result.cycle_count >= 1, "No cycles detected"
        assert result.final_completion >= 95, f"Completion only {result.final_completion}%"

