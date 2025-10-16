# Claude Agent System - Improvement Plan

**Status:** HIGH PRIORITY ITEMS IMPLEMENTED ✅
**Created:** 2025-10-16
**Last Updated:** 2025-10-16
**Priority:** High Priority items first, then Medium, then Low

---

## Implementation Status

**High Priority:**
- ✅ #1: Configurable Agent Timeouts (IMPLEMENTED)
- ✅ #8: Sudo Password Support (IMPLEMENTED)
- ✅ #9: Agent Drift Prevention - Goal Alignment Checks (IMPLEMENTED - Partial)

**Medium Priority:**
- ✅ #7: Parse Failure Handling (IMPLEMENTED)

---

## High Priority Improvements

### 1. Configurable Agent Timeouts

**Current Issue:** 45% executor timeout rate (5/11 executions), wasting time on retries. Planner also hitting timeouts on complex projects.

**Root Cause:** Hardcoded 10-minute timeout too aggressive for complex tasks (package installation, full test suite runs). 5-minute planner timeout occasionally insufficient.

**Real-world Data:**
- **Executor**: 45% timeout rate at 10 min → 0% at 30 min ✅
- **Planner**: Hit 2/3 timeouts on GitHub Analyzer Cycle 2 at 5 min, succeeded on attempt 3

**Solution:**

**File:** `config.py`
```python
# Add new configuration section:
# Agent timeouts (in seconds)
AGENT_TIMEOUTS = {
    "planner": 600,      # 10 minutes (complex planning, analysis)
    "reviewer": 600,     # 10 minutes (code review + test runs)
    "executor": 1800     # 30 minutes (complex builds, installations, test suites)
}
```

**File:** `agents/base.py` (line 42)
```python
# Before:
timeout=600,  # 10 minute timeout

# After:
from claude_agent_system import config
timeout=config.AGENT_TIMEOUTS.get(self.agent_type, 600),
```

**Expected Impact:**
- Reduce executor timeouts from 45% to <10%
- Save ~10 minutes per test (fewer retries)
- Total time savings: ~30-60 minutes across 6 tests

**Testing:**
- Run single test after change to verify timeouts work
- Monitor for any new timeout issues

---

### 2. Log Rotation

**Current Issue:** 13+ orchestrator logs accumulating (50KB now, will grow)

**Solution:**

**New File:** `utils/log_rotation.py`
```python
"""Log rotation utilities."""
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
import config

def rotate_logs(keep_last_n=10):
    """
    Rotate orchestrator logs, keeping only the most recent N.

    Args:
        keep_last_n: Number of recent logs to keep (default: 10)
    """
    logs_dir = Path(config.LOGS_DIR)
    archive_dir = logs_dir / "archive"
    archive_dir.mkdir(exist_ok=True)

    # Find all orchestrator logs
    log_files = sorted(
        logs_dir.glob("orchestrator_*.log"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )

    # Keep most recent N, archive the rest
    for log_file in log_files[keep_last_n:]:
        archive_path = archive_dir / log_file.name
        shutil.move(str(log_file), str(archive_path))
        print(f"Archived: {log_file.name}")

    # Delete archived logs older than 30 days
    cutoff_date = datetime.now() - timedelta(days=30)
    for archived_log in archive_dir.glob("orchestrator_*.log"):
        if datetime.fromtimestamp(archived_log.stat().st_mtime) < cutoff_date:
            archived_log.unlink()
            print(f"Deleted old archive: {archived_log.name}")

if __name__ == "__main__":
    rotate_logs()
```

**File:** `orchestrator.py` (add at startup)
```python
# Add near top of main():
from utils.log_rotation import rotate_logs
rotate_logs(keep_last_n=10)
```

**Alternative:** Add to CLI script `start-agent`:
```bash
# Before starting orchestrator
python3 /home/claude/claude-agent-system/utils/log_rotation.py
```

---

### 3. State Transition Logging

**Current Issue:** Completion % changes without explanation in logs

**Solution:**

