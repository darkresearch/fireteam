# Fireteam Memory System

An OB-1-inspired trace memory system with spontaneous retrieval, providing agents with "ever-present" context awareness.

## Overview

Fireteam's memory system enables agents to learn from past experiences, avoid repeating mistakes, and maintain architectural consistency across cycles. Inspired by [OB-1's Terminal Bench #1 achievement](https://www.openblocklabs.com/blog/terminal-bench-1), our implementation uses local vector storage with state-of-the-art embeddings for semantic search.

## Core Philosophy: Spontaneous Memory

Memory retrieval feels like human thought - relevant memories automatically surface based on what agents are working on, without explicit queries. Agents don't know they're "checking memory" - memories just appear as background knowledge in their context.

## Architecture

### Technology Stack

- **Vector Database:** ChromaDB 1.0+ (embedded, persistent SQLite backend)
- **Embeddings:** Qwen3-Embedding-0.6B (70.58 MTEB score, state-of-the-art)
- **Acceleration:** Metal/MPS on MacBook Pro M-series (with CPU fallback)
- **Caching:** LRU cache for embeddings, Hugging Face model cache

### Storage Structure

```
memory/
  {project_hash}/           # MD5 hash of project_dir
    chroma_db/              # Vector database (persistent)
```

### Memory Types

All memories stored with `type` field:
- `trace` - Execution output, errors, files modified
- `failed_approach` - What didn't work and why
- `decision` - Architectural choices and rationale
- `learning` - Patterns and conventions discovered
- `code_location` - Where key functionality lives

### Project Isolation

Each project gets a unique collection based on MD5 hash of `project_dir`:
```python
collection_name = hashlib.md5(project_dir.encode()).hexdigest()[:16]
```

This ensures **zero cross-project contamination** - projects never share memories.

## How It Works

### Automatic Retrieval Flow

**Every cycle, before each agent executes:**

1. **Agent stores execution context** (`self._execution_context = kwargs`)
2. **Agent builds semantic query** from current task context
3. **MemoryManager performs semantic search** (retrieves top 10 relevant memories)
4. **BaseAgent injects memories** into system prompt silently
5. **Agent sees memories** as "background knowledge"

This happens **3 times per cycle** (once per agent: Planner → Executor → Reviewer).

### Agent-Specific Retrieval

**PlannerAgent** retrieves:
- `decision` - Past architectural choices
- `failed_approach` - What to avoid
- `learning` - Discovered patterns

Context query: `"Planning to achieve: {goal}. Recent feedback: {last_review}"`

**ExecutorAgent** retrieves:
- `failed_approach` - Implementation gotchas
- `trace` - Past execution patterns
- `code_location` - Where things are implemented

Context query: `"Implementing plan: {plan}. Goal: {goal}"`

**ReviewerAgent** retrieves:
- `learning` - Known patterns
- `decision` - Architectural constraints
- `pattern` - Code conventions

Context query: `"Reviewing implementation: {execution_result}. Original plan: {plan}"`

### Memory Recording

**After Execution:**
```python
memory.add_memory(
    content=executor_result["execution_result"],
    memory_type="trace",
    cycle=cycle_num
)
```

**After Review:**
```python
# Reviewer extracts structured learnings
for learning in reviewer_result["learnings"]:
    memory.add_memory(
        content=learning["content"],
        memory_type=learning["type"],
        cycle=cycle_num
    )
```

### Learning Extraction

Reviewer agent extracts learnings using special syntax:

```
LEARNING[pattern]: All database operations use connection pooling
LEARNING[decision]: Using JWT tokens with 24h expiry for sessions
LEARNING[failed_approach]: Attempted websockets but had CORS issues
LEARNING[code_location]: User authentication logic in src/auth/handler.py
```

These are automatically parsed and stored in memory.

## Usage

### Running with Memory (Default)

```bash
python src/orchestrator.py --project-dir /path/to/project --goal "Your goal"
```

