# Ralph vs Fireteam: Comprehensive Audit

**Date:** January 2026
**Purpose:** Compare Ralph (https://github.com/frankbria/ralph-claude-code) with Fireteam to identify strengths, weaknesses, and opportunities for improvement.

---

## Executive Summary

Both Ralph and Fireteam solve the same core problem: **autonomous, iterative AI-assisted development with quality gates**. However, they take fundamentally different approaches:

| Aspect | Ralph | Fireteam |
|--------|-------|----------|
| **Language** | Bash/Shell scripts | Python (claude-agent-sdk) |
| **Target** | Claude Code CLI wrapper | Library + Claude Code plugin |
| **Authentication** | Uses Claude Code session/credits | Requires separate API key |
| **Complexity Handling** | Uniform (all tasks same loop) | Adaptive (routes by complexity) |
| **Exit Detection** | Dual-gate (heuristics + explicit signal) | Reviewer consensus (1 or 3 reviewers) |
| **Safety Mechanisms** | Circuit breaker, rate limiting | Max iterations, test hooks |
| **Architecture** | Procedural scripts | Async Python with SDK |

---

## Where Fireteam Excels

### 1. **Adaptive Complexity Routing** ✓
Fireteam's biggest differentiator. It estimates task complexity and routes to appropriate execution strategies:

- **TRIVIAL/SIMPLE** → Single-turn execution (no overhead)
- **MODERATE** → Execute-review loop (1 reviewer)
- **COMPLEX** → Plan + execute + parallel reviews (3 reviewers, majority consensus)

Ralph treats all tasks identically, running the same loop regardless of whether you're fixing a typo or building a feature. This wastes API calls on simple tasks and may under-validate complex ones.

**Verdict: Fireteam significantly better**

### 2. **SDK-Native Integration** ✓
Fireteam uses the `claude-agent-sdk` directly, providing:
- Type-safe Python API
- Proper async/await patterns
- Direct tool control per phase
- Programmable hooks system
- Easy embedding in other Python projects

Ralph shells out to `claude` CLI, parsing JSON output. This is more fragile and harder to extend.

**Verdict: Fireteam significantly better**

### 3. **Parallel Reviewer Consensus** ✓
For complex tasks, Fireteam runs 3 reviewers in parallel and requires 2/3 agreement. This:
- Reduces false positives from a single biased review
- Provides diverse perspectives on completion
- Catches issues one reviewer might miss

Ralph uses a single response analyzer with heuristics.

**Verdict: Fireteam better**

### 4. **Planning Phase for Complex Tasks** ✓
Fireteam's FULL mode creates an explicit plan before execution:
- Read-only exploration phase
- Detailed step-by-step plan
- Plan injected into executor context

Ralph jumps straight into execution, relying on PROMPT.md for guidance.

**Verdict: Fireteam better**

### 5. **Quality Hooks with Immediate Feedback** ✓
Fireteam's `PostToolUse` hook runs tests after every Edit/Write:
- Immediate test failure feedback
- Auto-detects test framework (pytest, npm, cargo, etc.)
- Claude sees failures and can fix in same iteration

Ralph runs tests but doesn't inject failures back into Claude's context mid-loop.

**Verdict: Fireteam better**

### 6. **Library-First Design** ✓
Fireteam is designed as a library with a clean public API:
```python
from fireteam import execute
result = await execute(project_dir, goal)
```

This enables:
- Embedding in CI/CD pipelines
- Building custom workflows
- Programmatic control and monitoring

Ralph is primarily a CLI tool, harder to integrate.

**Verdict: Fireteam better**

---

## Where Ralph Excels

### 1. **Claude Code Session Piggybacking** ★★★★
Ralph wraps the `claude` CLI, which means it automatically uses:
- The user's existing Claude Code session
- The user's existing credits/billing
- No separate API key required
- Single source of truth for usage and billing

Fireteam uses `claude-agent-sdk` which makes **direct API calls**, requiring:
- A separate `ANTHROPIC_API_KEY` environment variable
- Separate billing to that API account
- Users need both Claude Code credits AND API credits

**Current Fireteam architecture:**
```
Claude Code session (user's credits)
    ↓ (invokes hook)
Fireteam plugin (user_prompt_submit.py)
    ↓ (calls execute())
claude-agent-sdk → Direct Anthropic API (separate API key/billing)
```

**This is fundamentally wrong.** Fireteam should piggyback on Claude Code's session so users don't need to manage two separate billing sources.

**This is a critical architectural gap in Fireteam.**

### 2. **Circuit Breaker Pattern** ★★★
Ralph's circuit breaker is sophisticated:
- Tracks files changed per loop
- Detects repeated identical errors
- Monitors output length decline
- Three states: CLOSED → HALF_OPEN → OPEN
- Thresholds: 3 loops no progress, 5 repeated errors

Fireteam only has `max_iterations` (optional) - it can loop infinitely if reviewer never says "complete". No detection of stuck patterns.

**This is a significant gap in Fireteam.**

### 3. **Rate Limiting** ★★★
Ralph implements per-hour API call quotas:
- Configurable calls per hour limit
- Automatic pause when quota exhausted
- Wait-for-reset functionality
- 5-hour API limit detection with graceful handling

Fireteam has no rate limiting - it will happily burn through API quota without bounds.

**This is a significant gap in Fireteam.**

### 4. **Session Continuity** ★★
Ralph preserves context across iterations:
- 24-hour session expiration
- Session state tracking
- Resume capability after interruption
- Automatic cleanup of stale sessions

Fireteam starts fresh each `execute()` call - no cross-session memory.

**Moderate gap - depends on use case.**

### 5. **Dual-Gate Exit Detection** ★★
Ralph requires BOTH conditions:
1. Natural language completion indicators (heuristics)
2. Explicit `EXIT_SIGNAL: true` from Claude

This respects Claude's judgment over automation assumptions. If Claude says "I'm still working on this" despite heuristics suggesting completion, the loop continues.

Fireteam relies solely on reviewer completion percentage (≥95%). The executor's opinion isn't considered.

**Moderate improvement opportunity.**

### 6. **Live Monitoring Dashboard** ★★
Ralph provides tmux-based real-time monitoring:
- Loop status visualization
- Progress tracking
- Execution logs
- Interactive observation

Fireteam only logs to console - no dashboard or monitoring UI.

**Nice-to-have gap.**

### 7. **PRD Import Functionality** ★
Ralph can convert documents (MD, JSON, PDF, Word) into structured projects:
- Analyzes existing documentation
- Creates PROMPT.md automatically
- Integrates with Claude for analysis

Fireteam requires manual goal/context specification.

**Nice-to-have feature.**

### 8. **Explicit Error Classification** ★
Ralph's response analyzer has two-stage error filtering:
- Distinguishes JSON field "error" from actual errors
- Context-aware pattern matching
- Prevents false positives

Fireteam doesn't explicitly track error patterns.

**Minor improvement opportunity.**

---

## Ideas to Pull into Fireteam

### Priority 0: Foundational (Architecture Change Required)

#### 0.1 Use Claude Code Session Instead of Direct API
**What:** Refactor to use Claude Code CLI instead of claude-agent-sdk direct API calls
**Why:** Users should not need a separate API key; billing should be unified
**Impact:** This is an architectural change that affects the core execution model

**Current flow (wrong):**
```
Claude Code → Fireteam hook → claude-agent-sdk → Anthropic API (separate billing)
```

**Target flow (correct):**
```
Claude Code → Fireteam hook → claude CLI subprocess → Claude Code session (same billing)
```

**Implementation approaches:**

1. **Subprocess approach (like Ralph):**
   - Shell out to `claude` CLI with structured prompts
   - Parse JSON output
   - Simpler but loses type safety

2. **SDK with session passthrough:**
   - Investigate if claude-agent-sdk can accept session tokens
   - Would preserve type safety if possible
   - Needs SDK documentation review

3. **Hybrid approach:**
   - Use CLI for actual execution (billing goes to user's Claude Code)
   - Use SDK for local-only operations (complexity estimation with caching)

**Recommendation:** Start with subprocess approach for MVP, then optimize.

### Priority 1: Critical (Safety & Resource Management)

#### 1.1 Circuit Breaker Pattern
**What:** Implement stuck-loop detection
**Why:** Prevent infinite loops that waste API credits
**How:**
```python
@dataclass
class CircuitBreaker:
    state: Literal["closed", "half_open", "open"] = "closed"
    no_progress_count: int = 0
    repeated_error_count: int = 0
    last_error_hash: str = ""

    def record_iteration(self, files_changed: int, error: str | None):
        if files_changed == 0:
            self.no_progress_count += 1
        else:
            self.no_progress_count = 0

        if error and hash(error) == self.last_error_hash:
            self.repeated_error_count += 1
        else:
            self.repeated_error_count = 0
            self.last_error_hash = hash(error) if error else ""

        self._update_state()

    def should_halt(self) -> bool:
        return self.state == "open"
```

**Thresholds to consider:**
- 3 consecutive loops with no file changes
- 5 repeated identical errors
- Output length decline >70%

#### 1.2 Rate Limiting
**What:** API call budget management
**Why:** Prevent runaway costs
**How:**
```python
@dataclass
class RateLimiter:
    calls_per_hour: int = 100
    calls_this_hour: int = 0
    hour_started: datetime = field(default_factory=datetime.now)

    async def acquire(self):
        if self._is_new_hour():
            self._reset()
        if self.calls_this_hour >= self.calls_per_hour:
            await self._wait_for_reset()
        self.calls_this_hour += 1
```

### Priority 2: High (Quality Improvement)

#### 2.1 Dual-Gate Exit with Executor Opinion
**What:** Let the executor signal if it believes work is incomplete
**Why:** Respects Claude's judgment, prevents premature termination
**How:** After execution, check for explicit "WORK_COMPLETE: false" or similar signal. If executor says incomplete, continue regardless of reviewer.

#### 2.2 Progress Tracking Metrics
**What:** Track files changed, errors encountered, output length per iteration
**Why:** Better visibility into execution health
**How:** Add `IterationMetrics` dataclass collected each loop.

### Priority 3: Medium (UX Improvement)

#### 3.1 Session Continuity
**What:** Persist state across execute() calls
**Why:** Allow resumption after interruption
**How:** Optional session file that stores plan, iteration history, accumulated feedback.

#### 3.2 Live Progress Dashboard
**What:** Real-time execution monitoring
**Why:** Visibility into long-running tasks
**How:** Optional WebSocket or file-based progress updates that can be consumed by a UI.

### Priority 4: Low (Nice-to-Have)

#### 4.1 Document Import
**What:** Convert PRDs/specs to goals+context
**Why:** Smoother onboarding
**How:** Pre-processing step that uses Claude to extract actionable goals.

#### 4.2 Error Pattern Classification
**What:** Categorize and track error patterns
**Why:** Better stuck-loop detection
**How:** Error fingerprinting and classification.

---

## Comparative Analysis Matrix

| Feature | Ralph | Fireteam | Winner | Gap Severity |
|---------|-------|----------|--------|--------------|
| Complexity-based routing | No | Yes (4 levels) | **Fireteam** | N/A |
| Parallel reviews | No | Yes (3 reviewers) | **Fireteam** | N/A |
| Planning phase | No | Yes (FULL mode) | **Fireteam** | N/A |
| Test feedback injection | Partial | Yes (hooks) | **Fireteam** | N/A |
| Library-first design | No | Yes | **Fireteam** | N/A |
| **Uses Claude Code session** | Yes | No (separate API) | **Ralph** | **Critical** |
| Circuit breaker | Yes (sophisticated) | No | **Ralph** | **Critical** |
| Rate limiting | Yes | No | **Ralph** | **Critical** |
| Session continuity | Yes (24h) | No | **Ralph** | Medium |
| Dual-gate exit | Yes | No | **Ralph** | Medium |
| Live monitoring | Yes (tmux) | No | **Ralph** | Low |
| PRD import | Yes | No | **Ralph** | Low |

---

## Implementation Status

**All gaps have been closed.** The following features have been implemented:

| Gap | Status | Implementation |
|-----|--------|----------------|
| Claude Code session | ✅ DONE | `claude_cli.py` - wraps `claude` CLI |
| Circuit breaker | ✅ DONE | `circuit_breaker.py` - warns on stuck loops |
| Rate limiting | ✅ DONE | `rate_limiter.py` - 100 calls/hour default |
| Dual-gate exit | ✅ DONE | `WORK_COMPLETE:` signal in loops.py |
| Session continuity | ✅ DONE | Uses Claude Code's `--resume` |
| Live monitoring | ✅ DONE | `runner.py` - tmux-based execution |

### New Architecture

```
Before (SDK direct):
Claude Code → Fireteam → claude-agent-sdk → Anthropic API (separate billing)

After (CLI wrapper):
Claude Code → Fireteam → claude CLI subprocess → Claude Code session (same billing)
```

### CLI Commands

```bash
# Start autonomous session in tmux
fireteam start --project-dir /path --goal "Complete the feature"

# List running sessions
fireteam list

# Attach to session for live monitoring
fireteam attach fireteam-myproject

# View recent logs
fireteam logs fireteam-myproject -n 100

# Terminate session
fireteam kill fireteam-myproject
```

---

## Conclusion

Fireteam now has feature parity with Ralph's safety mechanisms while maintaining its architectural advantages:

**Fireteam's advantages over Ralph:**
- Adaptive complexity routing (trivial → complex)
- Parallel reviewer consensus (3 reviewers, 2/3 majority)
- Clean Python library API for embedding
- Type-safe, async-native codebase

**Ralph's features now in Fireteam:**
- Claude Code session piggybacking (unified billing)
- Circuit breaker (stuck loop detection)
- Rate limiting (API budget management)
- Tmux-based autonomous execution
- Session continuity
- Dual-gate exit detection

**Result:** Fireteam's intelligent orchestration + Ralph's "just works with Claude Code" integration model.