**File:** `orchestrator.py` (in review phase, after getting reviewer output)
```python
# After line where we update state with completion_percentage:
old_completion = state.get("completion_percentage", 0)
new_completion = review_result["completion_percentage"]

if new_completion != old_completion:
    direction = "↑" if new_completion > old_completion else "↓"
    self.logger.info(
        f"Completion updated: {old_completion}% {direction} {new_completion}% "
        f"(Cycle {cycle_num})"
    )

    # Log reason if available in review result
    if "reason" in review_result:
        self.logger.info(f"Reason: {review_result['reason']}")
```

**File:** `agents/reviewer.py` (enhance output parsing)
```python
# After extracting completion percentage, also extract reasoning:
def _parse_review_output(self, output):
    """Parse reviewer output for completion % and reasoning."""
    completion_pct = self._extract_completion_percentage(output)

    # Try to extract reasoning (look for common patterns)
    reasoning = ""
    if "reason" in output.lower() or "because" in output.lower():
        # Extract 1-2 sentences explaining the score
        # Implementation depends on reviewer output format
        pass

    return {
        "completion_percentage": completion_pct,
        "reason": reasoning,
        "full_output": output
    }
```

---

### 8. Sudo Password Support for System Dependencies

**Current Issue:** Agent system cannot install system dependencies (Node.js, build tools, etc.) because sudo requires a password. This blocked GitHub Analyzer for 5+ cycles until agent found a workaround (binary installation).

**Real-world Impact:**
- **GitHub Analyzer (Cycles 8-11):** Stuck unable to install Node.js for TypeScript compilation
- **Workaround:** Agent eventually installed Node.js binary to ~/.local/bin (no sudo needed)
- **Time Wasted:** ~5 cycles and multiple hours trying different approaches
- **Better Solution:** If agents could use sudo, Node.js installs in <1 minute

**Root Cause:**
- `sudo` requires password in this environment (`sudo -n whoami` fails)
- Agents cannot provide password interactively
- No passwordless sudo configured initially

**Solution:**

**Option 1: Environment Variable Approach (Recommended for flexibility)**

**File:** `.env` (in `/home/claude/claude-agent-system/`)
```bash
# Sudo password for system-level package installation
# Used by agents when installing dependencies (Node.js, build tools, etc.)
SUDO_PASSWORD=claude
```

**File:** `config.py` (add configuration)
```python
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    load_dotenv(env_file)

# Sudo password for system operations (optional)
SUDO_PASSWORD = os.getenv("SUDO_PASSWORD", None)

def has_sudo_access():
    """Check if sudo password is available."""
    return SUDO_PASSWORD is not None
```

**File:** `agents/executor.py` (add sudo helper method)
```python
import config

class ExecutorAgent(BaseAgent):
    def _run_with_sudo(self, command):
        """
        Run a command with sudo using password from environment.

        Args:
            command: Command to run (e.g., "apt-get install -y nodejs")

        Returns:
            Result of command execution
        """
        if not config.has_sudo_access():
            self.logger.warning(
                "SUDO_PASSWORD not configured. Cannot run: sudo " + command
            )
            return {
                "success": False,
                "error": "Sudo password not available. Set SUDO_PASSWORD in .env file."
            }

        # Use echo + pipe to provide password non-interactively
        sudo_command = f'echo "{config.SUDO_PASSWORD}" | sudo -S {command}'

        self.logger.info(f"Running with sudo: {command}")
        return self._execute_command(sudo_command, self.project_dir)

    def install_system_package(self, package_name):
        """
        Install a system package using apt-get.

        Example: install_system_package("nodejs")
        """
        return self._run_with_sudo(f"apt-get update && apt-get install -y {package_name}")
```

**File:** `.gitignore` (ensure .env is never committed)
```bash
# Environment variables (contains sudo password)
.env
```

**Usage in Agent Prompts:**
```python
# Add to executor/planner prompts:
"""
If you need to install system dependencies (Node.js, build tools, etc.),
you can use:

    self.install_system_package("nodejs npm")

This will use sudo with the configured password from the .env file.

Before attempting manual installation workarounds, try using
install_system_package() first.
"""
```

**Option 2: Passwordless Sudo (Alternative, better for dedicated dev environments)**

**One-time Setup Command:**
```bash
echo "claude" | sudo -S bash -c 'echo "claude ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/claude-nopasswd && chmod 440 /etc/sudoers.d/claude-nopasswd'
```

