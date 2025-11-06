# Fireteam Terminal-Bench Adapter - Detailed Usage

## Setup

### Prerequisites

- Python 3.12+
- Docker
- uv (Python package manager)
- Anthropic API key

### Installation

1. Install uv if not already installed:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. Install terminal-bench:
   ```bash
   uv tool install terminal-bench
   ```

3. Set up the adapter:
   ```bash
   cd benchmark
   uv pip install -e .
   ```

4. Set your API key:
   ```bash
   export ANTHROPIC_API_KEY="your-anthropic-api-key"
   ```

## Running Tasks

### Single Task

Run a specific task by ID:

```bash
tb run \
  --agent-import-path benchmark.adapters.fireteam_adapter:FireteamAdapter \
  --dataset terminal-bench-core \
  --task-id <task-id> \
  --global-agent-timeout-sec 600 \
  --log-level info
```

### Multiple Tasks

Run all tasks in a dataset:

```bash
tb run \
  --agent-import-path benchmark.adapters.fireteam_adapter:FireteamAdapter \
  --dataset terminal-bench-core \
  --global-agent-timeout-sec 1200
```

Run specific tasks by pattern:

```bash
tb run \
  --agent-import-path benchmark.adapters.fireteam_adapter:FireteamAdapter \
  --dataset terminal-bench-core \
  --task-id "python-*" \
  --global-agent-timeout-sec 600
```

### Timeout Configuration

Control how long tasks can run:

```bash
# Short timeout (10 minutes)
--global-agent-timeout-sec 600

# Long timeout (30 minutes)
--global-agent-timeout-sec 1800

# Very long timeout (1 hour)
--global-agent-timeout-sec 3600
```

**Note**: Terminal-bench handles timeouts - no need to configure Fireteam's orchestrator timeout.

### Customizing the Model

Use a different Claude model:

```bash
export ANTHROPIC_MODEL="claude-opus-4-20250514"

tb run \
  --agent-import-path benchmark.adapters.fireteam_adapter:FireteamAdapter \
  --task-id <task-id>
```

## Monitoring

### Real-time Logs

Terminal-bench displays Fireteam's output in real-time. You'll see:
- **Cycle numbers**: Track Fireteam's progress through planning/execution/review cycles
- **Planning phase**: What the planner agent decides to do
- **Execution phase**: What the executor agent implements
- **Review phase**: Completion percentage and quality assessment
- **Git commits**: Automatic commits after each cycle

Example output:
```
================================================================================
CYCLE 1 - Starting
================================================================================

PHASE 1: Planning
Planning completed

PHASE 2: Execution
Execution completed

PHASE 3: Review
Review completed - Completion: 45%
Committed changes: Cycle 1: 45% complete
```

### Output Location

Results are saved to:
- `runs/<timestamp>/` - Terminal-bench run directory
  - `results.json` - Task results and metrics
  - `logs/` - Task logs and asciinema recordings
  - Per-task subdirectories with detailed logs

## Interpreting Results

### Success ✅
Task completed within timeout with all tests passing. Fireteam reached 95%+ completion with triple validation.

### Timeout ⏱️
Fireteam exceeded the `--global-agent-timeout-sec` limit. Check logs to see progress made. You may need to increase the timeout for complex tasks.

### Failure ❌
Task failed tests. Review logs to understand what went wrong:
- Did Fireteam misunderstand the task?
- Were there technical errors?
- Did it run out of time before completing?

## Troubleshooting

### "ANTHROPIC_API_KEY not set"

```bash
export ANTHROPIC_API_KEY="your-key"
```

Make sure to set this before running terminal-bench.

### "Agent installation failed"

Check that `fireteam-setup.sh` is executable:

```bash
chmod +x benchmark/adapters/fireteam-setup.sh
```

Also verify that the script can install dependencies. You can test this manually in a container.

### "Git errors"

Fireteam handles existing repos (from Phase 1 refactoring). If issues persist:
- Check that git is installed in the container
- Verify git user.name and user.email are configured
- Review container logs for detailed error messages

### Container not stopping

Terminal-bench handles cleanup, but you can manually stop containers:

```bash
docker ps | grep terminal-bench
docker stop <container-id>
```

### Import errors