Memory automatically:
- Records execution traces
- Extracts learnings
- Provides context to agents
- **Cleans up after completion**

### Debug Mode (Preserve Memory)

```bash
python src/orchestrator.py --project-dir /path/to/project --goal "Your goal" --keep-memory
```

Preserves memory and state after completion for analysis.

### First Run

**Note:** First run downloads Qwen3-Embedding-0.6B model (~1.2GB) from Hugging Face. This is cached locally at `~/.cache/huggingface/` and subsequent runs use the cached version.

## Performance

### Timing Characteristics

- **Model load:** 3-5 seconds (once at startup)
- **Per retrieval:** ~1 second (with caching)
- **Per cycle overhead:** ~3 seconds (3 automatic retrievals)
- **Embedding cache hit:** <50ms

### Resource Usage

- **Model size:** ~1.2GB (RAM)
- **GPU usage:** Metal/MPS on M-series Mac (optional, falls back to CPU)
- **Disk usage:** Grows with memories, auto-cleaned on completion

## Observability

All memory operations are logged with timing and counts:

```
[MEMORY] Initializing MemoryManager...
[MEMORY] Model loaded in 3.45s
[MEMORY] Using Metal/MPS acceleration
[MEMORY] Project initialized with 0 existing memories
[PLANNER] Retrieving memories...
[MEMORY] Searching: Planning to achieve: Build auth system...
[MEMORY] Found 3 memories in 0.85s
[PLANNER] Retrieved 3 memories in 0.87s
[MEMORY] Added trace in 0.42s
[MEMORY] Added decision in 0.38s
[MEMORY] Deleting collection a3f2e1... (15 memories)...
[MEMORY] Successfully deleted 15 memories
```

Enable debug logging for detailed output:
```bash
python src/orchestrator.py --project-dir /path --goal "Goal" --debug
```

## Testing

### Run All Memory Tests

```bash
./tests/run_memory_tests.sh
```

### Test Coverage

**36 comprehensive tests:**
- ✅ MemoryManager CRUD operations
- ✅ Embedding generation and caching
- ✅ Semantic search functionality
- ✅ Memory type filtering
- ✅ Project isolation
- ✅ BaseAgent template method pattern
- ✅ Automatic memory retrieval
- ✅ Learning extraction
- ✅ Cleanup functionality
- ✅ Edge cases and error handling

### Individual Test Suites

```bash
# Unit tests for MemoryManager
python -m pytest tests/test_memory_manager.py -v

# Unit tests for BaseAgent memory
python -m pytest tests/test_base_agent_memory.py -v

# Integration tests
python -m pytest tests/test_memory_integration.py -v

# Isolation tests
python -m pytest tests/test_memory_isolation.py -v
```

## Configuration

### Memory Settings (in `src/config.py`)

```python
# Memory configuration
MEMORY_DIR = os.path.join(SYSTEM_DIR, "memory")
MEMORY_EMBEDDING_MODEL = "Qwen/Qwen3-Embedding-0.6B"
MEMORY_SEARCH_LIMIT = 10  # How many memories to retrieve per query
```

### Customization

Adjust search limit for more/fewer memories:
```python
# In config.py
MEMORY_SEARCH_LIMIT = 15  # Retrieve more memories per query
```

## Key Design Decisions

### Why Local (No APIs)?

- ✅ **Complete privacy** - Data never leaves your machine
- ✅ **Zero costs** - No API fees per embedding
- ✅ **Fast** - No network latency
- ✅ **Reliable** - No external dependencies
- ✅ **Perfect for Terminal Bench** - No repeated model downloads

### Why Qwen3-Embedding-0.6B?

- ✅ **State-of-the-art quality** - 70.58 MTEB score (beats competitors)
- ✅ **Optimized for Mac** - Excellent Metal/MPS performance
- ✅ **Good size/performance** - 600M parameters is sweet spot
- ✅ **Code-aware** - Trained on multilingual corpus including code
- ✅ **Open source** - Apache 2.0 license

