"""
Unit tests for agent classes.
Tests BaseAgent, PlannerAgent, ExecutorAgent, and ReviewerAgent functionality.
"""

import pytest
import tempfile
import shutil
import logging
import sys
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agents.base import BaseAgent
from agents.planner import PlannerAgent
from agents.executor import ExecutorAgent
from agents.reviewer import ReviewerAgent


class TestBaseAgent:
    """Test BaseAgent functionality."""
    
    @pytest.fixture
    def logger(self):
        """Create test logger."""
        return logging.getLogger("test")
    
    @pytest.fixture
    def mock_memory_manager(self):
        """Create mock memory manager."""
        memory = Mock()
        memory.search = Mock(return_value=[])
        return memory
    
    def test_initialization(self, logger):
        """Test BaseAgent initialization."""
        # Need to create a concrete subclass
        class TestAgent(BaseAgent):
            def get_system_prompt(self):
                return "Test prompt"
            
            def _do_execute(self, **kwargs):
                return {"success": True}
        
        agent = TestAgent("test", logger)
        
        assert agent.agent_type == "test"
        assert agent.logger == logger
        assert agent.max_retries > 0
        assert agent.retry_delay > 0
        assert agent.timeout > 0

    def test_get_system_prompt_not_implemented(self, logger):
        """Test that BaseAgent requires get_system_prompt implementation."""
        agent = BaseAgent("test", logger)
        
        with pytest.raises(NotImplementedError):
            agent.get_system_prompt()

    def test_do_execute_not_implemented(self, logger):
        """Test that BaseAgent requires _do_execute implementation."""
        agent = BaseAgent("test", logger)
        
        with pytest.raises(NotImplementedError):
            agent._do_execute()

    def test_execution_context_storage(self, logger):
        """Test that execute() stores execution context."""
        class TestAgent(BaseAgent):
            def get_system_prompt(self):
                return "Test prompt"
            
            def _do_execute(self, **kwargs):
                # Check that context is available
                assert self._execution_context == kwargs
                return {"success": True}
        
        agent = TestAgent("test", logger)
        agent.execute(project_dir="/tmp/test", goal="Test goal")
        
        # Context should be stored
        assert agent._execution_context["project_dir"] == "/tmp/test"
        assert agent._execution_context["goal"] == "Test goal"

    def test_memory_integration(self, logger, mock_memory_manager):
        """Test memory manager integration."""
        class TestAgent(BaseAgent):
            def get_system_prompt(self):
                return "Test prompt"
            
            def _do_execute(self, **kwargs):
                return {"success": True}
        
        agent = TestAgent("test", logger, memory_manager=mock_memory_manager)
        
        assert agent.memory == mock_memory_manager

    def test_retrieve_memories_without_manager(self, logger):
        """Test memory retrieval when no manager is set."""
        class TestAgent(BaseAgent):
            def get_system_prompt(self):
                return "Test prompt"
            
            def _build_memory_context_query(self):
                return "test query"
            
            def _do_execute(self, **kwargs):
                return {"success": True}
        
        agent = TestAgent("test", logger, memory_manager=None)
        
        # Should return empty string gracefully
        result = agent._retrieve_and_format_memories()
        assert result == ""

    def test_retrieve_memories_with_results(self, logger, mock_memory_manager):
        """Test memory retrieval with results."""
        # Mock memories
        mock_memory_manager.search.return_value = [
            {"content": "Learning 1", "type": "learning", "cycle": 1},
            {"content": "Decision 1", "type": "decision", "cycle": 2}
        ]
        
        class TestAgent(BaseAgent):
            def get_system_prompt(self):
                return "Test prompt"
            
            def _build_memory_context_query(self):
                return "test query"
            
            def _get_relevant_memory_types(self):
                return ["learning", "decision"]
            
            def _do_execute(self, **kwargs):
                return {"success": True}
        
        agent = TestAgent("test", logger, memory_manager=mock_memory_manager)
        
        # Retrieve memories
        result = agent._retrieve_and_format_memories()
        
        # Should have formatted memories
        assert result != ""
        assert "Learning 1" in result
        assert "Decision 1" in result
        assert "BACKGROUND KNOWLEDGE" in result

    def test_timeout_configuration(self, logger):
        """Test that agent timeout is configured correctly."""
        import config
        
        # Planner should have planner timeout
        planner = PlannerAgent(logger)
        assert planner.timeout == config.AGENT_TIMEOUTS["planner"]
        
        # Executor should have executor timeout
        executor = ExecutorAgent(logger)
        assert executor.timeout == config.AGENT_TIMEOUTS["executor"]
        
        # Reviewer should have reviewer timeout
        reviewer = ReviewerAgent(logger)
        assert reviewer.timeout == config.AGENT_TIMEOUTS["reviewer"]