**Pros:**
- No password in logs or environment variables
- Cleaner agent commands (just `sudo apt-get install nodejs`)
- More secure (no password stored in files)

**Cons:**
- Requires one-time system configuration
- Not portable across environments without setup
- Users might forget to set it up

**Recommendation:**
- **Use Option 2 (passwordless sudo) for dedicated dev/test environments** ✅
- **Use Option 1 (environment variable) if portability across machines is needed**

**Implementation Notes:**
1. Document in README.md that users should run the setup command
2. Add check at orchestrator startup to test if sudo works
3. Log warning if sudo not available but skip rather than fail

**Expected Impact:**
- TypeScript/Node.js projects: Install in 1 cycle instead of 5+
- Other dependencies: Automatically installable (Python packages, build tools, etc.)
- Time savings: ~30-60 minutes per project requiring system dependencies
- Better user experience: No manual intervention needed

**Setup Instructions for Users:**

Create `/home/claude/claude-agent-system/README.md` section:
```markdown
## Environment Setup

### Sudo Access (Required for installing system dependencies)

The agent system may need to install packages like Node.js, npm, or build tools.

**Option 1: Passwordless sudo (recommended for dev environments)**
```bash
echo "YOUR_PASSWORD" | sudo -S bash -c 'echo "$(whoami) ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/$(whoami)-nopasswd && chmod 440 /etc/sudoers.d/$(whoami)-nopasswd'
```

**Option 2: Environment variable (portable)**
1. Create `.env` file in `/home/claude/claude-agent-system/`:
   ```bash
   SUDO_PASSWORD=your_password_here
   ```
2. The `.env` file is gitignored and will not be committed

**Test sudo access:**
```bash
sudo -n whoami  # Should print "root" without password prompt
```
```

**Dependencies to Install:**
```bash
pip install python-dotenv  # For loading .env files
```

---

### 9. Prevent Agent Drift - Scope Creep Detection

**Current Issue:** Agents expand project scope beyond original goal without user approval. GitHub Analyzer created npm deployment infrastructure despite goal only requiring "production-ready" code.

**Real-world Impact:**
- **GitHub Analyzer Test:** Agent created deployment automation (deploy.sh, test-repositories.sh, 2,630+ lines of deployment docs)
- **Original Goal:** "Build a CLI tool... make it production-ready with proper error handling"
- **Agent Interpretation:** "Production-ready" → "Deploy to npm registry with automated publishing"
- **Result:** Wasted cycles (14-16) on deployment work never requested
- **User Feedback:** "We definitely do not want to deploy it to npm anywhere. Where did we say we were going to do that?"

**Root Cause:**
- Agents interpret ambiguous goals too broadly
- No mechanism to check if new work is within scope
- "Production-ready" misinterpreted as "deploy to production"
- Agents don't validate assumptions about deliverables

**Examples of Agent Drift:**

| Original Goal | Agent Did | Should Have Done |
|---------------|-----------|------------------|
| "Production-ready CLI tool" | Created npm publish automation | Made code high-quality, stopped there |
| "Handle rate limits" | Implemented monitoring, warnings, retries | Implemented basic handling, asked if more needed |
| "Generate markdown report" | Also created JSON format + deployment scripts | Generated markdown, asked if other formats wanted |

**Impact:**
- **Time wasted:** 2-3 cycles on out-of-scope work
- **Complexity added:** Unnecessary deployment infrastructure
- **Goal dilution:** Original goal lost in expanded scope
- **User confusion:** "Why is it doing this?"

**Solution:**

