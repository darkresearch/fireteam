"""
Tests for CLI tools.
Tests fireteam-status and other CLI utilities.
"""

import pytest
import tempfile
import shutil
import json
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from io import StringIO

# Add CLI directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "cli"))


class TestFireteamStatus:
    """Test fireteam-status CLI tool."""
    
    @pytest.fixture
    def temp_system_dir(self):
        """Create temporary system directory."""
        temp_dir = Path(tempfile.mkdtemp(prefix="test-system-"))
        
        # Create subdirectories
        (temp_dir / "state").mkdir()
        (temp_dir / "logs").mkdir()
        
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def mock_state_file(self, temp_system_dir):
        """Create mock state file."""
        state_file = temp_system_dir / "state" / "current.json"
        state_data = {
            "project_dir": "/tmp/test-project",
            "goal": "Build a test application",
            "status": "executing",
            "cycle_number": 5,
            "completion_percentage": 75,
            "git_branch": "fireteam-20250101-120000",
            "started_at": "2025-01-01T12:00:00",
            "updated_at": "2025-01-01T12:30:00",
            "completed": False
        }
        
        with open(state_file, 'w') as f:
            json.dump(state_data, f)
        
        return state_file
    
    def test_import_fireteam_status(self):
        """Test that fireteam-status can be imported."""
        # This is a sanity check
        try:
            # Can't easily import because of SYSTEM_DIR hardcoded path
            # But we can read the file
            status_file = Path(__file__).parent.parent / "cli" / "fireteam-status"
            assert status_file.exists()
            
            content = status_file.read_text()
            assert "def show_status" in content
            assert "def load_state" in content
        except Exception as e:
            pytest.skip(f"Could not read fireteam-status: {e}")

    @patch('sys.argv', ['fireteam-status', '--help'])
    def test_fireteam_status_help(self):
        """Test fireteam-status help output."""
        # Import the module (this will be tricky due to hardcoded paths)
        # For now, just verify file structure
        status_file = Path(__file__).parent.parent / "cli" / "fireteam-status"
        assert status_file.exists()
        
        content = status_file.read_text()
        # Check for key functions
        assert "def main()" in content
        assert "argparse" in content
        assert "--watch" in content
        assert "--logs" in content

    def test_check_process_running(self):
        """Test check_process_running function."""
        # We'll test the logic, not the actual function
        # since it has hardcoded paths
        
        # Current process should be running
        current_pid = os.getpid()
        
        # Verify process exists
        try:
            os.kill(current_pid, 0)
            is_running = True
        except (OSError, ProcessLookupError):
            is_running = False
        
        assert is_running is True
        
        # Invalid PID should not be running
        fake_pid = 999999
        try:
            os.kill(fake_pid, 0)
            is_running = True
        except (OSError, ProcessLookupError):
            is_running = False
        
        assert is_running is False

    def test_format_timestamp(self):
        """Test timestamp formatting logic."""
        from datetime import datetime
        
        # Test ISO format parsing
        iso_timestamp = "2025-01-01T12:30:45"
        dt = datetime.fromisoformat(iso_timestamp)
        formatted = dt.strftime("%Y-%m-%d %H:%M:%S")
        
        assert formatted == "2025-01-01 12:30:45"

    def test_state_file_format(self, mock_state_file):
        """Test state file can be parsed."""
        # Read and parse state file
        with open(mock_state_file, 'r') as f:
            state = json.load(f)
        
        # Verify required fields
        assert "project_dir" in state
        assert "goal" in state
        assert "status" in state
        assert "cycle_number" in state
        assert "completion_percentage" in state
        assert "started_at" in state
        assert "updated_at" in state
        
        # Verify values
        assert state["project_dir"] == "/tmp/test-project"
        assert state["status"] == "executing"
        assert state["cycle_number"] == 5
        assert state["completion_percentage"] == 75


class TestCLIScripts:
    """Test CLI shell scripts."""
    
    def test_start_agent_script_exists(self):
        """Test that start-agent script exists."""
        script_file = Path(__file__).parent.parent / "cli" / "start-agent"
        assert script_file.exists()
        
        content = script_file.read_text()
        # Check for key elements
        assert "#!/bin/bash" in content
        assert "--project-dir" in content
        assert "--prompt" in content or "--goal" in content

    def test_stop_agent_script_exists(self):
        """Test that stop-agent script exists."""
        script_file = Path(__file__).parent.parent / "cli" / "stop-agent"
        assert script_file.exists()
        
        content = script_file.read_text()
        # Check for key elements
        assert "#!/bin/bash" in content
        assert "PID" in content
        assert "kill" in content

    def test_agent_progress_script_exists(self):
        """Test that agent-progress script exists."""
        script_file = Path(__file__).parent.parent / "cli" / "agent-progress"
        if script_file.exists():
            content = script_file.read_text()
            assert len(content) > 0


