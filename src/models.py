"""
Data models for fireteam execution.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ExecutionMode(Enum):
    """Execution modes for fireteam tasks."""
    SINGLE_TURN = "single_turn"  # Direct Opus call, no loop
    MODERATE = "moderate"        # Execute + review loop
    FULL = "full"                # Plan + execute + parallel reviews loop


class PhaseType(Enum):
    """Phase types within execution."""
    PLAN = "plan"
    EXECUTE = "execute"
    REVIEW = "review"


@dataclass
class ReviewResult:
    """Result from a single reviewer."""
    completion_percentage: int
    feedback: str
    issues: list[str] = field(default_factory=list)
    passed: bool = False

    @classmethod
    def from_output(cls, output: str, threshold: int = 95) -> "ReviewResult":
        """Parse a ReviewResult from reviewer output."""
        completion = _extract_completion(output)
        issues = _extract_issues(output)
        return cls(
            completion_percentage=completion,
            feedback=output,
            issues=issues,
            passed=completion >= threshold,
        )


@dataclass
class IterationState:
    """State tracked across loop iterations."""
    iteration: int = 0
    plan: str | None = None
    execution_output: str | None = None
    review_history: list[dict[str, Any]] = field(default_factory=list)
    accumulated_feedback: str = ""

    def add_review(self, reviews: list[ReviewResult]) -> None:
        """Add reviews from an iteration and update accumulated feedback."""
        self.review_history.append({
            "iteration": self.iteration,
            "reviews": [
                {
                    "completion": r.completion_percentage,
                    "passed": r.passed,
                    "issues": r.issues,
                }
                for r in reviews
            ],
        })
        self.accumulated_feedback = self._aggregate_feedback(reviews)

    def _aggregate_feedback(self, reviews: list[ReviewResult]) -> str:
        """Aggregate feedback from reviewers into actionable format."""
        if not reviews:
            return ""

        parts = []
        for i, review in enumerate(reviews, 1):
            if len(reviews) > 1:
                parts.append(f"Reviewer {i} ({review.completion_percentage}%):")
            parts.append(review.feedback[:1500])  # Truncate long feedback
            if review.issues:
                parts.append("Issues found:")
                for issue in review.issues[:5]:  # Limit issues
                    parts.append(f"  - {issue}")
            parts.append("")

        return "\n".join(parts)


@dataclass
class LoopConfig:
    """Configuration for execution loops."""
    max_iterations: int | None = None  # None = infinite (default)
    completion_threshold: int = 95
    parallel_reviewers: int = 1  # 1 for MODERATE, 3 for FULL
    majority_required: int = 1   # 1 for MODERATE, 2 for FULL


@dataclass
class ExecutionResult:
    """Result of a fireteam execution."""
    success: bool
    mode: ExecutionMode
    output: str | None = None
    error: str | None = None
    completion_percentage: int = 0
    iterations: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


def _extract_completion(text: str) -> int:
    """Extract completion percentage from review output."""
    import re
    # Look for COMPLETION: XX% pattern
    match = re.search(r'COMPLETION:\s*(\d+)%', text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    # Fallback: find any percentage
    match = re.search(r'(\d+)%', text)
    return int(match.group(1)) if match else 50


def _extract_issues(text: str) -> list[str]:
    """Extract issues list from review output."""
    import re
    issues = []

    # Look for ISSUES: section
    issues_match = re.search(r'ISSUES:\s*\n((?:[-*]\s*.+\n?)+)', text, re.IGNORECASE)
    if issues_match:
        issues_text = issues_match.group(1)
        for line in issues_text.split('\n'):
            line = line.strip()
            if line.startswith(('-', '*')):
                issue = line.lstrip('-* ').strip()
                if issue:
                    issues.append(issue)

    return issues