**File:** `agents/planner.py` (add goal validation check)
```python
class PlannerAgent(BaseAgent):
    def __init__(self, ...):
        super().__init__(...)
        self.original_goal = goal  # Store original goal

    def _validate_scope(self, planned_tasks):
        """
        Check if planned tasks align with original goal.
        Flag potential scope creep for user review.
        """
        scope_keywords = {
            "deploy": ["deploy", "publish", "npm publish", "release", "production deployment"],
            "infrastructure": ["ci/cd", "docker", "kubernetes", "deployment pipeline"],
            "features": ["new feature", "additional feature", "bonus feature"],
            "platforms": ["mobile", "web", "desktop", "cloud"]
        }

        potential_drift = []

        for task in planned_tasks:
            task_lower = task.lower()

            # Check if task involves deployment/publishing
            if any(keyword in task_lower for keyword in scope_keywords["deploy"]):
                if not any(keyword in self.original_goal.lower() for keyword in scope_keywords["deploy"]):
                    potential_drift.append({
                        "task": task,
                        "category": "deployment",
                        "reason": "Task involves deployment but original goal doesn't mention deployment"
                    })

            # Check for infrastructure work
            if any(keyword in task_lower for keyword in scope_keywords["infrastructure"]):
                if not any(keyword in self.original_goal.lower() for keyword in scope_keywords["infrastructure"]):
                    potential_drift.append({
                        "task": task,
                        "category": "infrastructure",
                        "reason": "Task involves infrastructure but original goal doesn't specify this"
                    })

        return potential_drift

    def plan(self, ...):
        # ... generate plan ...

        # Check for scope creep
        drift = self._validate_scope(planned_tasks)

        if drift:
            self.logger.warning(f"⚠️  POTENTIAL SCOPE CREEP DETECTED")
            self.logger.warning(f"Found {len(drift)} task(s) that may be outside original goal:")

            for item in drift:
                self.logger.warning(f"  - {item['task']}")
                self.logger.warning(f"    Reason: {item['reason']}")

            # Add to plan output for reviewer
            plan_output += "\n\n## ⚠️ SCOPE VALIDATION WARNING\n\n"
            plan_output += "The following tasks may be outside the original goal:\n\n"
            for item in drift:
                plan_output += f"- **{item['task']}**\n"
                plan_output += f"  - Category: {item['category']}\n"
                plan_output += f"  - Reason: {item['reason']}\n\n"
            plan_output += "**Recommendation:** Reviewer should validate these tasks are actually needed.\n"

        return plan_output
```

**File:** `agents/reviewer.py` (add scope validation in review)
```python
class ReviewerAgent(BaseAgent):
    def review(self, ...):
        # ... perform review ...

        # Check if work done matches original goal
        review_output += "\n\n## Goal Alignment Check\n\n"
        review_output += f"**Original Goal:** {self.original_goal}\n\n"

        # Analyze what was actually built
        files_created = self._get_files_created()

        # Check for potential drift indicators
        drift_indicators = []

        if any("deploy" in f for f in files_created):
            if "deploy" not in self.original_goal.lower():
                drift_indicators.append("Deployment scripts created but not requested")

        if any("docker" in f for f in files_created):
            if "docker" not in self.original_goal.lower():
                drift_indicators.append("Docker files created but not requested")

        # Count documentation-only commits
        doc_commits = self._count_documentation_commits()
        if doc_commits > 3:
            drift_indicators.append(f"{doc_commits} documentation-only commits (may indicate over-documentation)")

        if drift_indicators:
            review_output += "**⚠️ Potential Scope Drift Detected:**\n\n"
            for indicator in drift_indicators:
                review_output += f"- {indicator}\n"
            review_output += "\n**Recommendation:** Consider if this extra work was necessary.\n"
        else:
            review_output += "✅ Work aligns well with original goal.\n"

        return review_output
```

**File:** `orchestrator.py` (add periodic goal alignment check)
```python
class Orchestrator:
    def run_cycle(self, cycle_num):
        # ... existing cycle logic ...

        # Every 3 cycles, check goal alignment
        if cycle_num > 0 and cycle_num % 3 == 0:
            self.logger.info(f"\n{'='*60}")
            self.logger.info(f"GOAL ALIGNMENT CHECK (Cycle {cycle_num})")
            self.logger.info(f"{'='*60}")
            self.logger.info(f"Original Goal: {self.goal}")

            # Check recent commits
            recent_commits = self._get_recent_commit_messages(count=5)

            self.logger.info(f"\nRecent work (last 5 commits):")
            for commit in recent_commits:
                self.logger.info(f"  - {commit}")

            self.logger.info(f"\n⚠️  Reminder: Ensure all work aligns with original goal!")
            self.logger.info(f"{'='*60}\n")
```

**Prompt Engineering Changes:**