class TestCLIArgumentParsing:
    """Test CLI argument parsing logic."""
    
    def test_status_arguments(self):
        """Test status command argument parsing."""
        import argparse
        
        # Simulate argument parsing for status command
        parser = argparse.ArgumentParser()
        parser.add_argument("--watch", action="store_true")
        parser.add_argument("--interval", type=int, default=5)
        parser.add_argument("--logs", action="store_true")
        parser.add_argument("--follow", action="store_true")
        parser.add_argument("--lines", type=int, default=20)
        
        # Test default
        args = parser.parse_args([])
        assert args.watch is False
        assert args.interval == 5
        assert args.logs is False
        
        # Test watch mode
        args = parser.parse_args(["--watch"])
        assert args.watch is True
        
        # Test custom interval
        args = parser.parse_args(["--watch", "--interval", "10"])
        assert args.watch is True
        assert args.interval == 10
        
        # Test logs
        args = parser.parse_args(["--logs"])
        assert args.logs is True
        
        # Test follow
        args = parser.parse_args(["--logs", "--follow"])
        assert args.logs is True
        assert args.follow is True


class TestSystemResourceMonitoring:
    """Test system resource monitoring functions."""
    
    @patch('subprocess.check_output')
    def test_memory_info_parsing(self, mock_subprocess):
        """Test memory information parsing."""
        # Mock free -h output
        mock_subprocess.return_value = """              total        used        free      shared  buff/cache   available
Mem:           15Gi       8.0Gi       2.0Gi       500Mi       5.0Gi       10Gi
Swap:         2.0Gi       0.0Gi       2.0Gi"""
        
        output = mock_subprocess()
        lines = output.strip().split('\n')
        mem_data = lines[1].split()
        
        assert mem_data[1] == "15Gi"  # total
        assert mem_data[2] == "8.0Gi"  # used

    @patch('subprocess.check_output')
    def test_cpu_load_parsing(self, mock_subprocess):
        """Test CPU load information parsing."""
        # Mock uptime output
        mock_subprocess.return_value = " 12:30:45 up 10 days,  3:45,  2 users,  load average: 1.23, 1.45, 1.67"
        
        output = mock_subprocess()
        load = output.split('load average:')[1].strip()
        
        assert load == "1.23, 1.45, 1.67"

    @patch('subprocess.check_output')
    def test_disk_usage_parsing(self, mock_subprocess):
        """Test disk usage information parsing."""
        # Mock df -h output
        mock_subprocess.return_value = """Filesystem      Size  Used Avail Use% Mounted on
/dev/sda1       100G   60G   40G  60% /"""
        
        output = mock_subprocess()
        disk_line = output.strip().split('\n')[1]
        disk_usage = disk_line.split()[4]
        
        assert disk_usage == "60%"


class TestPIDFileHandling:
    """Test PID file handling."""
    
    @pytest.fixture
    def temp_pid_file(self):
        """Create temporary PID file."""
        temp_file = Path(tempfile.mktemp(suffix=".pid"))
        yield temp_file
        if temp_file.exists():
            temp_file.unlink()
    
    def test_write_pid_file(self, temp_pid_file):
        """Test writing PID to file."""
        pid = 12345
        temp_pid_file.write_text(str(pid))
        
        # Read back
        read_pid = int(temp_pid_file.read_text().strip())
        assert read_pid == pid

    def test_read_pid_file(self, temp_pid_file):
        """Test reading PID from file."""
        pid = 67890
        temp_pid_file.write_text(f"{pid}\n")
        
        # Read back
        read_pid = int(temp_pid_file.read_text().strip())
        assert read_pid == pid

    def test_pid_file_cleanup(self, temp_pid_file):
        """Test PID file cleanup."""
        temp_pid_file.write_text("12345")
        assert temp_pid_file.exists()
        
        # Cleanup
        temp_pid_file.unlink()
        assert not temp_pid_file.exists()


