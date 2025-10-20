# Terminal Bench Integration Plan

**Status:** Phase 1 - Planning Complete
**Last Updated:** 2025-01-19
**Target Completion:** Phase 1 by end of January 2025

---

## Overview

Integrate Terminal Bench testing infrastructure to regularly benchmark Fireteam against industry standards (Claude Code, Factory Droids, etc.). This will be a permanent part of the repo with automation for running benchmarks and generating reports.

**Key Differentiator:** We're testing Fireteam's perpetual execution model with **48-hour task timeouts**, allowing the multi-cycle validation system to work on complex tasks that other agents might give up on.

---

## Directory Structure

```
fireteam/
├── benchmarks/                          # New directory
│   ├── terminal_bench/
│   │   ├── __init__.py
│   │   ├── fireteam_agent.py           # AbstractInstalledAgent implementation
│   │   ├── install_fireteam.sh         # Installation script for TB container
│   │   ├── run_benchmark.py            # Orchestration script to run benchmarks
│   │   ├── analyze_results.py          # Result parsing and report generation
│   │   ├── monitor_progress.py         # Real-time progress monitoring
│   │   ├── config.yaml                 # Benchmark configuration
│   │   └── reports/                    # Generated reports
│   │       ├── .gitkeep
│   │       ├── in_progress/            # Live results during run
│   │       │   ├── current_summary.md
│   │       │   └── completed_tasks.json
│   │       └── YYYY-MM-DD_vX.X.X/      # Final date-stamped reports
│   │           ├── summary.md          # Human-readable summary
│   │           ├── detailed_results.json
│   │           ├── comparison.md       # Compare vs previous runs
│   │           └── logs/               # Full execution logs
│   ├── TERMINAL_BENCH_PLAN.md          # This file
│   ├── README.md                        # Benchmarking guide
│   └── requirements.txt                 # TB-specific dependencies
```

---

## Component 1: Fireteam Agent Adapter

**File:** `benchmarks/terminal_bench/fireteam_agent.py`

**Purpose:** Implement `AbstractInstalledAgent` to expose Fireteam to Terminal Bench harness **without limiting its capabilities**

**Key Implementation Details:**

```python
from terminal_bench.agents.installed_agents.abstract_installed_agent import AbstractInstalledAgent
from terminal_bench.agents.installed_agents.types import TerminalCommand
import os

class FireteamAgent(AbstractInstalledAgent):
    @staticmethod
    def name() -> str:
        return "fireteam"

    @property
    def _install_agent_script_path(self) -> str:
        # Path to install_fireteam.sh
        return "benchmarks/terminal_bench/install_fireteam.sh"

    @property
    def _env(self) -> dict[str, str]:
        # Environment variables needed by Fireteam
        return {
            "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY"),
            "FIRETEAM_HOME": "/home/fireteam-user/fireteam",
            "PATH": "/home/fireteam-user/.local/bin:/usr/local/bin:/usr/bin:/bin",
            # Fireteam-specific: don't limit capabilities
            "FIRETEAM_BENCHMARK_MODE": "terminal-bench",
        }

    def _run_agent_commands(self, task_description: str) -> list[TerminalCommand]:
        # CRITICAL: Call full Fireteam orchestrator with ALL capabilities
        # - Multi-cycle execution
        # - Validation system
        # - Git integration
        # - State management
        # No artificial constraints

        return [
            TerminalCommand(
                command=(
                    f'cd /workspace && '
                    f'python3 /home/fireteam-user/fireteam/orchestrator.py '
                    f'--project-dir /workspace '
                    f'--prompt "{task_description}" '
                    f'--log-file /home/fireteam-user/fireteam/logs/terminal_bench_task.log'
                ),
                timeout=172800,  # 48 hours in seconds
            )
        ]
```

**Critical Design Decisions:**

1. **48-Hour Timeout:**
   - Allows Fireteam's perpetual execution to work properly
   - Tasks can run 20, 30, 50+ cycles if needed
   - Tests whether long-horizon execution improves completion quality

2. **Full Capabilities:**
   - Calls orchestrator.py directly (same as CLI)
   - No wrapper that limits functionality
   - All Fireteam features available: validation, git, state, etc.

3. **Working Directory:**
   - Tasks run in `/workspace` (TB standard)
   - Fireteam installed in `/home/fireteam-user/fireteam`
   - Logs to Fireteam's log directory for debugging

4. **State Isolation:**
   - Each task gets fresh Fireteam state
   - No contamination between tasks
   - Docker container ensures clean environment

---

## Component 2: Installation Script

**File:** `benchmarks/terminal_bench/install_fireteam.sh`

**Purpose:** Install Fireteam inside TB's Docker containers with proper permissions

**Critical Requirements:**