Add to all agent prompts:
```
SCOPE CONSTRAINT:

Your original goal is:
"{goal}"

IMPORTANT:
- Do NOT expand the scope beyond what's explicitly stated
- If the goal says "production-ready", that means HIGH QUALITY CODE, not "deploy to production"
- Do NOT create deployment infrastructure (Docker, npm publish scripts, CI/CD) unless explicitly requested
- Do NOT publish packages to registries (npm, PyPI, etc.) unless explicitly requested
- If you think additional work would be valuable, MENTION it in your output but DO NOT implement it
- When in doubt, stick to the literal interpretation of the goal

Examples:
- "Build a CLI tool" → Build the tool, don't deploy it
- "Production-ready" → Make code high-quality, don't publish it
- "Handle errors" → Basic error handling, don't build monitoring infrastructure
```

**Expected Impact:**
- Prevent scope creep from adding 20-30% extra work
- Save 2-3 cycles per project on out-of-scope work
- Reduce documentation bloat (fewer deployment guides for unrequested deployments)
- Improve user trust (agents do what was asked, nothing more)

**Testing:**
- Re-run GitHub Analyzer test with scope validation enabled
- Verify it stops at "production-ready code" without creating deployment scripts
- Test with ambiguous goals like "make it professional" to verify it asks for clarification

**Trade-offs:**
- **Pro:** Prevents wasted work on unrequested features
- **Pro:** Keeps projects focused on original goal
- **Pro:** Reduces complexity and documentation overhead
- **Con:** May occasionally flag legitimate work as drift
- **Con:** Adds validation overhead to planning/review

**Recommendation:** Implement as HIGH PRIORITY - this is a common pattern that wastes significant time.

---

## Medium Priority Improvements

### 4. Metrics Collection & Analysis

**Value:** Data-driven optimization, identify patterns, tune performance

**Solution:**

**New File:** `utils/metrics_logger.py`
```python
"""Metrics collection for agent system performance."""
import json
from datetime import datetime
from pathlib import Path
import config

class MetricsLogger:
    def __init__(self, project_name):
        self.project_name = project_name
        self.metrics_file = Path(config.LOGS_DIR) / "metrics.jsonl"
        self.session_start = datetime.now()

    def log_agent_execution(self, agent_type, duration, success,
                           attempt_number, timeout=False):
        """Log individual agent execution metrics."""
        metric = {
            "timestamp": datetime.now().isoformat(),
            "project": self.project_name,
            "agent_type": agent_type,
            "duration_seconds": duration,
            "success": success,
            "attempt_number": attempt_number,
            "timed_out": timeout
        }

        with open(self.metrics_file, 'a') as f:
            f.write(json.dumps(metric) + '\n')

    def log_cycle_completion(self, cycle_number, completion_pct,
                            total_duration):
        """Log cycle-level metrics."""
        metric = {
            "timestamp": datetime.now().isoformat(),
            "project": self.project_name,
            "event": "cycle_complete",
            "cycle_number": cycle_number,
            "completion_percentage": completion_pct,
            "duration_seconds": total_duration
        }

        with open(self.metrics_file, 'a') as f:
            f.write(json.dumps(metric) + '\n')

    def log_project_completion(self, final_completion, total_cycles,
                               total_duration):
        """Log project-level metrics."""
        metric = {
            "timestamp": datetime.now().isoformat(),
            "project": self.project_name,
            "event": "project_complete",
            "final_completion": final_completion,
            "total_cycles": total_cycles,
            "total_duration_seconds": total_duration
        }

        with open(self.metrics_file, 'a') as f:
            f.write(json.dumps(metric) + '\n')

# Analysis script
def analyze_metrics():
    """Analyze metrics and print summary statistics."""
    metrics_file = Path(config.LOGS_DIR) / "metrics.jsonl"

    if not metrics_file.exists():
        print("No metrics found")
        return

    # Load all metrics
    metrics = []
    with open(metrics_file) as f:
        for line in f:
            metrics.append(json.loads(line))

    # Analyze by agent type
    from collections import defaultdict
    import statistics

    agent_stats = defaultdict(lambda: {
        "executions": 0,
        "timeouts": 0,
        "durations": [],
        "success_rate": 0
    })

    for m in metrics:
        if "agent_type" in m:
            agent_type = m["agent_type"]
            agent_stats[agent_type]["executions"] += 1
            agent_stats[agent_type]["durations"].append(m["duration_seconds"])
            if m.get("timed_out"):
                agent_stats[agent_type]["timeouts"] += 1
            if m.get("success"):
                agent_stats[agent_type]["success_rate"] += 1

    # Print summary
    print("\n=== Agent Performance Metrics ===\n")
    for agent_type, stats in agent_stats.items():
        durations = stats["durations"]
        avg_duration = statistics.mean(durations) if durations else 0
        timeout_rate = (stats["timeouts"] / stats["executions"] * 100)
                       if stats["executions"] > 0 else 0
        success_rate = (stats["success_rate"] / stats["executions"] * 100)
                       if stats["executions"] > 0 else 0

        print(f"{agent_type.upper()}:")
        print(f"  Executions: {stats['executions']}")
        print(f"  Avg Duration: {avg_duration:.1f}s ({avg_duration/60:.1f}min)")
        print(f"  Timeout Rate: {timeout_rate:.1f}%")
        print(f"  Success Rate: {success_rate:.1f}%")
        print()

if __name__ == "__main__":
    analyze_metrics()
```

