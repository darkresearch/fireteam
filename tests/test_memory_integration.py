"""
Integration tests for memory system with full orchestrator cycle.
Tests memory recording, retrieval, and cleanup in realistic scenarios.
"""

import pytest
import tempfile
import shutil
import os
from pathlib import Path
import sys
from unittest.mock import Mock, patch, MagicMock

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from memory.manager import MemoryManager
from state.manager import StateManager
from agents import PlannerAgent, ExecutorAgent, ReviewerAgent
from test_base_agent_memory import ConcreteAgent


@pytest.mark.slow
class TestMemoryIntegration:
    """Test memory integration across full cycles (uses heavy Qwen3 model)."""
    
    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories for testing."""
        memory_dir = tempfile.mkdtemp()
        state_dir = tempfile.mkdtemp()
        project_dir = tempfile.mkdtemp()
        
        yield {
            "memory": memory_dir,
            "state": state_dir,
            "project": project_dir
        }
        
        shutil.rmtree(memory_dir, ignore_errors=True)
        shutil.rmtree(state_dir, ignore_errors=True)
        shutil.rmtree(project_dir, ignore_errors=True)
    
    @pytest.fixture
    def memory_manager(self, temp_dirs):
        """Create MemoryManager instance."""
        return MemoryManager(memory_dir=temp_dirs["memory"])
    
    @pytest.fixture
    def agents_with_memory(self, memory_manager):
        """Create agents with memory manager."""
        return {
            "planner": PlannerAgent(memory_manager=memory_manager),
            "executor": ExecutorAgent(memory_manager=memory_manager),
            "reviewer": ReviewerAgent(memory_manager=memory_manager)
        }
    
    def test_memory_flows_through_cycle(self, memory_manager, agents_with_memory, temp_dirs):
        """Test that memory is recorded and retrieved across a cycle."""
        project_dir = temp_dirs["project"]
        goal = "Build a simple calculator"
        
        # Initialize memory for project
        memory_manager.initialize_project(project_dir, goal)
        
        # Cycle 1: Add some learnings manually
        memory_manager.add_memory(
            content="User wants command-line interface",
            memory_type="decision",
            cycle=0
        )
        memory_manager.add_memory(
            content="Python 3.12+ required",
            memory_type="learning",
            cycle=0
        )
        
        # Simulate Cycle 2: Planner should retrieve these memories
        planner = agents_with_memory["planner"]
        
        # Set execution context (what planner.execute would do)
        planner._execution_context = {
            "goal": goal,
            "last_review": "Need to implement basic operations"
        }
        
        # Retrieve memories
        memories_text = planner._retrieve_and_format_memories()
        
        # Should contain previous learnings
        assert "command-line interface" in memories_text or "Python 3.12" in memories_text
        assert "BACKGROUND KNOWLEDGE" in memories_text
    
    def test_reviewer_extracts_learnings(self, agents_with_memory):
        """Test that reviewer can extract learnings from its output."""
        reviewer = agents_with_memory["reviewer"]
        
        # Sample review text with learnings
        review_text = """
        Project is progressing well. COMPLETION: 50%
        
        LEARNING[pattern]: All database operations use async/await
        LEARNING[decision]: Chose SQLite for simplicity
        LEARNING[failed_approach]: Tried Redis but had connection issues
        LEARNING[code_location]: Main calculator logic in src/calc.py
        
        Overall the code looks good but needs more testing.
        """
        
        learnings = reviewer._extract_learnings(review_text)
        
        # Should extract all 4 learnings
        assert len(learnings) == 4
        
        # Verify types
        types = [l["type"] for l in learnings]
        assert "pattern" in types
        assert "decision" in types
        assert "failed_approach" in types
        assert "code_location" in types
        
        # Verify content
        contents = [l["content"] for l in learnings]
        assert any("async/await" in c for c in contents)
        assert any("SQLite" in c for c in contents)
    
    def test_different_agents_retrieve_different_memory_types(self, memory_manager, agents_with_memory, temp_dirs):
        """Test that different agents retrieve different types of memories."""
        project_dir = temp_dirs["project"]
        memory_manager.initialize_project(project_dir, "Test goal")
        
        # Add various memory types
        memory_manager.add_memory("Pattern: Use async", "pattern", 1)
        memory_manager.add_memory("Decision: Use SQLite", "decision", 1)
        memory_manager.add_memory("Failed: Tried Redis", "failed_approach", 1)
        memory_manager.add_memory("Trace: npm install failed", "trace", 1)
        memory_manager.add_memory("Location: auth in src/auth.js", "code_location", 1)
        
        # Planner retrieves decisions, failed approaches, learnings
        planner = agents_with_memory["planner"]
        assert set(planner._get_relevant_memory_types()) == {"decision", "failed_approach", "learning"}
        
        # Executor retrieves failed approaches, traces, code locations
        executor = agents_with_memory["executor"]
        assert set(executor._get_relevant_memory_types()) == {"failed_approach", "trace", "code_location"}
        
        # Reviewer retrieves learnings, decisions, patterns
        reviewer = agents_with_memory["reviewer"]
        assert set(reviewer._get_relevant_memory_types()) == {"learning", "decision", "pattern"}
    
    def test_memory_persists_across_cycles(self, memory_manager, temp_dirs):
        """Test that memories persist and accumulate across cycles."""
        project_dir = temp_dirs["project"]
        memory_manager.initialize_project(project_dir, "Test goal")
        
        # Cycle 1: Add memories
        memory_manager.add_memory("Cycle 1 learning", "learning", 1)
        assert memory_manager.current_collection.count() == 1
        
        # Cycle 2: Add more memories
        memory_manager.add_memory("Cycle 2 learning", "learning", 2)
        assert memory_manager.current_collection.count() == 2
        
        # Cycle 3: Add more memories
        memory_manager.add_memory("Cycle 3 learning", "learning", 3)
        assert memory_manager.current_collection.count() == 3
        
        # Search should find all relevant
        results = memory_manager.search("learning", limit=10)
        assert len(results) == 3
    
    def test_agent_without_memory_works_normally(self, agents_with_memory):
        """Test that agents work fine when memory manager is None."""
        agent_no_memory = ConcreteAgent("test", memory_manager=None)
        
        # Execute should work
        result = agent_no_memory.execute(
            project_dir="/tmp/test",
            goal="Test"
        )
        
        assert result["success"] is True
        
        # Memory retrieval should return empty
        agent_no_memory._execution_context = {"goal": "Test"}
        memories = agent_no_memory._retrieve_and_format_memories()
        assert memories == ""


@pytest.mark.slow
class TestMemoryCleanup:
    """Test cleanup functionality (uses heavy Qwen3 model)."""
    
    @pytest.fixture
    def temp_memory_dir(self):
        """Create temporary memory directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_cleanup_removes_all_memories(self, temp_memory_dir):
        """Test that cleanup removes all project memories."""
        memory_manager = MemoryManager(memory_dir=temp_memory_dir)
        project_dir = "/tmp/test-cleanup"
        
        # Initialize and add memories
        memory_manager.initialize_project(project_dir, "Test goal")
        memory_manager.add_memory("Memory 1", "learning", 1)
        memory_manager.add_memory("Memory 2", "decision", 2)
        memory_manager.add_memory("Memory 3", "trace", 3)
        
        assert memory_manager.current_collection.count() == 3
        
        # Clear memories
        memory_manager.clear_project_memory(project_dir)
        
        # Reinitialize and check - should be empty
        memory_manager.initialize_project(project_dir, "Test goal")
        assert memory_manager.current_collection.count() == 0
    
    def test_cleanup_only_affects_target_project(self, temp_memory_dir):
        """Test that cleanup only removes memories for specified project."""
        memory_manager = MemoryManager(memory_dir=temp_memory_dir)
        
        project1 = "/tmp/test-project-a"
        project2 = "/tmp/test-project-b"
        
        # Add memories to project 1
        memory_manager.initialize_project(project1, "Goal 1")
        memory_manager.add_memory("Project 1 memory", "learning", 1)
        
        # Add memories to project 2
        memory_manager.initialize_project(project2, "Goal 2")
        memory_manager.add_memory("Project 2 memory", "learning", 1)
        
        # Clear project 1
        memory_manager.clear_project_memory(project1)
        
        # Project 2 should still have memories
        memory_manager.initialize_project(project2, "Goal 2")
        assert memory_manager.current_collection.count() == 1
        
        results = memory_manager.search("memory", limit=10)
        assert "Project 2" in results[0]["content"]


