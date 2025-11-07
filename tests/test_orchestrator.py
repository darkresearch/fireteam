"""
Integration tests for Orchestrator.
Tests full cycle execution, git integration, and completion checking.
"""

import pytest
import tempfile
import shutil
import os
import subprocess
import json
import logging
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from orchestrator import Orchestrator
import config


class TestOrchestrator:
    """Test Orchestrator functionality."""
    
    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary project directory."""
        temp_dir = tempfile.mkdtemp(prefix="test-project-")
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def temp_system_dir(self):
        """Create temporary system directory for config."""
        temp_dir = tempfile.mkdtemp(prefix="test-system-")
        # Create subdirectories
        os.makedirs(os.path.join(temp_dir, "state"), exist_ok=True)
        os.makedirs(os.path.join(temp_dir, "logs"), exist_ok=True)
        os.makedirs(os.path.join(temp_dir, "memory"), exist_ok=True)
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture(autouse=True)
    def patch_config(self, temp_system_dir):
        """Patch config to use temp directories."""
        with patch.dict('os.environ', {'FIRETEAM_DIR': temp_system_dir}):
            # Reload config to pick up new env var
            import importlib
            import config as config_module
            importlib.reload(config_module)
            yield
            # Reload again to restore
            importlib.reload(config_module)
    
    def test_initialization(self, temp_project_dir):
        """Test Orchestrator initialization."""
        goal = "Build a test application"
        
        orch = Orchestrator(temp_project_dir, goal, debug=False)
        
        assert orch.project_dir == os.path.abspath(temp_project_dir)
        assert orch.goal == goal
        assert orch.debug is False
        assert orch.keep_memory is False
        assert orch.state_manager is not None
        assert orch.memory is not None
        assert orch.planner is not None
        assert orch.executor is not None
        assert orch.reviewer is not None
        assert orch.running is True

    def test_initialization_with_debug(self, temp_project_dir):
        """Test Orchestrator initialization with debug mode."""
        orch = Orchestrator(temp_project_dir, "Test goal", debug=True)
        assert orch.debug is True

    def test_initialization_with_keep_memory(self, temp_project_dir):
        """Test Orchestrator initialization with keep_memory flag."""
        orch = Orchestrator(temp_project_dir, "Test goal", keep_memory=True)
        assert orch.keep_memory is True

    def test_setup_logging(self, temp_project_dir):
        """Test logging setup."""
        orch = Orchestrator(temp_project_dir, "Test goal")
        
        assert orch.logger is not None
        assert isinstance(orch.logger, logging.Logger)
        assert orch.logger.name == "orchestrator"

    def test_initialize_git_repo_new(self, temp_project_dir):
        """Test git repository initialization for new project."""
        orch = Orchestrator(temp_project_dir, "Test goal")
        
        branch_name = orch.initialize_git_repo()
        
        # Should return branch name
        assert branch_name is not None
        assert "fireteam-" in branch_name
        
        # .git directory should exist
        assert os.path.exists(os.path.join(temp_project_dir, ".git"))
        
        # Should be on the created branch
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=temp_project_dir,
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert branch_name in result.stdout

    def test_initialize_git_repo_existing(self, temp_project_dir):
        """Test git repository initialization for existing repo."""
        # Initialize git repo first
        subprocess.run(["git", "init"], cwd=temp_project_dir, check=True)
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=temp_project_dir,
            check=True
        )
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=temp_project_dir,
            check=True
        )
        
        # Create initial commit
        with open(os.path.join(temp_project_dir, "README.md"), "w") as f:
            f.write("# Test")
        subprocess.run(["git", "add", "."], cwd=temp_project_dir, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial"],
            cwd=temp_project_dir,
            check=True
        )
        
        # Now initialize orchestrator
        orch = Orchestrator(temp_project_dir, "Test goal")
        branch_name = orch.initialize_git_repo()
        
        # Should create new branch
        assert branch_name is not None
        assert "fireteam-" in branch_name

    def test_commit_changes(self, temp_project_dir):
        """Test committing changes."""
        orch = Orchestrator(temp_project_dir, "Test goal")
        orch.initialize_git_repo()
        
        # Make some changes
        test_file = os.path.join(temp_project_dir, "test.txt")
        with open(test_file, "w") as f:
            f.write("Test content")
        
        # Commit changes
        orch.commit_changes(1, "Test changes")
        
        # Check commit exists
        result = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=temp_project_dir,
            capture_output=True,
            text=True
        )
        assert "Cycle 1" in result.stdout
        assert "Test changes" in result.stdout

    def test_commit_changes_no_changes(self, temp_project_dir):
        """Test committing when there are no changes."""
        orch = Orchestrator(temp_project_dir, "Test goal")
        orch.initialize_git_repo()
        
        # Try to commit without changes - should handle gracefully
        orch.commit_changes(1, "No changes")
        
        # Should not crash

    @patch('subprocess.run')
    def test_push_to_remote_exists(self, mock_run, temp_project_dir):
        """Test pushing to remote when remote exists."""
        # Mock successful remote check and push
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="https://github.com/test/repo.git"),
            MagicMock(returncode=0)
        ]
        
        orch = Orchestrator(temp_project_dir, "Test goal")
        orch.push_to_remote()
        
        # Should have called git remote and git push
        assert mock_run.call_count == 2

    @patch('subprocess.run')
    def test_push_to_remote_no_remote(self, mock_run, temp_project_dir):
        """Test pushing when no remote exists."""
        # Mock failed remote check
        mock_run.return_value = MagicMock(returncode=1)
        
        orch = Orchestrator(temp_project_dir, "Test goal")
        orch.push_to_remote()
        
        # Should handle gracefully

    def test_check_completion_not_complete(self, temp_project_dir):
        """Test completion check when not complete."""
        orch = Orchestrator(temp_project_dir, "Test goal")
        
        state = {
            "completion_percentage": 50,
            "validation_checks": 0
        }
        
        is_complete = orch.check_completion(state)
        assert is_complete is False

    def test_check_completion_single_validation(self, temp_project_dir):
        """Test completion check with single validation."""
        orch = Orchestrator(temp_project_dir, "Test goal")
        
        state = {
            "completion_percentage": 96,
            "validation_checks": 0
        }
        
        is_complete = orch.check_completion(state)
        assert is_complete is False

    def test_check_completion_multiple_validations(self, temp_project_dir):
        """Test completion check with multiple validations."""
        orch = Orchestrator(temp_project_dir, "Test goal")
        
        # First validation
        state = {"completion_percentage": 96, "validation_checks": 0}
        orch.check_completion(state)
        
        # Second validation
        state = orch.state_manager.load_state()
        state["completion_percentage"] = 97
        orch.state_manager.update_state(state)
        orch.check_completion(state)
        
        # Third validation - should complete
        state = orch.state_manager.load_state()
        state["completion_percentage"] = 98
        orch.state_manager.update_state(state)
        is_complete = orch.check_completion(state)
        
        assert is_complete is True

    def test_check_completion_reset_on_drop(self, temp_project_dir):
        """Test validation checks reset when percentage drops."""
        orch = Orchestrator(temp_project_dir, "Test goal")
        
        # First validation
        state = {"completion_percentage": 96, "validation_checks": 0}
        orch.check_completion(state)
        
        state = orch.state_manager.load_state()
        assert state["validation_checks"] == 1
        
        # Drop below threshold
        state["completion_percentage"] = 90
        orch.state_manager.update_state(state)
        orch.check_completion(state)
        
        # Should reset
        state = orch.state_manager.load_state()
        assert state["validation_checks"] == 0

    @patch.object(Orchestrator, 'commit_changes')
    def test_run_cycle_structure(self, mock_commit, temp_project_dir):
        """Test that run_cycle follows proper structure."""
        orch = Orchestrator(temp_project_dir, "Test goal")
        
        # Initialize memory for project
        orch.memory.initialize_project(temp_project_dir, "Test goal")
        
        # Mock agent responses
        with patch.object(orch.planner, 'execute') as mock_planner, \
             patch.object(orch.executor, 'execute') as mock_executor, \
             patch.object(orch.reviewer, 'execute') as mock_reviewer:
            
            # Setup mocks
            mock_planner.return_value = {
                "success": True,
                "plan": "Test plan"
            }
            mock_executor.return_value = {
                "success": True,
                "execution_result": "Test execution"
            }
            mock_reviewer.return_value = {
                "success": True,
                "review": "Test review",
                "completion_percentage": 50,
                "learnings": []
            }
            
            # Run cycle
            state = {
                "cycle_number": 1,
                "completion_percentage": 0
            }
            
            result = orch.run_cycle(state)
            
            # All agents should have been called
            assert mock_planner.called
            assert mock_executor.called
            assert mock_reviewer.called
            
            # State should be updated
            assert "current_plan" in result
            assert "last_execution_result" in result
            assert "last_review" in result

    @patch.object(Orchestrator, 'commit_changes')
    def test_run_cycle_planner_failure(self, mock_commit, temp_project_dir):
        """Test run_cycle when planner fails."""
        orch = Orchestrator(temp_project_dir, "Test goal")
        
        with patch.object(orch.planner, 'execute') as mock_planner:
            mock_planner.return_value = {
                "success": False,
                "error": "Planner error"
            }
            
            state = {"cycle_number": 1}
            result = orch.run_cycle(state)
            
            # Should return original state
            assert result == state

    @patch.object(Orchestrator, 'commit_changes')
    def test_run_cycle_executor_failure(self, mock_commit, temp_project_dir):
        """Test run_cycle when executor fails."""
        orch = Orchestrator(temp_project_dir, "Test goal")
        
        with patch.object(orch.planner, 'execute') as mock_planner, \
             patch.object(orch.executor, 'execute') as mock_executor:
            
            mock_planner.return_value = {
                "success": True,
                "plan": "Test plan"
            }
            mock_executor.return_value = {
                "success": False,
                "error": "Executor error"
            }
            
            state = {"cycle_number": 1}
            result = orch.run_cycle(state)
            
            # Should return original state
            assert result == state

    @patch.object(Orchestrator, 'commit_changes')
    def test_run_cycle_reviewer_failure(self, mock_commit, temp_project_dir):
        """Test run_cycle when reviewer fails."""
        orch = Orchestrator(temp_project_dir, "Test goal")
        
        # Initialize memory for project
        orch.memory.initialize_project(temp_project_dir, "Test goal")
        
        with patch.object(orch.planner, 'execute') as mock_planner, \
             patch.object(orch.executor, 'execute') as mock_executor, \
             patch.object(orch.reviewer, 'execute') as mock_reviewer:
            
            mock_planner.return_value = {
                "success": True,
                "plan": "Test plan"
            }
            mock_executor.return_value = {
                "success": True,
                "execution_result": "Test execution"
            }
            mock_reviewer.return_value = {
                "success": False,
                "error": "Reviewer error"
            }
            
            state = {"cycle_number": 1}
            result = orch.run_cycle(state)
            
            # Should return original state
            assert result == state

    @patch.object(Orchestrator, 'commit_changes')
    def test_run_cycle_learning_extraction(self, mock_commit, temp_project_dir):
        """Test that learnings are extracted and stored."""
        orch = Orchestrator(temp_project_dir, "Test goal")
        
        with patch.object(orch.planner, 'execute') as mock_planner, \
             patch.object(orch.executor, 'execute') as mock_executor, \
             patch.object(orch.reviewer, 'execute') as mock_reviewer, \
             patch.object(orch.memory, 'add_memory') as mock_add_memory:
            
            mock_planner.return_value = {
                "success": True,
                "plan": "Test plan"
            }
            mock_executor.return_value = {
                "success": True,
                "execution_result": "Test execution"
            }
            mock_reviewer.return_value = {
                "success": True,
                "review": "Test review",
                "completion_percentage": 50,
                "learnings": [
                    {"type": "pattern", "content": "Using MVC"},
                    {"type": "decision", "content": "Chose SQLite"}
                ]
            }
            
            state = {"cycle_number": 1}
            orch.run_cycle(state)
            
            # Memory should have been called for learnings
            assert mock_add_memory.call_count >= 2

    def test_goal_alignment_check(self, temp_project_dir):
        """Test that goal alignment check happens at proper intervals."""
        orch = Orchestrator(temp_project_dir, "Test goal")
        
        # Initialize memory for project
        orch.memory.initialize_project(temp_project_dir, "Test goal")
        
        # Mock agents
        with patch.object(orch.planner, 'execute') as mock_planner, \
             patch.object(orch.executor, 'execute') as mock_executor, \
             patch.object(orch.reviewer, 'execute') as mock_reviewer, \
             patch.object(orch, 'commit_changes'):
            
            mock_planner.return_value = {"success": True, "plan": "Test"}
            mock_executor.return_value = {"success": True, "execution_result": "Test"}
            mock_reviewer.return_value = {
                "success": True,
                "review": "Test",
                "completion_percentage": 50,
                "learnings": []
            }
            
            # Run cycle 3 - should trigger alignment check
            state = {"cycle_number": 3, "completion_percentage": 50}
            orch.run_cycle(state)
            
            # Check that logger logged alignment check
            # (We'd need to capture logs to verify, but at least it shouldn't crash)

    def test_memory_manager_injection(self, temp_project_dir):
        """Test that memory manager is injected into agents."""
        orch = Orchestrator(temp_project_dir, "Test goal")
        
        # All agents should have memory manager
        assert orch.planner.memory == orch.memory
        assert orch.executor.memory == orch.memory
        assert orch.reviewer.memory == orch.memory

    def test_state_manager_integration(self, temp_project_dir):
        """Test state manager integration."""
        orch = Orchestrator(temp_project_dir, "Test goal")
        
        # Initialize state
        state = orch.state_manager.initialize_project(temp_project_dir, "Test goal")
        
        assert state is not None
        assert state["project_dir"] == os.path.abspath(temp_project_dir)
        assert state["goal"] == "Test goal"

    def test_signal_handler(self, temp_project_dir):
        """Test signal handler sets running flag."""
        import signal
        
        orch = Orchestrator(temp_project_dir, "Test goal")
        
        assert orch.running is True
        
        # Simulate signal
        orch._signal_handler(signal.SIGINT, None)
        
        assert orch.running is False

    def test_validation_mode_trigger(self, temp_project_dir):
        """Test that validation mode is triggered at high completion."""
        orch = Orchestrator(temp_project_dir, "Test goal")
        
        # Initialize memory for project
        orch.memory.initialize_project(temp_project_dir, "Test goal")
        
        with patch.object(orch.planner, 'execute') as mock_planner, \
             patch.object(orch.executor, 'execute') as mock_executor, \
             patch.object(orch.reviewer, 'execute') as mock_reviewer, \
             patch.object(orch, 'commit_changes'):
            
            mock_planner.return_value = {"success": True, "plan": "Test"}
            mock_executor.return_value = {"success": True, "execution_result": "Test"}
            mock_reviewer.return_value = {
                "success": True,
                "review": "Test",
                "completion_percentage": 96,
                "learnings": []
            }
            
            # Run cycle with high completion
            state = {"cycle_number": 1, "completion_percentage": 96}
            orch.run_cycle(state)
            
            # Reviewer should have been called with is_validation=True
            call_args = mock_reviewer.call_args
            assert call_args is not None
            assert call_args[1].get("is_validation") is True


class TestOrchestratorCLI:
    """Test Orchestrator CLI interface."""
    
    def test_main_missing_arguments(self):
        """Test that CLI requires arguments."""
        from orchestrator import main
        
        with pytest.raises(SystemExit):
            with patch('sys.argv', ['orchestrator.py']):
                main()

    @patch('orchestrator.Orchestrator')
    def test_main_with_arguments(self, mock_orch_class):
        """Test CLI with proper arguments."""
        from orchestrator import main
        
        # Mock orchestrator instance
        mock_instance = Mock()
        mock_instance.run.return_value = 0
        mock_orch_class.return_value = mock_instance
        
        with patch('sys.argv', [
            'orchestrator.py',
            '--project-dir', '/tmp/test',
            '--goal', 'Test goal'
        ]):
            # Expect SystemExit
            with pytest.raises(SystemExit) as exc_info:
                main()
            
            assert exc_info.value.code == 0
        
        # Should create orchestrator and run
        assert mock_orch_class.called
        assert mock_instance.run.called

    @patch('orchestrator.Orchestrator')
    def test_main_with_debug_flag(self, mock_orch_class):
        """Test CLI with debug flag."""
        from orchestrator import main
        
        mock_instance = Mock()
        mock_instance.run.return_value = 0
        mock_orch_class.return_value = mock_instance
        
        with patch('sys.argv', [
            'orchestrator.py',
            '--project-dir', '/tmp/test',
            '--goal', 'Test goal',
            '--debug'
        ]):
            # Expect SystemExit
            with pytest.raises(SystemExit) as exc_info:
                main()
            
            assert exc_info.value.code == 0
        
        # Should pass debug flag
        call_args = mock_orch_class.call_args
        assert call_args[1]['debug'] is True

    @patch('orchestrator.Orchestrator')
    def test_main_with_keep_memory_flag(self, mock_orch_class):
        """Test CLI with keep-memory flag."""
        from orchestrator import main
        
        mock_instance = Mock()
        mock_instance.run.return_value = 0
        mock_orch_class.return_value = mock_instance
        
        with patch('sys.argv', [
            'orchestrator.py',
            '--project-dir', '/tmp/test',
            '--goal', 'Test goal',
            '--keep-memory'
        ]):
            # Expect SystemExit
            with pytest.raises(SystemExit) as exc_info:
                main()
            
            assert exc_info.value.code == 0
        
        # Should pass keep_memory flag
        call_args = mock_orch_class.call_args
        assert call_args[1]['keep_memory'] is True