**File:** `agents/base.py` (integrate metrics)
```python
from utils.metrics_logger import MetricsLogger

class BaseAgent:
    def __init__(self, ...):
        # ... existing init ...
        self.metrics = MetricsLogger(project_dir.split('/')[-1])

    def execute(self, ...):
        start_time = time.time()
        timed_out = False
        success = False

        try:
            # ... existing execution logic ...
            success = result["success"]
        except subprocess.TimeoutExpired:
            timed_out = True
            # ... existing timeout handling ...
        finally:
            duration = time.time() - start_time
            self.metrics.log_agent_execution(
                self.agent_type, duration, success,
                attempt + 1, timed_out
            )
```

**Analysis Command:**
```bash
python3 /home/claude/claude-agent-system/utils/metrics_logger.py
```

---

### 5. Structured Error Messages with Suggestions

**Current Issue:** Raw stderr dumps, hard to identify patterns

**Solution:**

**New File:** `utils/error_parser.py`
```python
"""Parse common errors and provide actionable suggestions."""
import re

ERROR_PATTERNS = {
    "module_not_found": {
        "pattern": r"ModuleNotFoundError: No module named '([^']+)'",
        "suggestion": "Install missing module: pip install {module}",
        "severity": "high"
    },
    "file_not_found": {
        "pattern": r"FileNotFoundError: \[Errno 2\] No such file or directory: '([^']+)'",
        "suggestion": "Create missing file or check path: {file}",
        "severity": "high"
    },
    "permission_denied": {
        "pattern": r"PermissionError: \[Errno 13\] Permission denied: '([^']+)'",
        "suggestion": "Check file permissions: chmod +x {file}",
        "severity": "medium"
    },
    "import_error": {
        "pattern": r"ImportError: cannot import name '([^']+)' from '([^']+)'",
        "suggestion": "Check if {name} exists in {module} or update imports",
        "severity": "high"
    },
    "syntax_error": {
        "pattern": r"SyntaxError: (.+)",
        "suggestion": "Fix syntax error: {error}",
        "severity": "critical"
    },
    "type_error": {
        "pattern": r"TypeError: (.+)",
        "suggestion": "Fix type mismatch: {error}",
        "severity": "medium"
    },
    "attribute_error": {
        "pattern": r"AttributeError: '([^']+)' object has no attribute '([^']+)'",
        "suggestion": "Check if {attr} is valid for {obj} type",
        "severity": "medium"
    }
}

def parse_error(error_text):
    """
    Parse error text and return structured error info with suggestions.

    Returns:
        dict: {
            "error_type": str,
            "original": str,
            "suggestion": str,
            "severity": str,
            "matches": dict
        }
    """
    for error_type, config in ERROR_PATTERNS.items():
        match = re.search(config["pattern"], error_text)
        if match:
            # Extract variables from regex groups
            variables = {}
            if "module" in config["suggestion"]:
                variables["module"] = match.group(1)
            if "file" in config["suggestion"]:
                variables["file"] = match.group(1)
            if "name" in config["suggestion"]:
                variables["name"] = match.group(1)
                if match.lastindex >= 2:
                    variables["module"] = match.group(2)
            if "error" in config["suggestion"]:
                variables["error"] = match.group(1)
            if "attr" in config["suggestion"]:
                variables["obj"] = match.group(1)
                variables["attr"] = match.group(2)

            # Format suggestion with variables
            suggestion = config["suggestion"].format(**variables)

            return {
                "error_type": error_type,
                "original": error_text,
                "suggestion": suggestion,
                "severity": config["severity"],
                "matches": variables
            }

    # No pattern matched
    return {
        "error_type": "unknown",
        "original": error_text,
        "suggestion": "Review error message and debug manually",
        "severity": "unknown",
        "matches": {}
    }

def format_error_report(error_text):
    """Generate a formatted error report with suggestions."""
    parsed = parse_error(error_text)

    severity_emoji = {
        "critical": "🔴",
        "high": "🟠",
        "medium": "🟡",
        "unknown": "⚪"
    }

    report = f"""
{severity_emoji.get(parsed['severity'], '⚪')} {parsed['error_type'].upper().replace('_', ' ')}
Severity: {parsed['severity']}

Original Error:
{parsed['original']}

Suggested Fix:
💡 {parsed['suggestion']}
"""
    return report
```