1. **User Permissions:**
   - Claude Code cannot run as root
   - But needs root permissions to install packages
   - Solution: Create `fireteam-user` with passwordless sudo

2. **Installation Steps:**

```bash
#!/bin/bash
set -e

echo "Installing Fireteam in Terminal Bench container..."

# 1. Create fireteam-user with passwordless sudo (NOT root)
if ! id -u fireteam-user > /dev/null 2>&1; then
    useradd -m -s /bin/bash fireteam-user
    usermod -aG sudo fireteam-user
    echo "fireteam-user ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers
fi

# 2. Install system dependencies as root
apt-get update
apt-get install -y python3.12 python3-pip git curl

# 3. Install Claude CLI (as root, but will be available to fireteam-user)
# Follow Claude CLI installation

# 4. Switch to fireteam-user for Fireteam setup
su - fireteam-user << 'EOF'
cd ~
git clone https://github.com/darkresearch/fireteam.git
cd fireteam
# Checkout specific version if needed
git checkout ${FIRETEAM_VERSION:-main}
bash setup.sh
EOF

# 5. Verify installation
su - fireteam-user -c "cd ~/fireteam && python3 orchestrator.py --help"

echo "Fireteam installation complete"
```

**Key Technical Details:**

- User: `fireteam-user` (not root, but has sudo)
- Claude CLI runs as `fireteam-user`
- Can `sudo apt install` when needed
- Matches our sudo-setup.mdx documentation

---

## Component 3: Benchmark Runner

**File:** `benchmarks/terminal_bench/run_benchmark.py`

**Purpose:** Orchestrate full benchmark runs with progressive reporting

**Key Features:**

```python
import subprocess
import json
from pathlib import Path
from datetime import datetime
import yaml

class TerminalBenchRunner:
    def __init__(self, config_path="config.yaml"):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)

        # Setup progressive reporting
        self.progress_dir = Path("reports/in_progress")
        self.progress_dir.mkdir(parents=True, exist_ok=True)

    def run_benchmark(self):
        """Run Terminal Bench with progressive reporting"""

        # 1. Validate environment
        self._validate_env()

        # 2. Start benchmark with streaming output
        cmd = [
            "tb", "run",
            "--agent-import-path", "benchmarks.terminal_bench.fireteam_agent:FireteamAgent",
            "--dataset-name", self.config['terminal_bench']['dataset'],
            "--dataset-version", self.config['terminal_bench']['version'],
            "--n-concurrent", str(self.config['terminal_bench']['concurrency']),
            "--output-dir", str(self.progress_dir / "raw_results"),
        ]

        # 3. Stream output and update progress reports in real-time
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        for line in process.stdout:
            print(line, end='')
            # Parse line for task completion
            self._update_progress_report(line)

        # 4. Generate final report when complete
        self._generate_final_report()
```

**Progressive Reporting:**

```python
def _update_progress_report(self, log_line):
    """Update in-progress report as tasks complete"""

    # Detect task completion in TB output
    # Parse results
    # Update reports/in_progress/current_summary.md
    # Update reports/in_progress/completed_tasks.json

    # User can monitor: cat reports/in_progress/current_summary.md
```

**Configuration** (`config.yaml`):

```yaml
terminal_bench:
  version: "0.1.1"  # TB version
  dataset: "terminal-bench-core"
  concurrency: 1  # Start with 1, increase carefully

fireteam:
  version: "main"  # Git branch/tag to test
  timeout_hours: 48  # Per-task timeout
  completion_threshold: 95
  validation_checks: 3

reporting:
  compare_to_previous: true
  upload_to_leaderboard: false  # Manual for now
  progress_update_interval: 300  # Update progress every 5 min
```

---

## Component 4: Progress Monitor

**File:** `benchmarks/terminal_bench/monitor_progress.py`

**Purpose:** Real-time monitoring and reporting during long benchmark runs

**Features:**

1. **Live Dashboard:**
```
=== Terminal Bench Progress ===
Started: 2025-01-19 10:00:00
Elapsed: 14h 32m

Tasks: 12/80 completed (15%)
Currently Running: Task #13 (Cycle 8, 92% complete)

Completed Tasks:
✓ Task #1: Build kernel (18 cycles, 96%, 8.2 hours)
✓ Task #2: Git server (12 cycles, 97%, 4.1 hours)
...

Average: 6.2 hours/task, 14.3 cycles/task
Estimated completion: 52 hours remaining
```

2. **Incremental Reports:**
   - `reports/in_progress/current_summary.md` - Updated every 5 min
   - `reports/in_progress/completed_tasks.json` - Machine-readable
   - `reports/in_progress/task_logs/` - Per-task logs

3. **CLI Tool:**
```bash
# Monitor while running
python benchmarks/terminal_bench/monitor_progress.py --watch

# Get summary
python benchmarks/terminal_bench/monitor_progress.py --summary
```

