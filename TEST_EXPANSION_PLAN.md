# Test Expansion Implementation Plan

## Problem Statement

The Fireteam project currently has comprehensive tests for the memory system (Maria) with 36 test cases covering:
- Memory manager CRUD operations
- Agent memory integration
- Memory isolation between projects  
- End-to-end memory scenarios

However, **critical functionality lacks test coverage**:
- **Orchestrator**: No tests for the main orchestration loop, cycle execution, completion checking, git operations
- **State Manager**: No tests for state persistence, locking, completion tracking, parse failure handling
- **Individual Agents**: No tests for Planner, Executor, or Reviewer agent functionality
- **Config**: No tests for configuration loading and validation
- **CLI tools**: No tests for the CLI utilities (start-agent, stop-agent, agent-progress)
- **Integration**: No full system integration tests simulating complete orchestration cycles

This limits confidence in:
1. Core orchestration logic correctness
2. State management reliability
3. Agent behavior under various conditions
4. System-level workflows
5. Edge cases and error handling

## Current State

### Existing Test Infrastructure
**Location**: `tests/`
- `pytest.ini` configured with testpaths, naming conventions
- 4 test files, 36 tests total (all memory-focused)
- Uses temporary directories for isolation
- Mock/patch patterns for testing agents

**Test Files**:
1. `test_memory_manager.py` - MemoryManager unit tests (18 tests)
2. `test_memory_isolation.py` - Project isolation tests (7 tests)  
3. `test_base_agent_memory.py` - BaseAgent memory integration (9 tests)
4. `test_memory_integration.py` - End-to-end memory scenarios (2 tests)

### Source Code Structure
**Core Components** (`src/`):
```
src/
├── orchestrator.py         # Main loop - NO TESTS
├── config.py              # Configuration - NO TESTS
├── agents/
│   ├── base.py           # BaseAgent - Partial coverage (memory only)
│   ├── planner.py        # PlannerAgent - NO TESTS
│   ├── executor.py       # ExecutorAgent - NO TESTS
│   └── reviewer.py       # ReviewerAgent - NO TESTS
├── state/
│   └── manager.py        # StateManager - NO TESTS
└── memory/
    └── manager.py        # MemoryManager - FULL COVERAGE ✓
```

**CLI Tools** (`cli/`): No tests
- `start-agent` - bash script
- `stop-agent` - bash script
- `agent-progress` - bash script
- `fireteam-status` - bash script

### Key Functionality to Test

#### 1. Orchestrator (`src/orchestrator.py`)
Critical untested functionality:
- **Initialization**: Project setup, git repo initialization, memory initialization
- **Cycle execution**: Plan → Execute → Review → Commit loop
- **Completion checking**: Validation logic (3 consecutive >95% checks)
- **Git operations**: Commit creation, branch management, remote pushing
- **Error handling**: Agent failures, retry logic, graceful degradation
- **Signal handling**: SIGINT/SIGTERM graceful shutdown
- **Memory cleanup**: Automatic cleanup on completion

#### 2. State Manager (`src/state/manager.py`)
Critical untested functionality:
- **State persistence**: JSON serialization, file locking
- **Project isolation**: State reset between projects
- **Completion tracking**: Percentage updates, validation counters
- **Parse failure handling**: Fallback to last known completion (novel feature!)
- **Safety mechanisms**: 3 consecutive parse failures → 0%
- **Concurrent access**: File locking for race condition prevention

#### 3. Agent Classes
##### Planner (`src/agents/planner.py`)
- Initial plan creation prompts
- Plan update prompts based on feedback
- Memory context queries (decisions, failed approaches, learnings)
- Plan extraction from Claude output

##### Executor (`src/agents/executor.py`)
- Execution prompt building
- Memory context queries (failed approaches, traces, code locations)
- Result extraction and formatting

##### Reviewer (`src/agents/reviewer.py`)
- Review prompt building (normal vs validation mode)
- Completion percentage extraction (regex parsing)
- Learning extraction (`LEARNING[type]: content` pattern)
- Memory context queries (patterns, decisions, learnings)