**File:** `agents/base.py` (integrate error parsing)
```python
from utils.error_parser import parse_error, format_error_report

# In execute method, when handling failures:
if result.returncode != 0:
    self.logger.warning(f"{self.agent_type} failed with return code {result.returncode}")

    # Parse and log structured error
    error_info = parse_error(result.stderr)
    if error_info["error_type"] != "unknown":
        self.logger.error(f"Error Type: {error_info['error_type']}")
        self.logger.error(f"Suggestion: {error_info['suggestion']}")

    self.logger.warning(f"stderr: {result.stderr}")
```

---

### 6. Executor Progress Logging (Every Minute)

**Value:** Visibility into long-running tasks without overwhelming logs

**Solution:**

**File:** `agents/base.py`
```python
import threading
import time

class BaseAgent:
    def _log_progress_periodically(self, process, interval=60):
        """Log that agent is still running every N seconds."""
        start_time = time.time()

        def log_heartbeat():
            while process.poll() is None:  # While process is running
                elapsed = time.time() - start_time
                self.logger.info(
                    f"{self.agent_type} still running... "
                    f"({int(elapsed/60)}m {int(elapsed%60)}s elapsed)"
                )
                time.sleep(interval)

        thread = threading.Thread(target=log_heartbeat, daemon=True)
        thread.start()
        return thread

    def _execute_command(self, cmd, project_dir):
        """Execute command with progress logging."""
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=project_dir
        )

        # Start progress logging thread
        progress_thread = self._log_progress_periodically(process, interval=60)

        try:
            stdout, stderr = process.communicate(timeout=self.timeout)

            if process.returncode == 0:
                self.logger.info(f"{self.agent_type} completed successfully")
                return {"success": True, "output": stdout, "error": None}
            else:
                return {"success": False, "output": stdout, "error": stderr}

        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            raise
```

---

### 7. Use Last Known Completion Percentage on Parse Failure

**Current Issue:** When reviewer output can't be parsed, system defaults to 0%, triggering unnecessary cycles

**Real-world Example:**
- Cycle 0: Reaches 92%, commits successfully ✅
- Cycle 1: Executor finds nothing to do, reviewer says "looks good" without explicit percentage
- Parser fails, defaults to 0% → triggers unnecessary Cycle 2

**Root Cause:** Parser failure ≠ actual regression. Project is still at 92%, just couldn't parse the review output.

**Solution:**

**File:** `state_manager.py` (or wherever state is managed)
```python
class StateManager:
    def __init__(self):
        self.state = self._load_state()
        self.last_known_completion = self.state.get("completion_percentage", 0)
        self.consecutive_parse_failures = 0

    def update_completion_percentage(self, parsed_percentage):
        """
        Update completion percentage with fallback to last known value.

        Args:
            parsed_percentage: Result from parser (may be None if parsing failed)

        Returns:
            int: Completion percentage to use
        """
        if parsed_percentage is not None:
            # Successful parse - reset failure counter
            self.consecutive_parse_failures = 0
            self.last_known_completion = parsed_percentage
            self.logger.info(f"Completion: {parsed_percentage}%")
            return parsed_percentage
        else:
            # Parse failure - use last known value
            self.consecutive_parse_failures += 1
            self.logger.warning(
                f"Could not parse completion percentage "
                f"(failure #{self.consecutive_parse_failures}). "
                f"Using last known: {self.last_known_completion}%"
            )

            # Safety valve: stop after 3 consecutive failures
            if self.consecutive_parse_failures >= 3:
                self.logger.error(
                    "3 consecutive parse failures - parser may be broken. "
                    "Defaulting to 0% to force investigation."
                )
                return 0

            return self.last_known_completion
```