class TestPlannerAgent:
    """Test PlannerAgent functionality."""
    
    @pytest.fixture
    def logger(self):
        """Create test logger."""
        return logging.getLogger("test-planner")
    
    @pytest.fixture
    def planner(self, logger):
        """Create PlannerAgent instance."""
        return PlannerAgent(logger)
    
    def test_initialization(self, planner):
        """Test PlannerAgent initialization."""
        assert planner.agent_type == "planner"
        assert planner.logger is not None

    def test_get_system_prompt(self, planner):
        """Test that planner has proper system prompt."""
        prompt = planner.get_system_prompt()
        
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        
        # Should mention key responsibilities
        assert "plan" in prompt.lower() or "planner" in prompt.lower()
        assert "task" in prompt.lower()

    def test_build_initial_plan_prompt(self, planner):
        """Test initial plan prompt building."""
        goal = "Build a web application"
        
        prompt = planner._build_initial_plan_prompt(goal)
        
        assert isinstance(prompt, str)
        assert goal in prompt
        assert "plan" in prompt.lower()

    def test_build_update_plan_prompt(self, planner):
        """Test plan update prompt building."""
        goal = "Build a web application"
        previous_plan = "Step 1: Create files"
        execution_result = "Created files successfully"
        review = "Good progress, 50% complete"
        cycle = 2
        
        prompt = planner._build_update_plan_prompt(
            goal, previous_plan, execution_result, review, cycle
        )
        
        assert isinstance(prompt, str)
        assert goal in prompt
        assert str(cycle) in prompt

    def test_extract_plan(self, planner):
        """Test plan extraction from output."""
        output = """
# Project Plan

## Tasks
1. Setup environment
2. Write code
3. Test

This is the plan.
"""
        
        plan = planner._extract_plan(output)
        
        assert isinstance(plan, str)
        assert "Tasks" in plan
        assert "Setup environment" in plan

    def test_relevant_memory_types(self, planner):
        """Test that planner requests relevant memory types."""
        types = planner._get_relevant_memory_types()
        
        assert isinstance(types, list)
        # Planner should care about decisions and failed approaches
        assert "decision" in types
        assert "failed_approach" in types

    def test_build_memory_context_query(self, planner):
        """Test memory context query building."""
        # Set execution context
        planner._execution_context = {
            "goal": "Build app",
            "last_review": "Good progress"
        }
        
        query = planner._build_memory_context_query()
        
        assert isinstance(query, str)
        assert "Build app" in query

    @patch.object(PlannerAgent, '_execute_command')
    def test_do_execute_success(self, mock_execute, planner):
        """Test successful plan execution."""
        # Mock successful execution
        mock_execute.return_value = {
            "success": True,
            "output": "# Plan\n\n1. Task 1\n2. Task 2"
        }
        
        result = planner._do_execute(
            project_dir="/tmp/test",
            goal="Test goal",
            cycle_number=0
        )
        
        assert result["success"] is True
        assert "plan" in result
        assert "Task 1" in result["plan"]

    @patch.object(PlannerAgent, '_execute_command')
    def test_do_execute_failure(self, mock_execute, planner):
        """Test failed plan execution."""
        # Mock failed execution
        mock_execute.return_value = {
            "success": False,
            "error": "Test error"
        }
        
        result = planner._do_execute(
            project_dir="/tmp/test",
            goal="Test goal",
            cycle_number=0
        )
        
        assert result["success"] is False
        assert "error" in result


