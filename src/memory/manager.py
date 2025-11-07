"""Memory manager with semantic search and observability."""

import chromadb
from transformers import AutoModel, AutoTokenizer
from sentence_transformers import SentenceTransformer
import torch
import hashlib
import logging
import time
import uuid
from typing import Any, Optional
from functools import lru_cache


class MemoryManager:
    """Manages trace memory with automatic semantic search and observability."""
    
    def __init__(self, memory_dir: str = None, logger: logging.Logger = None, 
                 embedding_model: str = None):
        """Initialize with embeddings and Chroma storage.
        
        Args:
            memory_dir: Directory for memory storage
            logger: Logger instance
            embedding_model: HuggingFace model name for embeddings
                           (defaults to config.MEMORY_EMBEDDING_MODEL)
        """
        self.logger = logger or logging.getLogger("memory")
        
        if memory_dir is None:
            import config
            memory_dir = config.MEMORY_DIR
        
        self.logger.info("[MEMORY] Initializing MemoryManager...")
        
        # Initialize Chroma with persistent storage
        self.chroma_client = chromadb.PersistentClient(path=memory_dir)
        self.logger.info(f"[MEMORY] Chroma initialized at {memory_dir}")
        
        # Load embedding model
        if embedding_model is None:
            import config
            embedding_model = config.MEMORY_EMBEDDING_MODEL
        
        self.embedding_model_name = embedding_model
        self.logger.info(f"[MEMORY] Loading model {embedding_model}...")
        start_time = time.time()
        
        # Use sentence-transformers for lightweight models, 
        # otherwise use transformers library for Qwen3
        if 'sentence-transformers' in embedding_model or 'all-MiniLM' in embedding_model:
            # Lightweight model - use sentence-transformers API
            self.model = SentenceTransformer(embedding_model)
            self.tokenizer = self.model.tokenizer
            self.use_sentence_transformers = True
        else:
            # Qwen3 or other transformers model
            self.tokenizer = AutoTokenizer.from_pretrained(embedding_model)
            self.model = AutoModel.from_pretrained(embedding_model)
            self.use_sentence_transformers = False
            
            # Use Metal/MPS acceleration on Mac (with CPU fallback)
            if torch.backends.mps.is_available():
                self.model = self.model.to("mps")
                self.logger.info("[MEMORY] Using Metal/MPS acceleration")
            else:
                self.logger.info("[MEMORY] Using CPU (MPS not available)")
        
        load_time = time.time() - start_time
        self.logger.info(f"[MEMORY] Model loaded in {load_time:.2f}s")
        
        self.current_collection = None
    
    @lru_cache(maxsize=100)
    def _get_embeddings_cached(self, text_tuple: tuple) -> tuple:
        """Cached embedding generation (uses tuple for hashability)."""
        texts = list(text_tuple)
        return tuple(self._get_embeddings_impl(texts))
    
    def _get_embeddings_impl(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings using configured model."""
        if self.use_sentence_transformers:
            # Use sentence-transformers API (simpler)
            embeddings = self.model.encode(texts, convert_to_numpy=True)
            return embeddings.tolist()
        else:
            # Use transformers API for Qwen3
            # Tokenize
            inputs = self.tokenizer(texts, padding=True, truncation=True, return_tensors="pt")
            
            # Move to MPS if available
            if torch.backends.mps.is_available():
                inputs = {k: v.to("mps") for k, v in inputs.items()}
            
            # Generate embeddings
            with torch.no_grad():
                outputs = self.model(**inputs)
            
            # Mean pooling
            embeddings = outputs.last_hidden_state.mean(dim=1)
            
            # Normalize
            embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
            
            return embeddings.cpu().tolist()
    
    def _get_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Get embeddings with caching."""
        # Use cache for single text queries (common case)
        if len(texts) == 1:
            return list(self._get_embeddings_cached((texts[0],)))
        # Batch queries don't use cache
        return self._get_embeddings_impl(texts)
    
    def _get_collection_name(self, project_dir: str) -> str:
        """Generate collection name from project directory."""
        return hashlib.md5(project_dir.encode()).hexdigest()[:16]
    
    def initialize_project(self, project_dir: str, goal: str):
        """Initialize memory for a new project."""
        collection_name = self._get_collection_name(project_dir)
        self.logger.info(f"[MEMORY] Initializing project collection: {collection_name}")
        
        # Get or create collection
        self.current_collection = self.chroma_client.get_or_create_collection(
            name=collection_name,
            metadata={"project_dir": project_dir, "goal": goal}
        )
        
        # Log existing memory count
        count = self.current_collection.count()
        self.logger.info(f"[MEMORY] Project initialized with {count} existing memories")
    
    def add_memory(self, content: str, memory_type: str, cycle: int, metadata: dict = None):
        """
        Add a memory (unified method for all types).
        
        Args:
            content: The memory content (text)
            memory_type: Type (trace, failed_approach, decision, learning, code_location)
            cycle: Cycle number when this was recorded
            metadata: Optional additional metadata
        """
        if not self.current_collection:
            raise ValueError("Project not initialized. Call initialize_project first.")
        
        self.logger.debug(f"[MEMORY] Adding {memory_type} from cycle {cycle}: {content[:80]}...")
        
        start_time = time.time()
        
        # Generate embedding
        embedding = self._get_embeddings([content])[0]
        
        # Prepare metadata
        mem_metadata = {
            "type": memory_type,
            "cycle": cycle,
            **(metadata or {})
        }
        
        # Generate ID
        mem_id = str(uuid.uuid4())
        
        # Add to collection
        self.current_collection.add(
            ids=[mem_id],
            embeddings=[embedding],
            documents=[content],
            metadatas=[mem_metadata]
        )
        
        elapsed = time.time() - start_time
        self.logger.info(f"[MEMORY] Added {memory_type} in {elapsed:.2f}s")
    
    def search(self, query: str, limit: int = 10, memory_types: list[str] = None) -> list[dict]:
        """
        Semantic search for relevant memories.
        
        Args:
            query: Search query (will be embedded)
            limit: Maximum results to return
            memory_types: Filter by memory types (optional)
        
        Returns:
            List of memory dicts with 'content', 'type', 'cycle', etc.
        """
        if not self.current_collection:
            return []
        
        self.logger.info(f"[MEMORY] Searching: {query[:100]}...")
        start_time = time.time()
        
        # Generate query embedding (cached)
        query_embedding = self._get_embeddings([query])[0]
        
        # Build where clause for type filtering
        where = None
        if memory_types:
            where = {"type": {"$in": memory_types}}
            self.logger.debug(f"[MEMORY] Filtering by types: {memory_types}")
        
        # Search
        results = self.current_collection.query(
            query_embeddings=[query_embedding],
            n_results=limit,
            where=where
        )
        
        # Format results
        memories = []
        if results['documents'] and results['documents'][0]:
            for i, doc in enumerate(results['documents'][0]):
                memories.append({
                    "content": doc,
                    "type": results['metadatas'][0][i].get('type', 'unknown'),
                    "cycle": results['metadatas'][0][i].get('cycle', 0),
                    "distance": results['distances'][0][i] if 'distances' in results else None
                })
        
        elapsed = time.time() - start_time
        self.logger.info(f"[MEMORY] Found {len(memories)} memories in {elapsed:.2f}s")
        
        # Log top results if debug enabled
        if self.logger.level <= logging.DEBUG:
            for i, mem in enumerate(memories[:3]):  # Top 3
                self.logger.debug(f"[MEMORY]   {i+1}. [{mem['type']}] {mem['content'][:60]}...")
        
        return memories
    
    def clear_project_memory(self, project_dir: str):
        """Clear all memory for a project (with confirmation logging)."""
        collection_name = self._get_collection_name(project_dir)
        
        try:
            # Get count before deleting
            collection = self.chroma_client.get_collection(name=collection_name)
            count = collection.count()
            
            self.logger.info(f"[MEMORY] Deleting collection {collection_name} ({count} memories)...")
            self.chroma_client.delete_collection(name=collection_name)
            self.logger.info(f"[MEMORY] Successfully deleted {count} memories")
            
        except Exception as e:
            self.logger.warning(f"[MEMORY] Could not delete collection: {e}")

