"""
Unit tests for MemoryManager.
Tests CRUD operations, embeddings, search, and project isolation.
"""

import pytest
import tempfile
import shutil
import os
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from memory.manager import MemoryManager


@pytest.mark.slow
class TestMemoryManager:
    """Test MemoryManager functionality (uses heavy Qwen3 model)."""
    
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
    
    def test_initialization(self, memory_manager):
        """Test MemoryManager initializes correctly."""
        assert memory_manager is not None
        assert memory_manager.chroma_client is not None
        assert memory_manager.model is not None
        assert memory_manager.tokenizer is not None
        assert memory_manager.current_collection is None
    
    def test_model_loading(self, memory_manager):
        """Test Qwen3 model loads successfully."""
        # Model should be loaded
        assert memory_manager.model is not None
        assert memory_manager.tokenizer is not None
        
        # Test embedding generation
        embeddings = memory_manager._get_embeddings(["test text"])
        assert len(embeddings) == 1
        assert isinstance(embeddings[0], list)
        assert len(embeddings[0]) > 0  # Should have dimensions
    
    def test_project_initialization(self, memory_manager, temp_memory_dir):
        """Test project memory initialization."""
        project_dir = "/tmp/test-project-1"
        goal = "Build a test project"
        
        memory_manager.initialize_project(project_dir, goal)
        
        # Should have current collection
        assert memory_manager.current_collection is not None
        
        # Collection should be empty for new project
        count = memory_manager.current_collection.count()
        assert count == 0
    
    def test_add_memory(self, memory_manager):
        """Test adding memories."""
        project_dir = "/tmp/test-project-2"
        memory_manager.initialize_project(project_dir, "Test goal")
        
        # Add a memory
        memory_manager.add_memory(
            content="This is a test learning",
            memory_type="learning",
            cycle=1
        )
        
        # Should have 1 memory
        count = memory_manager.current_collection.count()
        assert count == 1
        
        # Add more memories
        memory_manager.add_memory(
            content="Failed approach: tried X",
            memory_type="failed_approach",
            cycle=2
        )
        memory_manager.add_memory(
            content="Decision: chose Y",
            memory_type="decision",
            cycle=2
        )
        
        count = memory_manager.current_collection.count()
        assert count == 3
    
    def test_semantic_search(self, memory_manager):
        """Test semantic search functionality."""
        project_dir = "/tmp/test-project-3"
        memory_manager.initialize_project(project_dir, "Test goal")
        
        # Add some memories
        memory_manager.add_memory(
            content="Authentication uses JWT tokens with 24h expiry",
            memory_type="decision",
            cycle=1
        )
        memory_manager.add_memory(
            content="Database uses PostgreSQL with connection pooling",
            memory_type="pattern",
            cycle=2
        )
        memory_manager.add_memory(
            content="Tried bcrypt but had Node 18 compatibility issues",
            memory_type="failed_approach",
            cycle=3
        )
        
        # Search for authentication
        results = memory_manager.search("authentication approach", limit=5)
        
        # Should find the JWT decision
        assert len(results) > 0
        assert any("JWT" in r["content"] for r in results)
        
        # Top result should be about auth
        assert "auth" in results[0]["content"].lower() or "JWT" in results[0]["content"]
    
    def test_memory_type_filtering(self, memory_manager):
        """Test filtering by memory type."""
        project_dir = "/tmp/test-project-4"
        memory_manager.initialize_project(project_dir, "Test goal")
        
        # Add different types
        memory_manager.add_memory("Pattern 1", "pattern", 1)
        memory_manager.add_memory("Decision 1", "decision", 1)
        memory_manager.add_memory("Failed approach 1", "failed_approach", 2)
        
        # Search with type filter
        results = memory_manager.search(
            "approach",
            limit=10,
            memory_types=["failed_approach"]
        )
        
        # Should only return failed_approach type
        assert len(results) > 0
        assert all(r["type"] == "failed_approach" for r in results)
    
    def test_project_isolation(self, memory_manager):
        """Test that different projects have isolated memories."""
        project1 = "/tmp/test-project-isolation-1"
        project2 = "/tmp/test-project-isolation-2"
        
        # Initialize project 1 and add memory
        memory_manager.initialize_project(project1, "Goal 1")
        memory_manager.add_memory("Project 1 memory", "learning", 1)
        
        count1 = memory_manager.current_collection.count()
        assert count1 == 1
        
        # Switch to project 2
        memory_manager.initialize_project(project2, "Goal 2")
        
        # Should be empty (different project)
        count2 = memory_manager.current_collection.count()
        assert count2 == 0
        
        # Add memory to project 2
        memory_manager.add_memory("Project 2 memory", "learning", 1)
        count2 = memory_manager.current_collection.count()
        assert count2 == 1
        
        # Switch back to project 1
        memory_manager.initialize_project(project1, "Goal 1")
        
        # Should still have 1 memory (isolated)
        count1 = memory_manager.current_collection.count()
        assert count1 == 1
        
        # Search should only return project 1 memory
        results = memory_manager.search("memory", limit=10)
        assert len(results) == 1
        assert "Project 1" in results[0]["content"]
    
    def test_embedding_caching(self, memory_manager):
        """Test that embeddings are cached for repeated queries."""
        project_dir = "/tmp/test-project-5"
        memory_manager.initialize_project(project_dir, "Test goal")
        
        # Add a memory
        memory_manager.add_memory("Test content", "learning", 1)
        
        # Clear cache info
        cache_info_before = memory_manager._get_embeddings_cached.cache_info()
        
        # Search multiple times with same query
        memory_manager.search("test query")
        memory_manager.search("test query")
        memory_manager.search("test query")
        
        # Cache should have hits
        cache_info_after = memory_manager._get_embeddings_cached.cache_info()
        assert cache_info_after.hits > cache_info_before.hits
    
    def test_clear_project_memory(self, memory_manager):
        """Test clearing project memory."""
        project_dir = "/tmp/test-project-6"
        memory_manager.initialize_project(project_dir, "Test goal")
        
        # Add memories
        memory_manager.add_memory("Memory 1", "learning", 1)
        memory_manager.add_memory("Memory 2", "decision", 2)
        
        assert memory_manager.current_collection.count() == 2
        
        # Clear memories
        memory_manager.clear_project_memory(project_dir)
        
        # Collection should be deleted - reinitialize to check
        memory_manager.initialize_project(project_dir, "Test goal")
        assert memory_manager.current_collection.count() == 0
    
    def test_memory_metadata(self, memory_manager):
        """Test that metadata is stored correctly."""
        project_dir = "/tmp/test-project-7"
        memory_manager.initialize_project(project_dir, "Test goal")
        
        # Add memory with custom metadata
        memory_manager.add_memory(
            content="Test content",
            memory_type="decision",
            cycle=5,
            metadata={"custom_field": "custom_value"}
        )
        
        # Search and verify metadata
        results = memory_manager.search("test", limit=1)
        assert len(results) == 1
        assert results[0]["type"] == "decision"
        assert results[0]["cycle"] == 5


@pytest.mark.slow
class TestMemoryManagerEdgeCases:
    """Test edge cases and error handling (uses heavy Qwen3 model)."""
    
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
    
    def test_add_memory_without_initialization(self, memory_manager):
        """Test that adding memory without project initialization raises error."""
        with pytest.raises(ValueError, match="Project not initialized"):
            memory_manager.add_memory("Test", "learning", 1)
    
    def test_search_without_initialization(self, memory_manager):
        """Test search without initialization returns empty list."""
        results = memory_manager.search("test")
        assert results == []
    
    def test_empty_search_query(self, memory_manager):
        """Test search with empty query."""
        memory_manager.initialize_project("/tmp/test", "Goal")
        results = memory_manager.search("")
        assert isinstance(results, list)
    
    def test_clear_nonexistent_project(self, memory_manager):
        """Test clearing memory for project that doesn't exist."""
        # Should not raise error
        memory_manager.clear_project_memory("/tmp/nonexistent-project")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