class TestExecutorAgent:
    """Test ExecutorAgent functionality."""
    
    @pytest.fixture
    def logger(self):
        """Create test logger."""
        return logging.getLogger("test-executor")
    
    @pytest.fixture
    def executor(self, logger):
        """Create ExecutorAgent instance."""
        return ExecutorAgent(logger)
    
    def test_initialization(self, executor):
        """Test ExecutorAgent initialization."""
        assert executor.agent_type == "executor"
        assert executor.logger is not None

    def test_get_system_prompt(self, executor):
        """Test that executor has proper system prompt."""
        prompt = executor.get_system_prompt()
        
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        
        # Should mention execution responsibilities
        assert "execut" in prompt.lower()
        assert "code" in prompt.lower() or "implement" in prompt.lower()

    def test_build_execution_prompt(self, executor):
        """Test execution prompt building."""
        goal = "Build a web application"
        plan = "1. Create files\n2. Write code"
        cycle = 1
        
        prompt = executor._build_execution_prompt(goal, plan, cycle)
        
        assert isinstance(prompt, str)
        assert goal in prompt
        assert plan in prompt
        assert str(cycle) in prompt

    def test_relevant_memory_types(self, executor):
        """Test that executor requests relevant memory types."""
        types = executor._get_relevant_memory_types()
        
        assert isinstance(types, list)
        # Executor should care about failed approaches and traces
        assert "failed_approach" in types
        assert "trace" in types

    def test_build_memory_context_query(self, executor):
        """Test memory context query building."""
        # Set execution context
        executor._execution_context = {
            "plan": "Create files",
            "goal": "Build app"
        }
        
        query = executor._build_memory_context_query()
        
        assert isinstance(query, str)
        assert "Create files" in query

    @patch.object(ExecutorAgent, '_execute_command')
    def test_do_execute_success(self, mock_execute, executor):
        """Test successful execution."""
        # Mock successful execution
        mock_execute.return_value = {
            "success": True,
            "output": "Created files and wrote code successfully"
        }
        
        result = executor._do_execute(
            project_dir="/tmp/test",
            goal="Test goal",
            plan="Create files",
            cycle_number=1
        )
        
        assert result["success"] is True
        assert "execution_result" in result
        assert "successfully" in result["execution_result"]

    @patch.object(ExecutorAgent, '_execute_command')
    def test_do_execute_failure(self, mock_execute, executor):
        """Test failed execution."""
        # Mock failed execution
        mock_execute.return_value = {
            "success": False,
            "error": "Test error"
        }
        
        result = executor._do_execute(
            project_dir="/tmp/test",
            goal="Test goal",
            plan="Create files",
            cycle_number=1
        )
        
        assert result["success"] is False
        assert "error" in result