---

## Component 5: Results Analyzer

**File:** `benchmarks/terminal_bench/analyze_results.py`

**Purpose:** Parse TB output, generate comprehensive reports

**Analysis Features:**

1. **Overall Score:** % of tasks completed successfully
2. **Category Breakdown:** Performance by task type
3. **Fireteam-Specific Metrics:**
   - Average cycles per task
   - Average time per task
   - Validation pass rates
   - Timeout vs. completion distribution
4. **Comparison:**
   - vs. previous Fireteam runs
   - vs. published leaderboard (Claude Code, Droids)
5. **Long-Horizon Analysis:**
   - Which tasks benefited from 48hr timeout?
   - Did more cycles improve quality?
   - Diminishing returns analysis

**Output Files:**

```
reports/2025-01-19_v1.0.0/
├── summary.md                    # Executive summary with key insights
├── detailed_results.json         # Machine-readable full results
├── comparison.md                 # vs. previous + leaderboard
├── long_horizon_analysis.md      # Fireteam-specific analysis
├── task_breakdown.csv            # Per-task results
└── logs/
    ├── task_001.log
    ├── task_002.log
    └── ...
```

---

## Component 6: Report Templates

**`summary.md` format:**

```markdown
# Fireteam Terminal Bench Results

**Date:** 2025-01-19
**Fireteam Version:** v1.0.0 (commit abc123)
**Terminal Bench:** v0.1.1 (Core dataset, 80 tasks)
**Timeout:** 48 hours per task

## Overall Score
**XX%** (X/80 tasks completed)

## Comparison
| System | Score | Timeout | Notes |
|--------|-------|---------|-------|
| Factory Droids (Claude Opus 4.1) | 58.8% | ? | Sep 2025 |
| **Fireteam (current)** | **XX%** | 48h | Jan 2025 |
| Claude Code | ~45%* | ? | Estimated |

## Fireteam Performance Characteristics

### Time & Cycles
- **Average time per task:** X.X hours
- **Average cycles per completed task:** X.X cycles
- **Max cycles observed:** XX cycles (Task #YY)
- **Tasks using >24 hours:** X/80 (XX%)

### Long-Horizon Value
Tasks that benefited from extended runtime:
- Task #XX: 32 cycles, 38 hours → 98% completion
- Task #YY: 28 cycles, 41 hours → 96% completion

Shows Fireteam's perpetual execution enables completion
of tasks that shorter-timeout systems might abandon.

## Category Breakdown
| Category | Score | Avg Cycles | Avg Time |
|----------|-------|------------|----------|
| Coding | XX% | X.X | X.X hrs |
| Build/Test | XX% | X.X | X.X hrs |
| ML Workflows | XX% | X.X | X.X hrs |
| Systems | XX% | X.X | X.X hrs |

## Key Insights
- Perpetual execution model allows completion of complex tasks
- Validation system prevented XX false completions
- Average of X.X validation cycles per task
- Longer timeouts enabled X tasks to reach completion

## Notable Successes
1. Task #XX: Completed in XX cycles (YY hours)
2. Task #YY: ...

## Top Failures
1. Task #XX: Timeout after XX cycles (reason: ...)
2. Task #YY: ...
```

---

## Implementation Phases

### Phase 1: Basic Integration (Week 1) - IN PROGRESS
- [x] Create directory structure
- [x] Write `TERMINAL_BENCH_PLAN.md`
- [x] Implement `FireteamAgent` class
- [x] Write `install_fireteam.sh` with proper permissions
- [x] Update for UV package manager
- [ ] Install Terminal Bench on host (uv pip install terminal-bench)
- [ ] Test installation in local Docker container
- [ ] Test on 1-2 tasks manually (with 48hr timeout)
- [ ] Verify Fireteam runs with full capabilities

### Phase 2: Progressive Reporting (Week 2)
- [ ] Build `run_benchmark.py` orchestrator
- [ ] Implement `monitor_progress.py`
- [ ] Create progressive reporting system
- [ ] Test with 5-10 tasks
- [ ] Verify reports update during execution

### Phase 3: Full Run (Week 3)
- [ ] Implement `analyze_results.py`
- [ ] Create final report templates
- [ ] Run full benchmark (80 tasks, ~1 week runtime)
- [ ] Monitor progress throughout
- [ ] Generate first official report

### Phase 4: Analysis & Iteration (Week 4)
- [ ] Analyze results
- [ ] Document long-horizon findings
- [ ] Tune settings if needed
- [ ] Generate comparison report
- [ ] Update documentation

### Phase 5: Ongoing (Monthly)
- [ ] Run benchmarks regularly
- [ ] Track progress over time
- [ ] Update leaderboard comparison
- [ ] Publish results (if desired)

---

## Key Technical Decisions

