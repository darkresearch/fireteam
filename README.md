# Claude Agent System

An autonomous multi-agent system for long-running project execution powered by Claude.

## Overview

The Claude Agent System is a sophisticated orchestration framework that manages three specialized agents in an infinite cycle of planning, execution, and review until project completion:

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
- **Git Integration**: Automatic repo initialization, branching, commits, and pushing
- **State Isolation**: Clean state separation between projects to prevent contamination
- **Completion Validation**: Triple-check validation system (3 consecutive >95% reviews)
- **Error Recovery**: Automatic retry logic and graceful degradation
- **Production Focus**: Emphasis on production-ready code with comprehensive testing

## Installation

1. **Prerequisites**
   - Python 3.7+
   - Git
   - Claude CLI ([installation guide](https://docs.claude.com/en/docs/claude-code/installation))

2. **Setup**
   ```bash
   cd /home/claude/claude-agent-system
   bash setup.sh
   source ~/.bashrc  # or restart your shell
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

State is stored in `state/current.json` and includes:

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

## Configuration

Edit `config.py` to customize:

- `MAX_RETRIES`: Number of retry attempts for failed agent calls (default: 3)
- `COMPLETION_THRESHOLD`: Percentage to trigger validation (default: 95)
- `VALIDATION_CHECKS_REQUIRED`: Consecutive checks needed (default: 3)
- `LOG_LEVEL`: Logging verbosity (default: INFO)

## Logging

Logs are stored in `logs/`:

- `orchestrator_YYYYMMDD_HHMMSS.log`: Per-run orchestrator logs
- `system.log`: Combined system output (when running in background)

## Project Structure

```
claude-agent-system/
├── orchestrator.py         # Main orchestration loop
├── config.py              # Configuration settings
├── agents/
│   ├── __init__.py
│   ├── base.py           # Base agent class
│   ├── planner.py        # Planner agent
│   ├── executor.py       # Executor agent
│   └── reviewer.py       # Reviewer agent
├── state/
│   ├── manager.py        # State management
│   └── current.json      # Active state (gitignored)
├── cli/
│   ├── start-agent       # Start system
│   ├── stop-agent        # Stop system
│   └── agent-progress    # Check status
├── logs/                 # Log directory
├── service/
│   └── claude-agent.service  # Systemd service file
├── setup.sh              # Installation script
└── README.md            # This file
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