class TestReviewerAgent:
    """Test ReviewerAgent functionality."""
    
    @pytest.fixture
    def logger(self):
        """Create test logger."""
        return logging.getLogger("test-reviewer")
    
    @pytest.fixture
    def reviewer(self, logger):
        """Create ReviewerAgent instance."""
        return ReviewerAgent(logger)
    
    def test_initialization(self, reviewer):
        """Test ReviewerAgent initialization."""
        assert reviewer.agent_type == "reviewer"
        assert reviewer.logger is not None

    def test_get_system_prompt(self, reviewer):
        """Test that reviewer has proper system prompt."""
        prompt = reviewer.get_system_prompt()
        
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        
        # Should mention review responsibilities
        assert "review" in prompt.lower()
        assert "completion" in prompt.lower() or "progress" in prompt.lower()

    def test_build_review_prompt(self, reviewer):
        """Test review prompt building."""
        goal = "Build a web application"
        plan = "1. Create files\n2. Write code"
        execution_result = "Created files"
        cycle = 1
        
        prompt = reviewer._build_review_prompt(
            goal, plan, execution_result, cycle, is_validation=False
        )
        
        assert isinstance(prompt, str)
        assert goal in prompt
        assert plan in prompt
        assert execution_result in prompt

    def test_build_review_prompt_validation_mode(self, reviewer):
        """Test review prompt in validation mode."""
        prompt = reviewer._build_review_prompt(
            "Test goal", "Test plan", "Test result", 5, is_validation=True
        )
        
        # Should include validation instructions
        assert "VALIDATION" in prompt
        assert "critical" in prompt.lower() or "thorough" in prompt.lower()

    def test_extract_completion_percentage_exact_format(self, reviewer):
        """Test completion percentage extraction with exact format."""
        output = """
Review Summary:
Project is progressing well.

COMPLETION: 75%

Next steps: Continue implementation.
"""
        
        percentage = reviewer._extract_completion_percentage(output)
        assert percentage == 75

    def test_extract_completion_percentage_case_insensitive(self, reviewer):
        """Test completion percentage extraction is case insensitive."""
        output = "completion: 80%"
        percentage = reviewer._extract_completion_percentage(output)
        assert percentage == 80

    def test_extract_completion_percentage_fallback(self, reviewer):
        """Test completion percentage extraction fallback."""
        output = "The project is about 60% complete overall."
        percentage = reviewer._extract_completion_percentage(output)
        assert percentage == 60

    def test_extract_completion_percentage_none(self, reviewer):
        """Test completion percentage extraction when not found."""
        output = "Review: Looking good!"
        percentage = reviewer._extract_completion_percentage(output)
        assert percentage == 0

    def test_extract_learnings(self, reviewer):
        """Test learning extraction from review."""
        review = """
Review summary:
Progress is good.

LEARNING[pattern]: All API calls use async/await
LEARNING[decision]: Using SQLite for simpler deployment
LEARNING[failed_approach]: Tried bcrypt but had Node 18 issues
LEARNING[code_location]: Auth middleware in src/auth/jwt.js

That's all.
"""
        
        learnings = reviewer._extract_learnings(review)
        
        assert len(learnings) == 4
        
        # Check each learning
        types = [l["type"] for l in learnings]
        assert "pattern" in types
        assert "decision" in types
        assert "failed_approach" in types
        assert "code_location" in types
        
        # Check content
        contents = [l["content"] for l in learnings]
        assert any("async/await" in c for c in contents)
        assert any("SQLite" in c for c in contents)

    def test_extract_learnings_no_learnings(self, reviewer):
        """Test learning extraction with no learnings."""
        review = "Just a simple review with no structured learnings."
        
        learnings = reviewer._extract_learnings(review)
        
        assert len(learnings) == 0

    def test_relevant_memory_types(self, reviewer):
        """Test that reviewer requests relevant memory types."""
        types = reviewer._get_relevant_memory_types()
        
        assert isinstance(types, list)
        # Reviewer should care about patterns, decisions, learnings
        assert "learning" in types
        assert "decision" in types
        assert "pattern" in types

    def test_build_memory_context_query(self, reviewer):
        """Test memory context query building."""
        # Set execution context
        reviewer._execution_context = {
            "execution_result": "Files created",
            "plan": "Create files"
        }
        
        query = reviewer._build_memory_context_query()
        
        assert isinstance(query, str)
        assert "Files created" in query

    @patch.object(ReviewerAgent, '_execute_command')
    def test_do_execute_success(self, mock_execute, reviewer):
        """Test successful review."""
        # Mock successful review
        mock_execute.return_value = {
            "success": True,
            "output": "COMPLETION: 85%\nGood progress!\nLEARNING[pattern]: Using MVC"
        }
        
        result = reviewer._do_execute(
            project_dir="/tmp/test",
            goal="Test goal",
            plan="Test plan",
            execution_result="Test result",
            cycle_number=1
        )
        
        assert result["success"] is True
        assert "review" in result
        assert "completion_percentage" in result
        assert result["completion_percentage"] == 85
        assert "learnings" in result
        assert len(result["learnings"]) == 1

    @patch.object(ReviewerAgent, '_execute_command')
    def test_do_execute_failure(self, mock_execute, reviewer):
        """Test failed review."""
        # Mock failed review
        mock_execute.return_value = {
            "success": False,
            "error": "Test error"
        }
        
        result = reviewer._do_execute(
            project_dir="/tmp/test",
            goal="Test goal",
            plan="Test plan",
            execution_result="Test result",
            cycle_number=1
        )
        
        assert result["success"] is False
        assert "error" in result
        assert result["completion_percentage"] == 0
        assert len(result["learnings"]) == 0

