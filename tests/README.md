# Fireteam Tests

This directory contains comprehensive tests for the entire Fireteam codebase, including unit tests and integration tests for all components.

## Test Summary

**Total Tests: 161**

- ✅ **Configuration Tests** (15 tests) - test_config.py
- ✅ **State Manager Tests** (20 tests) - test_state_manager.py
- ✅ **Agent Tests** (38 tests) - test_agents.py
- ✅ **Orchestrator Tests** (28 tests) - test_orchestrator.py
- ✅ **CLI Tools Tests** (24 tests) - test_cli_tools.py
- ✅ **Memory System Tests** (36 tests) - test_memory_*.py

## Running Tests

### Run All Tests

```bash
cd /Users/osprey/repos/dark/fireteam
source .venv/bin/activate
pytest tests/ -v
```

### Run Specific Test Categories

```bash
# Configuration tests
pytest tests/test_config.py -v

# State manager tests
pytest tests/test_state_manager.py -v

# Agent tests (BaseAgent, Planner, Executor, Reviewer)
pytest tests/test_agents.py -v

# Orchestrator integration tests
pytest tests/test_orchestrator.py -v

# CLI tools tests
pytest tests/test_cli_tools.py -v

# Memory system tests
pytest tests/test_memory_*.py -v
```

### Run with Coverage

```bash
pytest tests/ --cov=src --cov-report=html
```

### Run Specific Test

```bash
pytest tests/test_config.py::TestConfig::test_agent_timeouts -v
```

## Test Structure

### 1. Configuration Tests (`test_config.py`)

Tests for configuration module and environment variable handling:
- System directory configuration
- API key validation and lazy loading
- SDK configuration (tools, permissions, model)
- Agent configuration (retries, timeouts)
- Completion thresholds
- Git configuration
- Logging configuration
- Sudo configuration
- Memory system configuration
- Environment variable overrides
- Type validation

### 2. State Manager Tests (`test_state_manager.py`)

Tests for project state management:
- Initialization and file structure
- Project state initialization
- State loading and persistence
- State updates and timestamps
- Status reporting
- Completion tracking
- State clearing
- Cycle counting
- Completion percentage updates with fallbacks
- Parse failure handling
- State isolation between projects
- File locking mechanism
- Concurrent updates
- JSON format validation

### 3. Agent Tests (`test_agents.py`)

Tests for all agent classes:

**BaseAgent:**
- Initialization and configuration
- Abstract method enforcement
- Execution context storage
- Memory manager integration
- Memory retrieval with/without manager
- Timeout configuration

**PlannerAgent:**
- Initialization and system prompts
- Initial plan generation
- Plan updates based on feedback
- Memory context building
- Relevant memory type filtering
- Success and failure handling

**ExecutorAgent:**
- Initialization and system prompts
- Execution prompt building
- Memory context building
- Relevant memory type filtering
- Success and failure handling

**ReviewerAgent:**
- Initialization and system prompts
- Review prompt building
- Validation mode
- Completion percentage extraction (multiple formats)
- Learning extraction from reviews
- Memory context building
- Relevant memory type filtering
- Success and failure handling

### 4. Orchestrator Tests (`test_orchestrator.py`)

Integration tests for the main orchestrator:
- Initialization with various flags
- Logging setup
- Git repository initialization (new and existing)
- Git commit changes
- Remote push handling
- Completion checking and validation
- Cycle execution structure
- Agent failure handling (planner, executor, reviewer)
- Learning extraction and storage
- Goal alignment checks
- Memory manager injection
- State manager integration
- Signal handling
- Validation mode triggering
- CLI interface and argument parsing

### 5. CLI Tools Tests (`test_cli_tools.py`)

Tests for command-line utilities:
- Fireteam status command functionality
- Process monitoring
- State file parsing
- Timestamp formatting
- Script existence and structure
- Argument parsing
- System resource monitoring (memory, CPU, disk)
- PID file handling
- Log file handling
- Error handling
- Output formatting

### 6. Memory System Tests (`test_memory_*.py`)

Comprehensive tests for the memory system:

**test_memory_manager.py:**
- Initialization and model loading
- Project initialization
- Adding memories
- Semantic search
- Memory type filtering
- Embedding caching
- Cleanup functionality
- Edge cases

**test_base_agent_memory.py:**
- Execution context storage
- Template method pattern
- Automatic memory retrieval
- Memory injection into prompts
- Graceful degradation without memory

**test_memory_integration.py:**
- Full cycle memory flow
- Reviewer learning extraction
- Memory persistence across cycles
- Realistic multi-cycle scenarios

**test_memory_isolation.py:**
- Separate collections per project
- No memory leakage between projects
- Cleanup isolation
- Hash collision resistance

## Requirements

Install test dependencies using uv:

```bash
cd /Users/osprey/repos/dark/fireteam
source .venv/bin/activate
uv pip install -r requirements.txt
```

Key dependencies:
- pytest>=7.0.0
- chromadb>=1.0.0
- transformers>=4.50.0
- torch>=2.5.0

## First Run