**File:** `orchestrator.py` (in review phase)
```python
# Before:
completion_percentage = self._extract_completion_from_review(review_output)
if completion_percentage is None:
    completion_percentage = 0  # Default to 0 if parsing fails

# After:
parsed_percentage = self._extract_completion_from_review(review_output)
completion_percentage = self.state_manager.update_completion_percentage(parsed_percentage)
```

**Why This Is Better:**
1. **Monotonic assumption**: Completion percentage should only increase or stay same (not decrease unless genuinely broken)
2. **Git is source of truth**: If there are commits, there's progress. If no commits, nothing broke.
3. **Simple state**: Just one integer field (`last_known_completion`)
4. **Safety valve**: Still catches genuine parser breakage (3 consecutive failures)

**Expected Impact:**
- Eliminate unnecessary cycles from benign parsing failures
- Save ~10-20 minutes when parsing hiccups occur
- Maintain safety with consecutive failure detection

**Trade-offs:**
- **Current (default to 0%)**: More conservative, wastes cycles on parsing issues
- **Proposed (use last known)**: More efficient, better reflects actual state

**Consensus:** Proposed approach is better. System already has enough safeguards (max cycles, validation checks, git history) that defaulting to 0% is overly conservative.

---

## Low Priority Improvements (Future)

### 8. Adaptive Timeouts Based on Cycle Number

**Idea:** Later cycles tend to be faster (smaller changes)

**Implementation:** Reduce timeout by 20% for Cycle 2+

---

### 9. Retry Strategy Improvements

**Current:** Fixed 3 retries with 5-second delay

**Better:** Exponential backoff (5s, 10s, 20s)

---

### 10. Parallel Agent Execution (Advanced)

**Idea:** Run planner for next cycle while current cycle reviews

**Complexity:** High - requires careful state management

---

## Implementation Checklist

**WAIT UNTIL BATCH TESTS COMPLETE BEFORE STARTING**

- [ ] **Step 1:** Create backup of working system
  ```bash
  cp -r /home/claude/claude-agent-system /home/claude/claude-agent-system-backup
  ```

- [ ] **Step 2:** Implement High Priority items (in order)
  - [ ] 1. Configurable Agent Timeouts
  - [ ] 2. Log Rotation
  - [ ] 3. State Transition Logging

- [ ] **Step 3:** Test with single project
  ```bash
  start-agent --project-dir /home/claude/test-project --prompt "Build hello world"
  ```

- [ ] **Step 4:** Implement Medium Priority items
  - [ ] 4. Metrics Collection
  - [ ] 5. Structured Error Messages
  - [ ] 6. Executor Progress Logging
  - [ ] 7. Use Last Known Completion % on Parse Failure

- [ ] **Step 5:** Run full test suite again to validate improvements

- [ ] **Step 6:** Analyze metrics to verify improvements
  ```bash
  python3 /home/claude/claude-agent-system/utils/metrics_logger.py
  ```

---

## Expected Outcomes

**Time Savings:**
- Reduce executor timeouts: ~45% → <10% (save ~30-60 min per full test run)
- Faster debugging with structured errors
- Better visibility with progress logging

**Quality Improvements:**
- Better logs for debugging
- Metrics-driven optimization
- Cleaner log management

**Metrics to Track:**
- Timeout rate (target: <10%)
- Average cycle time (baseline: TBD)
- Success rate by agent (target: >95%)
- Time to 90% completion (baseline: ~30-60 min per project)

---

## Notes

- All changes are backwards compatible
- No breaking changes to existing interfaces
- Can be implemented incrementally
- Each improvement is independent (can be done separately)
