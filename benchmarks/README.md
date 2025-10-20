# Fireteam Benchmarking

This directory contains infrastructure for benchmarking Fireteam against industry-standard coding benchmarks.

## Current Benchmarks

### Terminal Bench

Terminal Bench is the industry-standard benchmark for evaluating AI coding agents on real-world terminal tasks. It tests agents on 80 diverse tasks including:
- System administration
- Machine learning workflows
- Build and compilation
- Security tasks
- Networking configuration

**Key Differentiator:** Fireteam runs with a **48-hour timeout per task**, enabling our perpetual execution model to fully iterate toward completion rather than stopping prematurely like shorter-timeout systems.

**Location:** `terminal_bench/`
**Documentation:** See `terminal_bench/TERMINAL_BENCH_PLAN.md` for complete details

## Architecture

**Important:** Understand where each component runs:

```
┌─────────────────────────────────────────────────────────────┐
│ HOST MACHINE (your laptop/server)                          │
│                                                             │
│  • terminal-bench CLI installed (via uv)                   │
│  • You run: tb run --agent fireteam ...                    │
│  • Orchestrates Docker containers                          │
│  • Collects results                                        │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ DOCKER CONTAINER (one per task, auto-created by TB) │  │
│  │                                                      │  │
│  │  • Task environment (from Terminal Bench)           │  │
│  │  • Fireteam installed via install_fireteam.sh       │  │
│  │  • Fireteam orchestrator runs inside here           │  │
│  │  • Claude Code runs as fireteam-user with sudo      │  │
│  │  • Solves task, TB collects results                 │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

**Summary:**
- **Host:** Install `terminal-bench` with UV
- **Container:** Fireteam gets installed automatically by Terminal Bench
- **You only interact with the host** - Docker is handled for you

## Quick Start

### Prerequisites

```bash
# Docker (required by Terminal Bench)
docker --version

# Python 3.12+
python3 --version

# Anthropic API key
export ANTHROPIC_API_KEY="your-key-here"
```

### Installation

```bash
# Install UV if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add UV to PATH (if needed)
export PATH="$HOME/.local/bin:$PATH"

# Install Terminal Bench and dependencies (on host machine)
cd benchmarks/terminal_bench
uv sync

# Activate the virtual environment
source .venv/bin/activate

# Verify Terminal Bench CLI works
tb --help

# Verify Fireteam agent loads correctly
python3 -c "
from fireteam_agent import FireteamAgent
agent = FireteamAgent()
print(f'✓ Agent name: {agent.name()}')
print(f'✓ Install script: {agent._install_agent_script_path}')
"
```

**Note:** Terminal Bench runs on your host machine and orchestrates Docker containers. Fireteam gets installed inside the Docker containers automatically via `install_fireteam.sh`.

### Running a Test

```bash
# Make sure you're in the venv and have ANTHROPIC_API_KEY set
cd benchmarks/terminal_bench
source .venv/bin/activate
export ANTHROPIC_API_KEY="your-key-here"

# Run full benchmark (takes ~2-3 weeks with 48hr timeout)
python run_benchmark.py
```

### Monitoring Progress

Since Terminal Bench runs can take weeks with our 48-hour timeout, we provide real-time progress monitoring:

```bash
# Watch progress in real-time
python monitor_progress.py --watch

# Get current summary
python monitor_progress.py --summary

# Check individual task logs
ls reports/in_progress/task_logs/
```

## Results

Benchmark results are saved to `terminal_bench/reports/` with:
- Timestamped final reports: `YYYY-MM-DD_vX.X.X/`
- Live progress during runs: `in_progress/`

See `terminal_bench/reports/` for all results.

## Configuration

Edit `terminal_bench/config.yaml` to customize:
- Task timeout (default: 48 hours)
- Concurrency (default: 1 task at a time)
- Fireteam version to test
- Reporting options

## Documentation

- **Terminal Bench Plan:** `terminal_bench/TERMINAL_BENCH_PLAN.md`
- **Terminal Bench Docs:** https://www.tbench.ai/docs
- **Terminal Bench GitHub:** https://github.com/laude-institute/terminal-bench

## Current Status

**Phase 1: Basic Integration** - In Progress
- [x] Directory structure created
- [x] Agent adapter implemented
- [x] Installation script created
- [ ] Tested on sample tasks
- [ ] Verified full orchestrator capabilities

See `terminal_bench/TERMINAL_BENCH_PLAN.md` for detailed roadmap.

## Contributing

When adding new benchmarks:
1. Create subdirectory (e.g., `new_benchmark/`)
2. Follow Terminal Bench structure pattern
3. Document in this README
4. Add integration tests

## Notes

- **Long runtime:** With 48-hour timeouts, expect 2-3 weeks for full Terminal Bench run
- **Progressive reporting:** Check `reports/in_progress/` for results as tasks complete
- **Cost management:** Start with `concurrency: 1` in config.yaml
- **Permissions:** Fireteam runs as `fireteam-user` (not root) with sudo access

---

For questions or issues, see the main Fireteam documentation or file an issue.
