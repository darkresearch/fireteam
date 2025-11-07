"""
Lightweight embedding tests using sentence-transformers.
Fast tests for CI that verify HuggingFace integration without heavy model downloads.
"""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.mark.lightweight
class TestLightweightEmbeddings:
    """Fast embedding tests using lightweight model."""
    
    def test_huggingface_pipeline_works(self, lightweight_memory_manager):
        """Verify HuggingFace model loading and embedding generation."""
        # Test embedding generation
        embeddings = lightweight_memory_manager._get_embeddings(["test text"])
        
        assert len(embeddings) == 1
        assert isinstance(embeddings[0], list)
        assert len(embeddings[0]) == 384  # MiniLM-L6-v2 dimension
    
    def test_save_and_retrieve_memories(self, lightweight_memory_manager, isolated_tmp_dir):
        """Test full save/retrieve cycle with semantic search."""
        project_dir = isolated_tmp_dir / "project"
        project_dir.mkdir()
        
        # Initialize and add memories
        lightweight_memory_manager.initialize_project(str(project_dir), "Test goal")
        
        lightweight_memory_manager.add_memory(
            "Using FastAPI for REST API",
            "decision", 1
        )
        lightweight_memory_manager.add_memory(
            "JWT authentication with 24h expiry",
            "pattern", 2
        )
        
        # Semantic search should work
        results = lightweight_memory_manager.search("API framework", limit=5)
        
        assert len(results) > 0
        assert any("FastAPI" in r["content"] for r in results)

