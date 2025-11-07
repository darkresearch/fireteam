# Fireteam

[![Tests](https://github.com/darkresearch/fireteam/actions/workflows/test.yml/badge.svg)](https://github.com/darkresearch/fireteam/actions/workflows/test.yml)

An autonomous multi-agent system for long-running project execution powered by Claude.

## Overview

The Fireteam is a sophisticated orchestration framework that manages three specialized agents in an infinite cycle of planning, execution, and review until project completion:

- **Planner Agent**: Creates and updates project plans
- **Executor Agent**: Executes planned tasks
- **Reviewer Agent**: Assesses progress and estimates completion

## Architecture

```
Orchestrator (Infinite Loop)
    ↓
[Plan] → [Execute] → [Review] → [Git Commit]
    ↑___________________________________|
```

### Key Features

- **Autonomous Operation**: Runs continuously until project completion
- **Memory System**: Local vector-based memory with semantic search for learning from past cycles
- **Git Integration**: Automatic repo initialization, branching, commits, and pushing
- **State Isolation**: Clean state separation between projects to prevent contamination
- **Completion Validation**: Triple-check validation system (3 consecutive >95% reviews)
- **Error Recovery**: Automatic retry logic and graceful degradation
- **Production Focus**: Emphasis on production-ready code with comprehensive testing
- **Comprehensive Testing**: 165 tests with CI/CD pipeline ensuring reliability

## Installation

1. **Prerequisites**
   - Python 3.12+
   - Git
   - Anthropic API key

2. **Setup**
   ```bash
   # Clone repository
   git clone https://github.com/darkresearch/fireteam
   cd fireteam
   
   # Run setup script
   bash setup.sh
   source ~/.bashrc  # or restart your shell
   
   # Set API key
   export ANTHROPIC_API_KEY="your-key-here"
   # Or add to .env file
   echo "ANTHROPIC_API_KEY=your-key-here" > .env
   ```

3. **Verify Installation**
   ```bash
   # Check Python version
   python3.12 --version
   
   # Run tests (optional)
   pytest tests/ -m "not slow and not e2e and not integration" -v
   ```

## Usage

### Starting a Project

```bash
start-agent --project-dir /path/to/project --prompt "Your project goal here"
```

Example:
```bash
start-agent --project-dir ~/my-calculator --prompt "Build a Python command-line calculator with support for basic arithmetic operations"
```

### Checking Progress

```bash
agent-progress
```

This shows:
- Current status (running/stopped)
- Project information
- Current cycle number
- Completion percentage
- Recent activity logs

### Stopping the System

```bash
stop-agent
```

This gracefully shuts down the orchestrator and all running agents.

## How It Works

### Initialization

1. Creates/validates Git repository in project directory
2. Creates timestamped branch (e.g., `agent-20240315-143022`)
3. Initializes clean project state

### Cycle Execution

Each cycle consists of three phases:

1. **Planning Phase**
   - Planner agent reviews goal, previous plan, and recent results
   - Creates or updates project plan
   - Breaks down remaining work into actionable tasks

2. **Execution Phase**
   - Executor agent implements tasks from the plan
   - Writes actual, working code (no placeholders)
   - Tests implementations
   - Documents work

3. **Review Phase**
   - Reviewer agent examines the codebase
   - Tests functionality
   - Estimates completion percentage (0-100%)
   - Identifies gaps or issues

4. **Git Commit**
   - Commits all changes with descriptive message
   - Pushes to remote if origin exists

### Completion Logic

- System runs infinite cycles until completion
- When Reviewer estimates >95% complete: enter validation mode
- Validation requires 3 consecutive reviews confirming >95%
- Each validation review takes a fresh, critical look
- Upon completion: system stops and logs success

## State Management

State is stored in `state/current.json` (runtime data directory) and includes:

- `project_dir`: Absolute path to project
- `goal`: Project objective
- `status`: Current phase (planning/executing/reviewing)
- `cycle_number`: Current cycle count
- `completion_percentage`: Latest estimate (0-100)
- `validation_checks`: Consecutive validation passes
- `git_branch`: Current branch name
- `current_plan`: Latest plan
- `last_execution_result`: Latest execution output
- `last_review`: Latest review output

**Important**: State is completely reset between projects to prevent cross-contamination.

## Memory System

Fireteam includes an OB-1-inspired memory system that enables agents to learn from past experiences and avoid repeating mistakes.

### How It Works

- **Automatic Retrieval**: Memories are automatically injected into agent context each cycle
- **Semantic Search**: Uses local vector embeddings (Qwen3-Embedding-0.6B) for relevant memory retrieval
- **Project Isolation**: Each project has its own memory collection - no cross-contamination
- **Learning Types**: Tracks traces, failed approaches, decisions, learnings, and code locations
- **Automatic Cleanup**: Memory is cleaned up on project completion (unless `--keep-memory` flag is used)

### Memory Storage

```
memory/
  {project_hash}/           # MD5 hash of project_dir
    chroma_db/              # Vector database (persistent)
```

### Performance

- **First run**: Downloads ~1.2GB embedding model (cached for subsequent runs)
- **Per cycle overhead**: ~3 seconds for memory retrieval
- **Storage**: Grows with project size, auto-cleaned on completion

Read more in the [memory system documentation](docs/advanced/memory-system.mdx).

## Configuration

Configuration is managed via `src/config.py` and environment variables:

### Core Settings

- `MAX_RETRIES`: Number of retry attempts for failed agent calls (default: 3)
- `COMPLETION_THRESHOLD`: Percentage to trigger validation (default: 95)
- `VALIDATION_CHECKS_REQUIRED`: Consecutive checks needed (default: 3)
- `LOG_LEVEL`: Logging verbosity (default: INFO)

### Agent Timeouts

Configure via environment variables or `src/config.py`:
- `FIRETEAM_AGENT_TIMEOUT_PLANNER`: Planner timeout in seconds (default: 600)
- `FIRETEAM_AGENT_TIMEOUT_EXECUTOR`: Executor timeout in seconds (default: 1800)
- `FIRETEAM_AGENT_TIMEOUT_REVIEWER`: Reviewer timeout in seconds (default: 600)

### Memory System

- `MEMORY_EMBEDDING_MODEL`: Embedding model (default: "Qwen/Qwen3-Embedding-0.6B")
- `MEMORY_SEARCH_LIMIT`: Number of memories to retrieve (default: 10)

### Environment Variables

Create a `.env` file in the repository root:
```bash
# Required
ANTHROPIC_API_KEY=your-key-here

# Optional
ANTHROPIC_MODEL=claude-sonnet-4-5-20250929
FIRETEAM_LOG_LEVEL=INFO
GIT_USER_NAME=fireteam
GIT_USER_EMAIL=fireteam@darkresearch.ai
```

## Logging

Logs are stored in `logs/`:

- `orchestrator_YYYYMMDD_HHMMSS.log`: Per-run orchestrator logs
- `system.log`: Combined system output (when running in background)

## Project Structure

```
fireteam/
├── src/                    # Source code directory
│   ├── orchestrator.py    # Main orchestration loop
│   ├── config.py          # Configuration settings
│   ├── __init__.py
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base.py        # Base agent class with memory integration
│   │   ├── planner.py     # Planner agent
│   │   ├── executor.py    # Executor agent
│   │   └── reviewer.py    # Reviewer agent
│   ├── state/
│   │   ├── __init__.py
│   │   └── manager.py     # State management module
│   └── memory/
│       ├── __init__.py
│       └── manager.py     # Memory system with embeddings
├── benchmark/              # Terminal-bench adapter
│   ├── adapters/
│   │   ├── fireteam_adapter.py
│   │   └── fireteam-setup.sh
│   ├── README.md
│   └── USAGE.md
├── tests/                  # Comprehensive test suite (165 tests)
│   ├── pytest.ini
│   ├── conftest.py
│   ├── helpers.py
│   ├── test_*.py          # Unit tests
│   └── README.md
├── docs/                   # Mintlify documentation
│   ├── mint.json
│   └── *.mdx              # Documentation pages
├── cli/
│   ├── start-agent        # Start system
│   ├── stop-agent         # Stop system
│   ├── agent-progress     # Check progress
│   └── fireteam-status    # Detailed status
├── .github/
│   └── workflows/
│       └── test.yml       # CI/CD pipeline
├── state/                 # Runtime state data (gitignored)
│   └── current.json       # Active project state
├── memory/                # Memory storage (gitignored)
│   └── {project_hash}/    # Per-project vector database
├── logs/                  # Log directory
├── setup.sh               # Installation script
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## Troubleshooting

### System won't start

- Check Claude CLI is installed: `claude --version`
- Ensure project directory is accessible
- Check logs in `logs/system.log`

### Agents failing repeatedly

- Check Claude CLI credentials
- Verify network connectivity
- Review agent logs for specific errors
- Ensure sufficient disk space

### State corruption

- Stop the system: `stop-agent`
- Remove state file: `rm state/current.json`
- Restart with fresh state

### Git issues

- Ensure git is configured: `git config --list`
- Check remote access: `git remote -v` (in project dir)
- Verify credentials for pushing

### Memory issues

- First run downloads ~1.2GB model - be patient
- Check logs for `[MEMORY]` prefixed messages
- Memory is auto-cleaned on completion

## Testing

Fireteam has a comprehensive test suite with 165 tests covering all components.

### Running Tests

```bash
# Fast tests only (recommended for development)
pytest tests/ -m "not slow and not e2e and not integration" -v

# All tests including E2E (requires API key, ~$1-2 cost)
pytest tests/ -v

# Specific test categories
pytest tests/test_agents.py -v      # Agent tests
pytest tests/test_memory_*.py -v    # Memory system tests
pytest tests/test_orchestrator.py -v # Orchestrator tests
```

### Test Categories

- **Unit Tests (161 tests)**: Fast, no API calls required
  - Configuration (15 tests)
  - State Manager (20 tests)
  - Agents (38 tests)
  - Orchestrator (28 tests)
  - CLI Tools (24 tests)
  - Memory System (36 tests)

- **E2E Tests (2 tests)**: Real task completion with API calls
- **Integration Tests (2 tests)**: Terminal-bench integration

### CI/CD Pipeline

GitHub Actions workflow runs:
- Fast tests on all PRs (~2 minutes, free)
- E2E tests on main branch only (~15 minutes, costs ~$1-2)

See [tests/README.md](tests/README.md) for detailed testing documentation.

## Best Practices

1. **Clear Goals**: Provide specific, detailed project goals
2. **Monitor Progress**: Check `agent-progress` periodically
3. **Review Commits**: Examine git commits to understand changes
4. **Iterate on Plans**: Let the system adapt through multiple cycles
5. **Trust Validation**: The triple-check ensures quality

## Advanced Usage

### Multiple Projects

Each project maintains isolated state. To work on multiple projects:

```bash
# Start project 1
start-agent --project-dir ~/project1 --prompt "Goal 1"

# Wait for completion or stop
stop-agent

# Start project 2 (completely fresh state)
start-agent --project-dir ~/project2 --prompt "Goal 2"
```

### Custom Branch Names

The system automatically creates timestamped branches. To continue from a specific commit:

1. Manually checkout desired branch in project directory
2. System will create new branch from that point

### Remote Repositories

To push to a remote:

```bash
cd /path/to/project
git remote add origin <url>
# System will automatically push subsequent commits
```

## Technical Details

### Agent Communication

Agents don't communicate directly. The orchestrator:
- Passes outputs as inputs to the next agent
- Maintains state in shared state file
- Ensures proper sequencing

### Claude CLI Integration

Agents invoke Claude CLI with:
```bash
claude --dangerously-skip-permissions --prompt "<prompt>" --cwd <project-dir>
```

The `--dangerously-skip-permissions` flag enables fully autonomous operation.

### Error Handling

- Each agent call has retry logic (3 attempts by default)
- Exponential backoff between retries
- Graceful degradation on persistent failures
- Comprehensive logging for debugging

## Contributing

This is a production system. Contributions should:
- Follow Python best practices (PEP 8)
- Include error handling
- Update documentation
- Maintain backward compatibility

## License

MIT License - See LICENSE file for details

## Support

- Documentation: [Claude Code Docs](https://docs.claude.com/en/docs/claude-code)
- Issues: Report via project repository
- Sub-agents: [Sub-agent Documentation](https://docs.claude.com/en/docs/claude-code/sub-agents)

## Version

1.0.0 - Initial release