### Why Spontaneous Retrieval?

Traditional approach:
```python
# Agent explicitly queries memory
if should_check_memory():
    memories = memory.search(query)
```

**Problems:**
- Agent decides when to check (adds complexity)
- Explicit queries feel mechanical
- Easy to forget to check

**Our approach:**
```python
# Memory automatically appears in context
# Agent never knows it's happening
```

**Benefits:**
- Mimics human thought (memories pop up naturally)
- No decision overhead
- Always relevant (semantic search)
- Agent-specific (each gets what it needs)

### Why Chroma?

- ✅ Embedded (no external service)
- ✅ Mature and stable
- ✅ Built for LLM workflows
- ✅ Persistent SQLite backend
- ✅ Excellent Python API

## Example Memory Flow

### Cycle 1: Initial Implementation

**Executor completes work:**
```
"Implemented JWT authentication using jsonwebtoken library.
Created middleware in src/auth/jwt.js.
All tests passing."
```

**Stored as:** `trace` memory

**Reviewer extracts learnings:**
```
LEARNING[decision]: Using JWT tokens with 24h expiry for sessions
LEARNING[code_location]: Authentication middleware in src/auth/jwt.js
LEARNING[pattern]: All protected routes use auth middleware
```

**Stored as:** 3 separate memories (`decision`, `code_location`, `pattern`)

### Cycle 2: Hit a Problem

**Executor reports:**
```
"Attempted to add refresh tokens using redis-om library
but encountered connection errors in test environment.
Falling back to in-memory session store."
```

**Stored as:** `trace` memory

**Reviewer extracts:**
```
LEARNING[failed_approach]: Tried redis-om for refresh tokens but had connection issues
LEARNING[decision]: Using in-memory session store for MVP
```

**Stored as:** 2 memories

### Cycle 5: Planning Auth Improvements

**Planner automatically receives context:**
```
---
BACKGROUND KNOWLEDGE FROM PREVIOUS WORK:
(You have access to these learnings from earlier cycles)

• Decision (Cycle 1): Using JWT tokens with 24h expiry for sessions
• Failed Approach (Cycle 2): Tried redis-om for refresh tokens but had connection issues
• Code Location (Cycle 1): Authentication middleware in src/auth/jwt.js
• Pattern (Cycle 1): All protected routes use auth middleware

Use this background knowledge naturally. Don't explicitly reference cycles.
---
```

Planner naturally avoids redis-om and builds on existing JWT implementation.

## Troubleshooting

### Model Download Issues

If model download fails on first run:
```bash
# Check Hugging Face cache
ls -lh ~/.cache/huggingface/hub/models--Qwen--Qwen3-Embedding-0.6B/

# Clear cache and retry
rm -rf ~/.cache/huggingface/
python src/orchestrator.py --project-dir /path --goal "Test"
```

### Memory Not Working

Check logs for `[MEMORY]` prefix:
```bash
# Look for memory operations in logs
grep "\[MEMORY\]" logs/orchestrator_*.log
```

Should see:
- Model loading
- Project initialization
- Search operations
- Memory additions

### MPS/Metal Issues on Mac

If you see warnings about MPS:
```
[MEMORY] Using CPU (MPS not available)
```

This is fine - memory will work on CPU. Slightly slower but functional.

To enable MPS, ensure PyTorch 2.5+ with Metal support:
```bash
pip install --upgrade torch
```

### Cleanup Issues

If cleanup fails:
```bash
# Manual cleanup
rm -rf memory/{project_hash}/
rm state/current.json
```

Or run with `--keep-memory` to preserve data.

## Comparison to OB-1

### Similarities (Inspired By)

- ✅ Trace memory (commands, outputs, errors)
- ✅ Recording failed approaches
- ✅ Preventing mistake repetition
- ✅ Context across long-horizon tasks

### Enhancements (We Added)