If you see "No module named 'terminal_bench'", make sure you've installed the adapter:

```bash
cd benchmark
uv pip install -e .
```

## Advanced Usage

### Local Development

Test adapter changes without running full terminal-bench:

```bash
cd benchmark
python test_adapter.py
```

This validates:
- Agent name is correct
- Environment variables are set properly
- Install script exists and is executable
- Command generation works

### Custom Datasets

Point to local dataset directory:

```bash
tb run \
  --agent-import-path benchmark.adapters.fireteam_adapter:FireteamAdapter \
  --dataset-path /path/to/custom/tasks
```

### Parallel Execution

Run multiple tasks concurrently:

```bash
tb run \
  --agent-import-path benchmark.adapters.fireteam_adapter:FireteamAdapter \
  --dataset terminal-bench-core \
  --n-concurrent 4
```

**Note**: This runs 4 tasks in parallel. Adjust based on your machine's resources.

### Skip Rebuilds

Speed up repeated runs by skipping container rebuilds:

```bash
tb run \
  --agent-import-path benchmark.adapters.fireteam_adapter:FireteamAdapter \
  --task-id <task-id> \
  --no-rebuild
```

### Livestream Output

See output in real-time as tasks execute:

```bash
tb run \
  --agent-import-path benchmark.adapters.fireteam_adapter:FireteamAdapter \
  --task-id <task-id> \
  --livestream
```

## Performance Tips

1. **Start with simple tasks**: Test with easy tasks first to validate setup
2. **Adjust timeouts**: Complex tasks may need 30-60 minutes
3. **Monitor resource usage**: Fireteam runs multiple agents, so ensure adequate CPU/memory
4. **Use parallel execution wisely**: Too many parallel tasks can overwhelm your system
5. **Review logs regularly**: Understand how Fireteam approaches tasks

## Understanding Fireteam's Behavior

### Multi-Cycle Approach

Fireteam doesn't solve tasks in one shot. It iteratively:
1. **Plans** what to do next
2. **Executes** the plan
3. **Reviews** progress and estimates completion

This continues until 95%+ completion with triple validation.

### Why Multiple Cycles?

- **Complex tasks** need iterative refinement
- **Self-correction** happens during review phase
- **Quality validation** ensures production-ready code

### Typical Cycle Count

- Simple tasks: 3-5 cycles
- Medium tasks: 5-10 cycles
- Complex tasks: 10-20 cycles

## Contributing

To improve the adapter:

1. Make changes to `adapters/fireteam_adapter.py`
2. Test locally with `python test_adapter.py`
3. Run a simple task to verify:
   ```bash
   tb run --agent-import-path benchmark.adapters.fireteam_adapter:FireteamAdapter --task-id simple-task
   ```
4. Submit a PR with your changes

## Support

- **Fireteam issues**: [GitHub Issues](https://github.com/your-org/fireteam/issues)
- **Terminal-bench docs**: https://www.tbench.ai/docs
- **Integration plan**: See [TERMINAL_BENCH_ADAPTER_PLAN.md](../TERMINAL_BENCH_ADAPTER_PLAN.md)

## Examples

### Example 1: Simple Task

```bash
export ANTHROPIC_API_KEY="sk-ant-..."

tb run \
  --agent-import-path benchmark.adapters.fireteam_adapter:FireteamAdapter \
  --dataset terminal-bench-core \
  --task-id hello-world \
  --global-agent-timeout-sec 300
```

### Example 2: Complex Task with Long Timeout

```bash
tb run \
  --agent-import-path benchmark.adapters.fireteam_adapter:FireteamAdapter \
  --dataset terminal-bench-core \
  --task-id build-complex-app \
  --global-agent-timeout-sec 3600
```

### Example 3: Run Multiple Tasks

```bash
tb run \
  --agent-import-path benchmark.adapters.fireteam_adapter:FireteamAdapter \
  --dataset terminal-bench-core \
  --task-id "python-*" \
  --n-concurrent 2 \
  --global-agent-timeout-sec 1200
```

### Example 4: Debug Mode

```bash
tb run \
  --agent-import-path benchmark.adapters.fireteam_adapter:FireteamAdapter \
  --task-id <task-id> \
  --log-level debug \
  --livestream
```