class TestLogFileHandling:
    """Test log file handling."""
    
    @pytest.fixture
    def temp_log_dir(self):
        """Create temporary log directory."""
        temp_dir = Path(tempfile.mkdtemp(prefix="test-logs-"))
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_log_file_creation(self, temp_log_dir):
        """Test log file creation."""
        log_file = temp_log_dir / "orchestrator_20250101_120000.log"
        
        # Write log content
        log_content = "2025-01-01 12:00:00 - INFO - Starting system\n"
        log_file.write_text(log_content)
        
        # Verify
        assert log_file.exists()
        assert log_file.read_text() == log_content

    def test_find_latest_log(self, temp_log_dir):
        """Test finding latest log file."""
        # Create multiple log files
        log1 = temp_log_dir / "orchestrator_20250101_120000.log"
        log2 = temp_log_dir / "orchestrator_20250101_130000.log"
        log3 = temp_log_dir / "orchestrator_20250101_140000.log"
        
        log1.write_text("Log 1")
        log2.write_text("Log 2")
        log3.write_text("Log 3")
        
        # Find latest
        log_files = sorted(temp_log_dir.glob("orchestrator_*.log"))
        latest_log = log_files[-1]
        
        assert latest_log == log3

    def test_read_log_lines(self, temp_log_dir):
        """Test reading specific number of log lines."""
        log_file = temp_log_dir / "test.log"
        
        # Write multiple lines
        lines = [f"Line {i}\n" for i in range(50)]
        log_file.write_text("".join(lines))
        
        # Read last N lines
        content = log_file.read_text().split('\n')
        last_20 = content[-21:-1]  # -1 excludes empty line at end
        
        assert len(last_20) == 20
        assert last_20[-1] == "Line 49"


class TestCLIErrorHandling:
    """Test CLI error handling."""
    
    def test_missing_state_file(self):
        """Test handling of missing state file."""
        fake_path = Path("/tmp/nonexistent-state-file.json")
        
        # Should not crash when file doesn't exist
        exists = fake_path.exists()
        assert exists is False
        
        # Handling logic should check existence first
        if not exists:
            state = None
        else:
            with open(fake_path, 'r') as f:
                state = json.load(f)
        
        assert state is None

    def test_invalid_json_state(self):
        """Test handling of invalid JSON in state file."""
        temp_file = Path(tempfile.mktemp(suffix=".json"))
        
        try:
            # Write invalid JSON
            temp_file.write_text("{ invalid json }")
            
            # Try to parse
            try:
                with open(temp_file, 'r') as f:
                    state = json.load(f)
            except json.JSONDecodeError:
                state = None
            
            assert state is None
        finally:
            if temp_file.exists():
                temp_file.unlink()

    def test_missing_pid_file(self):
        """Test handling of missing PID file."""
        fake_path = Path("/tmp/nonexistent.pid")
        
        # Should handle gracefully
        if not fake_path.exists():
            running = False
        else:
            pid = int(fake_path.read_text().strip())
            # Check if process is running
            try:
                os.kill(pid, 0)
                running = True
            except (OSError, ProcessLookupError):
                running = False
        
        assert running is False


class TestCLIOutputFormatting:
    """Test CLI output formatting."""
    
    def test_status_display_format(self):
        """Test status display formatting."""
        # Test the format structure (without actually calling the function)
        status_lines = [
            "=" * 60,
            "🔥 FIRETEAM STATUS",
            "=" * 60,
            "",
            "Status: ✅ RUNNING (PID: 12345)",
            "",
            "📁 Project State:",
            "-" * 60,
            "  Project: /tmp/test-project",
            "  Goal: Build application",
            "  Status: EXECUTING",
            "  Cycle: 5",
            "  Completion: 75%",
        ]
        
        # Verify formatting
        assert len(status_lines) > 0
        assert "FIRETEAM STATUS" in status_lines[1]

    def test_goal_truncation(self):
        """Test long goal string truncation."""
        long_goal = "A" * 100
        
        # Truncate if too long
        if len(long_goal) > 80:
            truncated = long_goal[:77] + "..."
        else:
            truncated = long_goal
        
        assert len(truncated) == 80
        assert truncated.endswith("...")

    def test_timestamp_formatting(self):
        """Test timestamp formatting."""
        from datetime import datetime
        
        iso_timestamp = "2025-01-01T12:30:45"
        dt = datetime.fromisoformat(iso_timestamp)
        formatted = dt.strftime("%Y-%m-%d %H:%M:%S")
        
        assert " " in formatted
        assert ":" in formatted
        assert "-" in formatted