##### BaseAgent (`src/agents/base.py`)
Current coverage: Memory integration only
Missing coverage:
- SDK execution with retry logic
- Timeout handling
- Error type detection (CLINotFoundError, etc.)
- Command execution success/failure paths

#### 4. Config (`src/config.py`)
No tests for:
- Environment variable loading
- Default value fallbacks
- API key validation
- Path configuration
- Timeout configuration

## Proposed Changes

### Phase 1: Unit Tests for Core Components

#### 1.1 State Manager Tests (`tests/test_state_manager.py`)
**Intent**: Verify state persistence, isolation, and failure handling

Test categories:
- **Initialization**: Fresh project state, required fields, timestamp generation
- **State Updates**: Single updates, batch updates, timestamp updates
- **Persistence**: File operations, JSON serialization
- **Locking**: Concurrent access prevention, lock acquisition/release
- **Completion Tracking**: 
  - Percentage updates (success path)
  - Parse failure handling (fallback to last known)
  - 3-failure safety valve
  - Validation counter tracking
- **Project Isolation**: State clearing between projects
- **Edge Cases**: Missing state file, corrupted JSON, lock file issues

**Key test scenarios**:
```python
def test_parse_failure_uses_last_known_completion()
def test_three_consecutive_failures_resets_to_zero()
def test_validation_checks_reset_on_percentage_drop()
def test_concurrent_state_access_with_locking()
def test_state_isolation_between_projects()
```

#### 1.2 Planner Agent Tests (`tests/test_planner_agent.py`)
**Intent**: Verify planning prompts and memory integration

Test categories:
- **Prompt Building**: Initial vs update prompts, context inclusion
- **Memory Integration**: Query building, type filtering (decision, failed_approach, learning)
- **Plan Extraction**: Output parsing
- **Error Handling**: SDK failures, retry logic
- **Context Awareness**: Cycle number, previous plan, feedback integration

#### 1.3 Executor Agent Tests (`tests/test_executor_agent.py`)
**Intent**: Verify execution prompts and memory integration

Test categories:
- **Prompt Building**: Goal and plan context
- **Memory Integration**: Query building, type filtering (failed_approach, trace, code_location)
- **Result Extraction**: Output parsing
- **Error Handling**: Implementation failures, partial completions

#### 1.4 Reviewer Agent Tests (`tests/test_reviewer_agent.py`)
**Intent**: Verify review logic, completion extraction, learning extraction

Test categories:
- **Prompt Building**: Normal vs validation mode
- **Completion Extraction**: Regex parsing, format variations, fallbacks
- **Learning Extraction**: `LEARNING[type]: content` pattern matching
- **Memory Integration**: Query building, type filtering (learning, decision, pattern)
- **Validation Mode**: Extra critical prompts, thorough checking
- **Edge Cases**: Missing completion marker, malformed learnings

**Key test scenarios**:
```python
def test_extract_completion_percentage_from_standard_format()
def test_extract_completion_fallback_patterns()
def test_extract_learnings_all_types()
def test_validation_mode_prompt_includes_critical_checks()
```

#### 1.5 BaseAgent Tests (`tests/test_base_agent.py`)
**Intent**: Complete coverage of base agent functionality

Test categories:
- **SDK Execution**: Success/failure paths, output collection
- **Retry Logic**: MAX_RETRIES attempts, exponential backoff
- **Error Handling**: CLINotFoundError, CLIConnectionError, ProcessError
- **Timeout Handling**: Agent-specific timeouts
- **Execute Template**: _do_execute() delegation pattern

#### 1.6 Config Tests (`tests/test_config.py`)
**Intent**: Verify configuration loading and defaults

Test categories:
- **Environment Variables**: Loading, overrides, defaults
- **API Key Handling**: Lazy loading, validation
- **Path Configuration**: System paths, memory dir, state dir
- **Timeout Configuration**: Agent-specific timeouts
- **Model Configuration**: SDK options, model selection

