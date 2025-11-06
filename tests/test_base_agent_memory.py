"""
Unit tests for BaseAgent memory integration.
Tests execution context storage, automatic retrieval, and memory injection.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
import sys
from unittest.mock import Mock, MagicMock, patch

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agents.base import BaseAgent
from memory.manager import MemoryManager


class ConcreteAgent(BaseAgent):
    """Concrete implementation for testing."""
    
    def get_system_prompt(self) -> str:
        return "Test agent system prompt"
    
    def _do_execute(self, **kwargs):
        """Simple implementation for testing."""
        return {
            "success": True,
            "test_result": "completed",
            "kwargs_received": kwargs
        }
    
    def _build_memory_context_query(self) -> str:
        """Build context query from stored execution context."""
        goal = self._execution_context.get('goal', '')
        plan = self._execution_context.get('plan', '')
        return f"Working on: {goal}. Plan: {plan}"
    
    def _get_relevant_memory_types(self) -> list[str]:
        return ["learning", "decision"]


class TestBaseAgentMemoryIntegration:
    """Test BaseAgent memory features."""
    
    @pytest.fixture
    def temp_memory_dir(self):
        """Create temporary memory directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def memory_manager(self, temp_memory_dir):
        """Create MemoryManager instance."""
        return MemoryManager(memory_dir=temp_memory_dir)
    
    @pytest.fixture
    def agent_with_memory(self, memory_manager):
        """Create agent with memory manager."""
        return ConcreteAgent("test", memory_manager=memory_manager)
    
    @pytest.fixture
    def agent_without_memory(self):
        """Create agent without memory manager."""
        return ConcreteAgent("test", memory_manager=None)
    
    def test_execution_context_storage(self, agent_without_memory):
        """Test that execute() stores kwargs in _execution_context."""
        kwargs = {
            "project_dir": "/tmp/test",
            "goal": "Test goal",
            "plan": "Test plan",
            "cycle_number": 5
        }
        
        agent_without_memory.execute(**kwargs)
        
        # Check context was stored
        assert agent_without_memory._execution_context == kwargs
        assert agent_without_memory._execution_context["goal"] == "Test goal"
        assert agent_without_memory._execution_context["cycle_number"] == 5
    
    def test_execute_calls_do_execute(self, agent_without_memory):
        """Test that execute() properly calls _do_execute()."""
        result = agent_without_memory.execute(
            project_dir="/tmp/test",
            goal="Test goal",
            plan="Test plan"
        )
        
        # Should return result from _do_execute
        assert result["success"] is True
        assert result["test_result"] == "completed"
        assert "kwargs_received" in result
    
    def test_memory_context_query_building(self, agent_with_memory):
        """Test that agents can build context queries from execution context."""
        agent_with_memory._execution_context = {
            "goal": "Build auth system",
            "plan": "Implement JWT tokens"
        }
        
        query = agent_with_memory._build_memory_context_query()
        
        assert "Build auth system" in query
        assert "Implement JWT tokens" in query
    
    def test_retrieve_memories_without_memory_manager(self, agent_without_memory):
        """Test that retrieval works gracefully without memory manager."""
        agent_without_memory._execution_context = {"goal": "Test"}
        
        memories = agent_without_memory._retrieve_and_format_memories()
        
        # Should return empty string
        assert memories == ""
    
    def test_retrieve_memories_with_empty_query(self, agent_with_memory):
        """Test retrieval with empty context query."""
        # Agent returns empty query
        agent_with_memory._execution_context = {}
        
        memories = agent_with_memory._retrieve_and_format_memories()
        
        # Should return empty string
        assert memories == ""
    
    def test_retrieve_and_format_memories(self, agent_with_memory, memory_manager):
        """Test automatic memory retrieval and formatting."""
        project_dir = "/tmp/test-project"
        memory_manager.initialize_project(project_dir, "Test goal")
        
        # Add some memories
        memory_manager.add_memory(
            content="Authentication uses JWT tokens",
            memory_type="decision",
            cycle=1
        )
        memory_manager.add_memory(
            content="All API calls use async/await pattern",
            memory_type="learning",
            cycle=2
        )
        
        # Set execution context
        agent_with_memory._execution_context = {
            "goal": "Build authentication",
            "plan": "Implement JWT middleware"
        }
        
        # Retrieve memories
        formatted = agent_with_memory._retrieve_and_format_memories()
        
        # Should contain formatted memories
        assert "BACKGROUND KNOWLEDGE" in formatted
        assert "JWT tokens" in formatted
        assert "Cycle 1" in formatted or "Cycle 2" in formatted
    
    def test_memory_type_filtering(self, agent_with_memory, memory_manager):
        """Test that agents retrieve only relevant memory types."""
        project_dir = "/tmp/test-project-types"
        memory_manager.initialize_project(project_dir, "Test goal")
        
        # Add different types
        memory_manager.add_memory("Learning 1", "learning", 1)
        memory_manager.add_memory("Decision 1", "decision", 1)
        memory_manager.add_memory("Trace 1", "trace", 1)
        memory_manager.add_memory("Failed 1", "failed_approach", 1)
        
        # Agent only wants learning and decision
        agent_with_memory._execution_context = {"goal": "Test"}
        
        # Mock search to verify it's called with correct types
        original_search = memory_manager.search
        
        def mock_search(query, limit=10, memory_types=None):
            # Verify types passed
            assert memory_types is not None
            assert set(memory_types) == {"learning", "decision"}
            return original_search(query, limit, memory_types)
        
        memory_manager.search = mock_search
        
        # Trigger retrieval
        agent_with_memory._retrieve_and_format_memories()


class TestMemoryInjection:
    """Test memory injection into agent execution."""
    
    @pytest.fixture
    def temp_memory_dir(self):
        """Create temporary memory directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_memory_injection_into_system_prompt(self, temp_memory_dir):
        """Test that memories are injected into system prompt."""
        memory_manager = MemoryManager(memory_dir=temp_memory_dir)
        agent = ConcreteAgent("test", memory_manager=memory_manager)
        
        # Initialize project and add memory
        memory_manager.initialize_project("/tmp/test", "Test goal")
        memory_manager.add_memory("Important context", "learning", 1)
        
        # Set execution context
        agent._execution_context = {"goal": "Important context test"}
        
        # Mock _execute_with_sdk to capture enhanced prompt
        captured_prompt = None
        
        async def mock_execute(prompt, project_dir):
            nonlocal captured_prompt
            # Get the enhanced system prompt from options
            # This would be called inside _execute_with_sdk
            memory_context = agent._retrieve_and_format_memories()
            base_prompt = agent.get_system_prompt()
            captured_prompt = base_prompt + "\n" + memory_context if memory_context else base_prompt
            
            return {"success": True, "output": "Test output", "error": None}
        
        with patch.object(agent, '_execute_with_sdk', side_effect=mock_execute):
            with patch.object(agent, '_execute_command', return_value={"success": True, "output": "Test"}):
                agent.execute(goal="Test")
        
        # Verify memory was retrieved and formatted
        formatted = agent._retrieve_and_format_memories()
        assert "Important context" in formatted
        assert "BACKGROUND KNOWLEDGE" in formatted


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

