# Fireteam Terminal-Bench Adapter

Adapter to run [Fireteam](../README.md) on [terminal-bench](https://www.tbench.ai/) tasks.

## Quick Start

### Installation

From the fireteam repository root:

```bash
# Install terminal-bench
uv tool install terminal-bench

# Install adapter dependencies
cd benchmark
uv pip install -e .
```

### Running a Task

```bash
export ANTHROPIC_API_KEY="your-key-here"

tb run \
  --agent-import-path benchmark.adapters.fireteam_adapter:FireteamAdapter \
  --dataset terminal-bench-core \
  --task-id hello-world \
  --global-agent-timeout-sec 600
```

### Local Testing

```bash
cd benchmark
python test_adapter.py
```

## How It Works

1. Terminal-bench creates a Docker container with the task environment
2. Fireteam code is copied to `/fireteam` in the container
3. Dependencies are installed via `fireteam-setup.sh` (using `uv`)
4. Orchestrator runs with `/app` as the project directory
5. State and logs are stored in `/app/state` and `/app/logs`
6. Fireteam runs planning → execution → review cycles until complete or timeout

## Architecture

```
Terminal-Bench Container
┌─────────────────────────────────────┐
│ /app (task working directory)       │
│   ├─ git repo (existing)            │
│   ├─ task files                     │
│   ├─ state/ (Fireteam state)        │
│   └─ logs/ (Fireteam logs)          │
│                                      │
│ /fireteam (installed agent)         │
│   ├─ orchestrator.py                │
│   ├─ agents/                        │
│   ├─ state/                         │
│   └─ config.py                      │
└─────────────────────────────────────┘
```

## Key Features

- **Existing Repository Support**: Works with terminal-bench's pre-initialized git repos
- **Timeout Handling**: Terminal-bench manages timeouts via `--global-agent-timeout-sec`
- **Real-time Logging**: Fireteam's cycle output streams to terminal-bench logs
- **State Isolation**: Each task gets isolated state in `/app/state`
- **UV Package Management**: Consistent with Fireteam's package management approach

## See Also

- [USAGE.md](USAGE.md) - Detailed usage guide
- [Terminal-Bench Docs](https://www.tbench.ai/docs)
- [Fireteam Main README](../README.md)
- [Integration Plan](../TERMINAL_BENCH_ADAPTER_PLAN.md)

## Troubleshooting

### "ANTHROPIC_API_KEY not set"

```bash
export ANTHROPIC_API_KEY="your-key"
```

### "Agent installation failed"

Check that `fireteam-setup.sh` is executable and has the correct dependencies.

### Test locally first

Always run `python test_adapter.py` to validate the adapter before running terminal-bench tasks.