### Phase 2: Integration Tests

#### 2.1 Orchestrator Integration Tests (`tests/test_orchestrator_integration.py`)
**Intent**: Test orchestration flow with mocked agents

Test categories:
- **Initialization**: Git repo setup (new and existing), memory initialization
- **Single Cycle**: Plan → Execute → Review → Commit flow
- **Multi-Cycle**: State accumulation across cycles
- **Completion Logic**: 
  - Validation triggering at >95%
  - 3 consecutive checks required
  - Reset on percentage drop
- **Git Operations**: Commits, branch creation, remote pushing (mocked)
- **Error Recovery**: Agent failures, retries, partial progress
- **Graceful Shutdown**: Signal handling, cleanup
- **Memory Integration**: Memory recording and retrieval through cycle

**Key test scenarios**:
```python
def test_single_cycle_execution()
def test_completion_requires_three_consecutive_validations()
def test_git_commit_after_each_cycle()
def test_memory_cleanup_on_completion()
def test_graceful_shutdown_on_signal()
def test_agent_failure_with_retry()
```

#### 2.2 Full System Integration Tests (`tests/test_system_integration.py`)
**Intent**: End-to-end system tests with realistic scenarios

Test categories:
- **Complete Project Lifecycle**: Start → Multiple cycles → Completion
- **State Persistence**: State survives crashes (test with state file manipulation)
- **Memory Accumulation**: Memories persist and are retrieved correctly
- **Git Integration**: Real git operations in temp repo
- **Error Scenarios**: 
  - Network failures (mocked SDK errors)
  - Disk full (mocked file operations)
  - Corrupted state recovery
- **Performance**: Cycle timing, memory search performance

**Key test scenarios**:
```python
def test_complete_project_lifecycle_with_mocked_agents()
def test_state_recovery_after_interruption()
def test_memory_grows_and_retrieves_across_cycles()
```

### Phase 3: CLI and End-to-End Tests

#### 3.1 CLI Tests (`tests/test_cli.py`)
**Intent**: Test CLI utilities work correctly

Test categories:
- **start-agent**: Argument parsing, orchestrator launch, PID management
- **stop-agent**: Graceful shutdown, cleanup
- **agent-progress**: Status display, state reading
- **Error Cases**: Invalid arguments, missing dependencies, already running

**Approach**: Use subprocess to test CLI commands in isolated environment

### Phase 4: CI/CD Integration

#### 4.1 GitHub Actions Workflow (`.github/workflows/test.yml`)
**Intent**: Automated testing on push/PR

Workflow features:
- **Python 3.12+** requirement (per WARP.md)
- **Matrix Testing**: Test on multiple Python versions (3.12, 3.13)
- **Dependency Installation**: Use `uv` (per WARP.md)
- **Test Execution**: Run full test suite with coverage
- **Coverage Reporting**: Generate and upload coverage reports
- **Secrets Management**: Add ANTHROPIC_API_KEY as GitHub secret
- **Test Isolation**: Each test job gets fresh environment

**Key configuration**:
```yaml
- Python 3.12+ (required by claude-agent-sdk>=0.1.4)
- Install with: uv pip install -r requirements.txt
- Run: pytest tests/ -v --cov=src --cov-report=term-missing
- Secrets: ANTHROPIC_API_KEY (for integration tests)
```

#### 4.2 Test Coverage Goals
- **Target**: 80%+ overall coverage
- **Critical paths**: 100% coverage (orchestration loop, state management)
- **Memory system**: Already at ~100%
- **CI Enforcement**: Fail on coverage drops

## Test Organization