### 1. Timeout Strategy: 48 Hours
**Rationale:**
- Fireteam is designed for perpetual execution
- Want to test if long-horizon iteration improves quality
- Many tasks might benefit from 20-50 cycles
- Differentiates from shorter-timeout systems

**Trade-offs:**
- ✅ Tests Fireteam's core value prop
- ✅ May achieve higher completion rates
- ✅ Data on diminishing returns
- ❌ Longer total runtime (weeks for full suite)
- ❌ Higher API costs

**Mitigation:**
- Start with concurrency=1 to manage costs
- Progressive reporting shows value early
- Can adjust timeout based on findings

### 2. Full Fireteam Capabilities
**Implementation:**
- Call `orchestrator.py` directly
- No wrapper limiting functionality
- All features enabled: validation, git, state, etc.

**Why:**
- Accurate test of Fireteam's real performance
- Validation system is core differentiator
- Want apples-to-apples with production usage

### 3. Progressive Reporting
**Implementation:**
- `monitor_progress.py` updates every 5 minutes
- `in_progress/` directory with live results
- Per-task logs available immediately

**Why:**
- 80 tasks × 48 hours = potential weeks of runtime
- Need visibility into progress
- Can analyze completed tasks while others run
- Early stopping if issues detected

### 4. Docker Permissions
**Solution:**
- Create `fireteam-user` (not root)
- Add to sudoers with NOPASSWD
- Claude runs as `fireteam-user`
- Can install packages via sudo

**Why:**
- Claude Code security requirement (can't run as root)
- Still needs install permissions
- Matches our documented sudo-setup.mdx

### 5. Concurrency
**Starting Point:** `n-concurrent=1`

**Rationale:**
- Safer for first run
- Lower API costs
- Easier to debug issues
- Can increase after validation

**Future:** May increase to 2-4 based on:
- API rate limits
- Cost budget
- Stability of results

---

## Cost & Runtime Estimates

### With 48-Hour Timeout, Concurrency=1

**Best Case (tasks complete quickly):**
- 80 tasks × 2 hours avg = 160 hours = ~7 days

**Expected Case:**
- 80 tasks × 6 hours avg = 480 hours = ~20 days

**Worst Case (many timeouts):**
- 80 tasks × 48 hours = 3,840 hours = 160 days (but unlikely)

**Realistic Estimate:**
- ~50% complete in <6 hours
- ~30% complete in 6-24 hours
- ~15% complete in 24-48 hours
- ~5% timeout
- **Total: ~2-3 weeks for full run**

### With Concurrency=4 (Future)

**Expected:** ~5-7 days total runtime

**Considerations:**
- API rate limits
- Cost (4× concurrent API usage)
- Docker resource requirements

---

## Success Criteria

### Phase 1 Success:
- [ ] Fireteam installs successfully in TB container
- [ ] Full orchestrator capabilities available
- [ ] Can complete at least 1 task end-to-end
- [ ] Permissions work correctly

### Phase 2 Success:
- [ ] Progressive reporting functional
- [ ] Can monitor live progress
- [ ] 5-10 task run completes
- [ ] Reports accurate

### Phase 3 Success:
- [ ] Full 80-task run completes
- [ ] Comprehensive report generated
- [ ] Clear score vs. leaderboard
- [ ] Long-horizon analysis available

### Phase 4 Success:
- [ ] Findings documented
- [ ] Comparison to Claude Code/Droids
- [ ] Insights on long-horizon value
- [ ] Recommendations for future runs

---

## Future Enhancements

1. **GitHub Actions Integration:**
   - Monthly automated runs
   - Artifact upload
   - Notifications on completion

2. **Cost Optimization:**
   - Dynamic timeout (shorter for simple tasks)
   - Smart concurrency based on task complexity
   - Early stopping for clearly failed tasks

3. **Leaderboard Submission:**
   - Automated submission process
   - Version tracking
   - Public results page

4. **Custom Task Suite:**
   - Create Fireteam-specific long-horizon tasks
   - Test 24-72 hour project completion
   - Benchmark vs. Claude Code directly

---

## Open Questions

1. **Actual task distribution:** How many will timeout vs. complete early?
2. **Diminishing returns:** At what cycle count does quality plateau?
3. **Cost-benefit:** Is 48hr timeout worth the API cost increase?
4. **Comparison fairness:** What timeout do other systems use?

These will be answered by Phase 3 full run.

---

## References

- Terminal Bench: https://www.tbench.ai/
- Terminal Bench Docs: https://www.tbench.ai/docs
- GitHub: https://github.com/laude-institute/terminal-bench
- Factory Droids Result: https://factory.ai/news/terminal-bench
- Current Leaderboard: https://www.tbench.ai/

---

**Last Updated:** 2025-01-19
**Next Review:** After Phase 1 completion
