"""
Isolation tests for memory system.
Verifies that different projects have completely isolated memories.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from memory.manager import MemoryManager


@pytest.mark.slow
class TestProjectIsolation:
    """Test that different projects have isolated memories (uses heavy Qwen3 model)."""
    
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
    
    def test_two_projects_have_separate_collections(self, memory_manager):
        """Test that two projects create separate Chroma collections."""
        project1 = "/tmp/isolated-project-1"
        project2 = "/tmp/isolated-project-2"
        
        # Get collection names
        collection1 = memory_manager._get_collection_name(project1)
        collection2 = memory_manager._get_collection_name(project2)
        
        # Should be different
        assert collection1 != collection2
        
        # Should be deterministic (same input = same hash)
        assert collection1 == memory_manager._get_collection_name(project1)
        assert collection2 == memory_manager._get_collection_name(project2)
    
    def test_memories_dont_leak_between_projects(self, memory_manager):
        """Test that memories from one project don't appear in another."""
        project1 = "/tmp/isolated-project-alpha"
        project2 = "/tmp/isolated-project-beta"
        
        # Project 1: Add memories about authentication
        memory_manager.initialize_project(project1, "Build auth system")
        memory_manager.add_memory("Using JWT tokens for auth", "decision", 1)
        memory_manager.add_memory("Password hashing with bcrypt", "pattern", 1)
        memory_manager.add_memory("Auth middleware in src/auth/", "code_location", 2)
        
        assert memory_manager.current_collection.count() == 3
        
        # Project 2: Add memories about e-commerce
        memory_manager.initialize_project(project2, "Build e-commerce site")
        memory_manager.add_memory("Using Stripe for payments", "decision", 1)
        memory_manager.add_memory("Product catalog in MongoDB", "pattern", 1)
        
        # Project 2 should only have 2 memories
        assert memory_manager.current_collection.count() == 2
        
        # Search in project 2 for auth-related content
        results = memory_manager.search("authentication JWT", limit=10)
        
        # Should NOT find any auth memories from project 1
        for result in results:
            assert "JWT" not in result["content"]
            assert "bcrypt" not in result["content"]
            assert "auth" not in result["content"].lower()
        
        # Should find e-commerce memories
        results = memory_manager.search("payment", limit=10)
        assert len(results) > 0
        assert any("Stripe" in r["content"] for r in results)
    
    def test_switching_between_projects(self, memory_manager):
        """Test switching between projects maintains isolation."""
        project_a = "/tmp/project-a"
        project_b = "/tmp/project-b"
        
        # Initialize project A
        memory_manager.initialize_project(project_a, "Project A")
        memory_manager.add_memory("Project A memory 1", "learning", 1)
        memory_manager.add_memory("Project A memory 2", "decision", 2)
        
        # Switch to project B
        memory_manager.initialize_project(project_b, "Project B")
        memory_manager.add_memory("Project B memory 1", "learning", 1)
        
        # Switch back to project A
        memory_manager.initialize_project(project_a, "Project A")
        
        # Should still have 2 memories
        assert memory_manager.current_collection.count() == 2
        
        # Search should only return project A memories
        results = memory_manager.search("memory", limit=10)
        assert len(results) == 2
        assert all("Project A" in r["content"] for r in results)
    
    def test_concurrent_projects_in_same_memory_dir(self, temp_memory_dir):
        """Test that multiple MemoryManager instances can work with different projects."""
        # Create two separate memory managers (simulating concurrent processes)
        manager1 = MemoryManager(memory_dir=temp_memory_dir)
        manager2 = MemoryManager(memory_dir=temp_memory_dir)
        
        project1 = "/tmp/concurrent-project-1"
        project2 = "/tmp/concurrent-project-2"
        
        # Initialize different projects
        manager1.initialize_project(project1, "Goal 1")
        manager2.initialize_project(project2, "Goal 2")
        
        # Add memories
        manager1.add_memory("Manager 1 memory", "learning", 1)
        manager2.add_memory("Manager 2 memory", "learning", 1)
        
        # Each should have 1 memory
        assert manager1.current_collection.count() == 1
        assert manager2.current_collection.count() == 1
        
        # Verify isolation
        results1 = manager1.search("memory", limit=10)
        results2 = manager2.search("memory", limit=10)
        
        assert len(results1) == 1
        assert len(results2) == 1
        assert "Manager 1" in results1[0]["content"]
        assert "Manager 2" in results2[0]["content"]
    
    def test_cleanup_only_affects_target_project(self, memory_manager):
        """Test that cleanup doesn't affect other projects."""
        project1 = "/tmp/cleanup-project-1"
        project2 = "/tmp/cleanup-project-2"
        project3 = "/tmp/cleanup-project-3"
        
        # Create memories in all projects
        for project in [project1, project2, project3]:
            memory_manager.initialize_project(project, f"Goal for {project}")
            memory_manager.add_memory(f"Memory for {project}", "learning", 1)
        
        # Clear project 2
        memory_manager.clear_project_memory(project2)
        
        # Project 1 should still have memories
        memory_manager.initialize_project(project1, "Goal")
        assert memory_manager.current_collection.count() == 1
        
        # Project 2 should be empty
        memory_manager.initialize_project(project2, "Goal")
        assert memory_manager.current_collection.count() == 0
        
        # Project 3 should still have memories
        memory_manager.initialize_project(project3, "Goal")
        assert memory_manager.current_collection.count() == 1
    
    def test_hash_collision_resistance(self, memory_manager):
        """Test that similar project paths generate different hashes."""
        project_paths = [
            "/tmp/project",
            "/tmp/project1",
            "/tmp/project2",
            "/tmp/projects",
            "/tmp/my-project"
        ]
        
        hashes = [memory_manager._get_collection_name(p) for p in project_paths]
        
        # All hashes should be unique
        assert len(hashes) == len(set(hashes))
        
        # Each hash should be 16 characters (MD5 truncated)
        assert all(len(h) == 16 for h in hashes)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