@pytest.mark.slow
class TestEndToEndScenario:
    """Test realistic end-to-end scenarios."""
    
    @pytest.fixture
    def temp_memory_dir(self):
        """Create temporary memory directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.mark.slow
    def test_realistic_multi_cycle_scenario(self, temp_memory_dir):
        """Test a realistic scenario across multiple cycles (uses heavy Qwen3 model)."""
        memory_manager = MemoryManager(memory_dir=temp_memory_dir)
        project_dir = "/tmp/realistic-project"
        goal = "Build REST API with authentication"
        
        # Initialize
        memory_manager.initialize_project(project_dir, goal)
        
        # Cycle 1: Initial implementation
        memory_manager.add_memory(
            content="Decided to use FastAPI framework",
            memory_type="decision",
            cycle=1
        )
        memory_manager.add_memory(
            content="Implemented basic user registration endpoint",
            memory_type="trace",
            cycle=1
        )
        
        # Cycle 2: Hit an issue
        memory_manager.add_memory(
            content="Tried using bcrypt for password hashing but had installation issues on M1 Mac",
            memory_type="failed_approach",
            cycle=2
        )
        memory_manager.add_memory(
            content="Switched to passlib with argon2 - works perfectly",
            memory_type="decision",
            cycle=2
        )
        
        # Cycle 3: Continuing implementation
        memory_manager.add_memory(
            content="All authentication logic in src/api/auth.py",
            memory_type="code_location",
            cycle=3
        )
        memory_manager.add_memory(
            content="API uses JWT tokens with 24h expiry, stored in httpOnly cookies",
            memory_type="pattern",
            cycle=3
        )
        
        # Cycle 4: Search for authentication context
        results = memory_manager.search(
            "authentication implementation approach",
            limit=10
        )
        
        # Should find relevant memories
        assert len(results) > 0
        
        # Should include the passlib decision
        contents = [r["content"] for r in results]
        assert any("passlib" in c or "argon2" in c for c in contents)
        
        # Should include the bcrypt failure (to avoid repeating)
        assert any("bcrypt" in c for c in contents)
        
        # Search for code location
        results = memory_manager.search(
            "where is authentication code",
            limit=5,
            memory_types=["code_location"]
        )
        
        assert len(results) > 0
        assert any("src/api/auth.py" in r["content"] for r in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