**Note:** The first test run will download the Qwen3-Embedding-0.6B model (~1.2GB) from Hugging Face for memory tests. This is cached locally, so subsequent runs are faster.

## Troubleshooting

### Model Download Issues

If model download fails:
```bash
# Clear Hugging Face cache
rm -rf ~/.cache/huggingface/

# Re-run tests
pytest tests/ -v
```

### Chroma Database Lock Issues

If tests fail with database lock errors:
```bash
# Clear test artifacts
rm -rf /tmp/test-*
rm -rf /tmp/*-project-*

# Re-run tests
pytest tests/ -v
```

### MPS/Metal Issues on Mac

If you see MPS-related warnings, this is normal. Tests will fall back to CPU automatically.

## Test Coverage

✅ **Comprehensive Coverage** across all components:

### Core Components
- ✅ Configuration management
- ✅ State management and persistence
- ✅ File locking and concurrency
- ✅ Project isolation
- ✅ Completion tracking

### Agents
- ✅ BaseAgent template pattern
- ✅ PlannerAgent logic
- ✅ ExecutorAgent logic
- ✅ ReviewerAgent logic
- ✅ Memory integration
- ✅ Timeout configuration

### Orchestrator
- ✅ Full cycle execution
- ✅ Git integration
- ✅ Agent coordination
- ✅ Error handling
- ✅ Validation mode
- ✅ Learning extraction

### Memory System
- ✅ MemoryManager CRUD operations
- ✅ Embedding generation and caching
- ✅ Semantic search functionality
- ✅ Project isolation
- ✅ Automatic retrieval
- ✅ Learning extraction
- ✅ Cleanup functionality

### CLI Tools
- ✅ Status monitoring
- ✅ Process management
- ✅ Log handling
- ✅ Error handling
- ✅ Output formatting

## Test Quality

All tests follow best practices:
- **Isolated**: Each test is independent
- **Deterministic**: Tests produce consistent results
- **Fast**: Most tests run in milliseconds
- **Comprehensive**: Test both success and failure paths
- **Intent-focused**: Test functionality, not implementation details
- **Well-documented**: Clear test names and docstrings

## New Test Categories

### Lightweight Tests (2 tests)

Fast tests using small embedding models (`sentence-transformers/all-MiniLM-L6-v2`).
Verify HuggingFace integration without heavy downloads.

**What they test:**
- HuggingFace model loading pipeline
- Embedding generation works
- Save/retrieve memories with semantic search

**Run with:**
```bash
pytest tests/ -m "lightweight" -v
```

**Performance:** ~5-10 seconds (first run downloads ~80MB model)

### End-to-End Tests (1 test)

Real subprocess tests that spawn Fireteam and complete actual tasks.
Uses real Claude API - costs money and takes time.

**What they test:**
- Complete Fireteam workflow from start to finish
- Real subprocess spawning
- File creation and git commits
- Task completion with 95%+ accuracy

**Run with:**
```bash
pytest tests/ -m "e2e" -v --keep-artifacts
```

**Performance:** ~3-5 minutes per test
**Cost:** ~$0.10-0.50 per run (uses Claude API)

### Integration Tests (1 test)

Tests with external systems (terminal-bench).
Requires `tb` command to be installed.

**What they test:**
- Terminal-bench adapter works correctly
- 100% accuracy on hello-world task
- Installation script works
- Container environment setup

**Run with:**
```bash
pytest tests/ -m "integration" -v
```

**Performance:** ~10 minutes per test
**Cost:** ~$0.20-1.00 per run (uses Claude API)

## Running Tests Selectively

```bash
# Fast tests only (skip API calls and slow tests) - for CI
pytest tests/ -m "not slow and not e2e and not integration" -v

# All unit tests including lightweight embedding tests
pytest tests/ -m "not slow" -v

# Only slow/expensive tests
pytest tests/ -m "slow" -v

# Parallel execution (safe with isolated fixtures)
pytest tests/ -n auto

# Keep artifacts on failure for debugging
pytest tests/ --keep-artifacts -v
```

## Dependencies

### Core test dependencies (always needed):
- pytest>=7.0.0
- All src/ dependencies (chromadb, transformers, torch, etc.)

### Lightweight embedding tests:
- sentence-transformers>=2.2.0 (already in requirements.txt)

### Integration tests:
- terminal-bench: `uv tool install terminal-bench`
- Docker (for terminal-bench containers)

## API Costs & CI Considerations

E2E and integration tests use real Claude API:
- **Hello world test:** ~$0.10-0.50 per run
- **Terminal-bench test:** ~$0.20-1.00 per run

**Recommendation for CI:**
- Run fast tests (unit + lightweight) on all PRs (~2 minutes, no cost)
- Run e2e/integration tests only on main branch (saves ~$1-2 per PR)

## Test Summary

**Total: 165 tests**

- Configuration: 15 tests
- State Manager: 20 tests
- Agents: 38 tests
- Orchestrator: 28 tests
- CLI Tools: 24 tests
- Memory System: 36 tests
- **Lightweight Embeddings: 2 tests** ⚡ NEW
- **E2E Hello World: 1 test** 🚀 NEW
- **Terminal-bench Integration: 1 test** 🎯 NEW