- ✅ **Semantic search** - Find memories by meaning, not keywords
- ✅ **Agent-specific retrieval** - Each agent gets relevant context
- ✅ **Spontaneous injection** - Memories appear automatically
- ✅ **State-of-the-art embeddings** - Qwen3-0.6B (70.58 MTEB)
- ✅ **Comprehensive observability** - All operations logged with timing
- ✅ **Automatic cleanup** - No manual memory management
- ✅ **Project isolation** - Multi-project support

## Future Enhancements (Post-MVP)

Ideas for extending the memory system:

1. **Memory Consolidation** - Merge duplicate/similar learnings
2. **Forgetting Mechanism** - Remove outdated or irrelevant memories
3. **Cross-Project Transfer** - Opt-in knowledge sharing between projects
4. **Memory Analytics** - Dashboard showing memory growth and patterns
5. **Export/Import** - Share memory dumps for debugging or collaboration
6. **Semantic Clustering** - Visualize related memories as knowledge graph

## Implementation Details

### Files Created

- `src/memory/manager.py` - Core MemoryManager class (220 lines)
- `src/memory/__init__.py` - Module initialization
- `tests/test_memory_manager.py` - 14 unit tests
- `tests/test_base_agent_memory.py` - 10 unit tests
- `tests/test_memory_integration.py` - 5 integration tests
- `tests/test_memory_isolation.py` - 7 isolation tests
- `tests/run_memory_tests.sh` - Test runner script

### Files Modified

- `requirements.txt` - Added chromadb, transformers, torch, pytest
- `src/config.py` - Added memory configuration
- `src/agents/base.py` - Template method pattern + automatic retrieval
- `src/agents/planner.py` - Memory integration
- `src/agents/executor.py` - Memory integration
- `src/agents/reviewer.py` - Memory integration + learning extraction
- `src/orchestrator.py` - Full lifecycle integration + cleanup

### Lines of Code

- **Production code:** ~400 lines (MemoryManager + BaseAgent enhancements)
- **Test code:** ~500 lines (36 comprehensive tests)
- **Total:** ~900 lines for complete memory system

## Dependencies Added

```
chromadb>=1.0.0        # Vector database
transformers>=4.50.0   # Hugging Face model loading
torch>=2.5.0           # PyTorch with Metal/MPS support
pytest>=7.0.0          # Testing framework
```

## Version History

### v1.0.0 - Initial Memory System (November 6, 2025)

**Features:**
- Local vector storage with ChromaDB
- Qwen3-Embedding-0.6B for state-of-the-art retrieval
- Spontaneous memory retrieval
- Agent-specific context queries
- Automatic cleanup with debug mode
- Comprehensive test coverage (36 tests)
- Full observability with timing metrics

**Performance:**
- ~3 seconds overhead per cycle
- ~1.2GB model size (cached locally)
- Metal/MPS acceleration on Mac

**Inspired by:** OB-1's Terminal Bench achievement ([blog post](https://www.openblocklabs.com/blog/terminal-bench-1))

## Contributing

When extending the memory system:

1. **Add new memory types** - Update `memory_type` field values
2. **Customize retrieval** - Override `_build_memory_context_query()` in agents
3. **Add metadata** - Pass `metadata` dict to `add_memory()`
4. **Test thoroughly** - Add tests to appropriate test file
5. **Document** - Update this file with new features

## Support

For issues related to memory system:
- Check logs for `[MEMORY]` prefixed messages
- Run tests: `./tests/run_memory_tests.sh`
- Enable debug logging: `--debug` flag
- Preserve memory for inspection: `--keep-memory` flag

## References

- [OB-1 Terminal Bench Achievement](https://www.openblocklabs.com/blog/terminal-bench-1)
- [ChromaDB Documentation](https://docs.trychroma.com/)
- [Qwen3 Model Card](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B)
- [MTEB Leaderboard](https://huggingface.co/spaces/mteb/leaderboard)

