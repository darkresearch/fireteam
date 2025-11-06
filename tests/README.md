# Fireteam Tests

This directory contains tests for the Fireteam codebase, with comprehensive coverage of the memory system.

## Running Tests

### Run All Memory Tests

```bash
cd /Users/osprey/repos/dark/fireteam
./tests/run_memory_tests.sh
```

### Run Specific Test Files

```bash
# Test MemoryManager
python -m pytest tests/test_memory_manager.py -v

# Test BaseAgent memory integration
python -m pytest tests/test_base_agent_memory.py -v

# Test full integration
python -m pytest tests/test_memory_integration.py -v

# Test project isolation
python -m pytest tests/test_memory_isolation.py -v
```

### Run All Tests

```bash
python -m pytest tests/ -v
```

### Run with Coverage

```bash
python -m pytest tests/ --cov=src --cov-report=html
```

## Test Structure

### Memory System Tests

1. **test_memory_manager.py** - Unit tests for MemoryManager
   - Initialization and model loading
   - Adding memories
   - Semantic search
   - Memory type filtering
   - Embedding caching
   - Cleanup functionality
   - Edge cases

2. **test_base_agent_memory.py** - Unit tests for BaseAgent memory integration
   - Execution context storage
   - Template method pattern
   - Automatic memory retrieval
   - Memory injection into prompts
   - Graceful degradation without memory

3. **test_memory_integration.py** - Integration tests
   - Full cycle memory flow
   - Reviewer learning extraction
   - Memory persistence across cycles
   - Realistic multi-cycle scenarios

4. **test_memory_isolation.py** - Project isolation tests
   - Separate collections per project
   - No memory leakage between projects
   - Cleanup isolation
   - Hash collision resistance

## Requirements

Install test dependencies:

```bash
pip install -r requirements.txt
```

This includes:
- pytest>=7.0.0
- chromadb>=1.0.0
- transformers>=4.50.0
- torch>=2.5.0

## First Run

**Note:** The first test run will download the Qwen3-Embedding-0.6B model (~1.2GB) from Hugging Face. This is cached locally, so subsequent runs are faster.

## Troubleshooting

### Model Download Issues

If model download fails:
```bash
# Clear Hugging Face cache
rm -rf ~/.cache/huggingface/

# Re-run tests
./tests/run_memory_tests.sh
```

### Chroma Database Lock Issues

If tests fail with database lock errors:
```bash
# Clear test artifacts
rm -rf /tmp/test-*
rm -rf /tmp/*-project-*

# Re-run tests
./tests/run_memory_tests.sh
```

### MPS/Metal Issues on Mac

If you see MPS-related warnings, this is normal. Tests will fall back to CPU automatically.

## Test Coverage

Current coverage focuses on memory system:
- ✅ MemoryManager CRUD operations
- ✅ Embedding generation and caching
- ✅ Semantic search functionality
- ✅ Project isolation
- ✅ BaseAgent template method pattern
- ✅ Automatic memory retrieval
- ✅ Learning extraction
- ✅ Cleanup functionality

## Future Test Coverage

Areas to expand:
- Full orchestrator cycle tests
- State manager integration
- Agent prompt injection verification
- Performance benchmarks