### Directory Structure
```
tests/
├── pytest.ini                          # Existing
├── conftest.py                         # NEW - Shared fixtures
├── unit/                               # NEW - Unit tests
│   ├── test_state_manager.py          # NEW
│   ├── test_config.py                 # NEW
│   ├── test_base_agent.py             # NEW
│   ├── test_planner_agent.py          # NEW
│   ├── test_executor_agent.py         # NEW
│   └── test_reviewer_agent.py         # NEW
├── integration/                        # NEW - Integration tests
│   ├── test_orchestrator_integration.py    # NEW
│   └── test_system_integration.py          # NEW
├── cli/                                # NEW - CLI tests
│   └── test_cli.py                     # NEW
└── memory/                             # NEW - Move existing memory tests
    ├── test_memory_manager.py          # MOVED from tests/
    ├── test_memory_isolation.py        # MOVED from tests/
    ├── test_base_agent_memory.py       # MOVED from tests/
    └── test_memory_integration.py      # MOVED from tests/
```

### Shared Test Fixtures (`tests/conftest.py`)
**Purpose**: DRY principle, shared test utilities

Common fixtures:
- `temp_project_dir`: Temporary directory with git initialization
- `mock_claude_sdk`: Mock Claude SDK for agent testing
- `sample_state`: Pre-populated state for testing
- `memory_manager_fixture`: Configured memory manager
- `mock_git_commands`: Mock git subprocess calls

## Test Execution Strategy

### Development Workflow
1. **Fast feedback**: `pytest tests/unit/ -v` (unit tests only, fast)
2. **Integration**: `pytest tests/integration/ -v` (slower, mocked SDK)
3. **Full suite**: `pytest tests/ -v --cov=src` (all tests + coverage)

### CI Pipeline
1. **Unit tests**: Always run, fast feedback
2. **Integration tests**: Run with mocked SDK
3. **System tests**: Run with mocked SDK, test lifecycle
4. **Coverage check**: Enforce 80%+ threshold

### Test Markers
Use pytest markers for selective testing:
```python
@pytest.mark.unit           # Fast unit tests
@pytest.mark.integration    # Integration tests (slower)
@pytest.mark.slow           # Very slow tests (full system)
@pytest.mark.requires_api   # Requires ANTHROPIC_API_KEY
```

Run examples:
```bash
pytest -m unit                # Fast unit tests only
pytest -m "not slow"          # Skip slow tests
pytest -m requires_api        # Only tests needing API
```

## Dependencies

### New Test Dependencies
Add to `requirements.txt`:
```
# Testing - existing
pytest>=7.0.0

# Testing - NEW
pytest-cov>=4.1.0           # Coverage reporting
pytest-asyncio>=0.23.0      # Async test support
pytest-timeout>=2.2.0       # Timeout handling
pytest-mock>=3.12.0         # Enhanced mocking
```

## Success Criteria

1. ✅ **Coverage**: 80%+ overall, 100% for critical paths
2. ✅ **All components tested**: Orchestrator, StateManager, all agents, config
3. ✅ **Integration tests**: Full cycle execution, state persistence, memory integration
4. ✅ **CI/CD**: GitHub Actions running all tests automatically
5. ✅ **Test quality**: Tests verify intent/behavior, not just code coverage
6. ✅ **Maintainability**: Clear test organization, shared fixtures, good naming
7. ✅ **Documentation**: Each test has clear docstring explaining intent

## Implementation Order

1. **Phase 1a**: State Manager tests (foundation for everything)
2. **Phase 1b**: Config tests (needed for other components)
3. **Phase 1c**: BaseAgent tests (extended coverage)
4. **Phase 1d**: Individual agent tests (Planner, Executor, Reviewer)
5. **Phase 2a**: Orchestrator integration tests
6. **Phase 2b**: System integration tests
7. **Phase 3**: CLI tests (if time permits)
8. **Phase 4**: CI/CD setup and integration

## Notes

- **Memory tests are excellent**: Use them as a template for quality
- **Mock the SDK**: Don't make real API calls in tests (expensive, slow)
- **Test intent, not implementation**: Tests should survive refactoring
- **Isolation**: Each test should be independent, use temp directories
- **ANTHROPIC_API_KEY**: Will be GitHub secret for CI
- **uv requirement**: Per WARP.md, use `uv` for dependency installation
- **Python 3.12+**: Required by claude-agent-sdk>=0.1.4 per WARP.md
