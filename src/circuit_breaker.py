"""
Circuit breaker pattern for fireteam execution loops.

Detects stuck loops and warns (but doesn't halt) when patterns indicate
the loop is not making progress. Tracks:
- Files changed per iteration
- Repeated identical errors
- Output length trends
"""

import hashlib
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    HALF_OPEN = "half_open"  # Testing if issue resolved
    OPEN = "open"          # Problem detected, warning issued


@dataclass
class IterationMetrics:
    """Metrics collected for a single iteration."""
    iteration: int
    files_changed: int = 0
    output_length: int = 0
    error_hash: str | None = None
    completion_percentage: int = 0

    @staticmethod
    def hash_error(error: str | None) -> str | None:
        """Create a hash of an error for comparison."""
        if not error:
            return None
        return hashlib.md5(error.encode()).hexdigest()[:16]


@dataclass
class CircuitBreaker:
    """
    Circuit breaker for detecting stuck execution loops.

    Monitors iteration metrics and warns when patterns suggest
    the loop is stuck. Does NOT halt execution - just warns.

    Thresholds (configurable):
    - no_progress_threshold: Consecutive iterations with 0 files changed
    - repeated_error_threshold: Consecutive identical errors
    - output_decline_threshold: Percentage decline in output length
    """

    # Thresholds
    no_progress_threshold: int = 3
    repeated_error_threshold: int = 5
    output_decline_threshold: float = 0.7  # 70% decline

    # State tracking
    state: CircuitState = field(default=CircuitState.CLOSED)
    no_progress_count: int = 0
    repeated_error_count: int = 0
    last_error_hash: str | None = None
    output_lengths: list[int] = field(default_factory=list)
    metrics_history: list[IterationMetrics] = field(default_factory=list)

    # Callbacks
    on_warning: Callable[[str], None] | None = None

    def __post_init__(self) -> None:
        self.log = logging.getLogger("fireteam.circuit_breaker")

    def record_iteration(self, metrics: IterationMetrics) -> None:
        """
        Record metrics from an iteration and update circuit state.

        Args:
            metrics: Metrics from the completed iteration
        """
        self.metrics_history.append(metrics)
        self.output_lengths.append(metrics.output_length)

        # Check for no progress
        if metrics.files_changed == 0:
            self.no_progress_count += 1
        else:
            self.no_progress_count = 0

        # Check for repeated errors
        if metrics.error_hash:
            if metrics.error_hash == self.last_error_hash:
                self.repeated_error_count += 1
            else:
                self.repeated_error_count = 0
            self.last_error_hash = metrics.error_hash
        else:
            self.repeated_error_count = 0
            self.last_error_hash = None

        # Update state and issue warnings
        self._update_state(metrics)

    def _update_state(self, metrics: IterationMetrics) -> None:
        """Update circuit state based on current metrics."""
        warnings = []

        # Check no progress threshold
        if self.no_progress_count >= self.no_progress_threshold:
            warnings.append(
                f"No files changed in {self.no_progress_count} consecutive iterations"
            )

        # Check repeated error threshold
        if self.repeated_error_count >= self.repeated_error_threshold:
            warnings.append(
                f"Same error repeated {self.repeated_error_count} times"
            )

        # Check output decline
        if len(self.output_lengths) >= 3:
            recent = self.output_lengths[-3:]
            if recent[0] > 0:
                decline = 1 - (recent[-1] / recent[0])
                if decline >= self.output_decline_threshold:
                    warnings.append(
                        f"Output length declined {decline:.0%} over last 3 iterations"
                    )

        # Update state
        if warnings:
            self.state = CircuitState.OPEN
            self._issue_warnings(warnings, metrics)
        elif self.state == CircuitState.OPEN:
            # Recovery detected
            self.state = CircuitState.HALF_OPEN
            self.log.info("Circuit breaker: Recovery detected, moving to HALF_OPEN")
        elif self.state == CircuitState.HALF_OPEN:
            # Confirmed recovery
            self.state = CircuitState.CLOSED
            self.log.info("Circuit breaker: Confirmed recovery, moving to CLOSED")

    def _issue_warnings(self, warnings: list[str], metrics: IterationMetrics) -> None:
        """Issue warnings about potential stuck loop."""
        msg = (
            f"[CIRCUIT BREAKER WARNING] Iteration {metrics.iteration}: "
            f"Potential stuck loop detected:\n"
            + "\n".join(f"  - {w}" for w in warnings)
        )

        self.log.warning(msg)

        if self.on_warning:
            self.on_warning(msg)

    def is_open(self) -> bool:
        """Check if circuit is open (problem detected)."""
        return self.state == CircuitState.OPEN

    def get_status(self) -> dict[str, str | int | bool]:
        """Get current circuit breaker status."""
        return {
            "state": self.state.value,
            "no_progress_count": self.no_progress_count,
            "repeated_error_count": self.repeated_error_count,
            "iterations_recorded": len(self.metrics_history),
            "warnings_issued": self.state == CircuitState.OPEN,
        }

    def reset(self) -> None:
        """Reset circuit breaker to initial state."""
        self.state = CircuitState.CLOSED
        self.no_progress_count = 0
        self.repeated_error_count = 0
        self.last_error_hash = None
        self.output_lengths.clear()
        self.metrics_history.clear()


def create_circuit_breaker(
    no_progress_threshold: int = 3,
    repeated_error_threshold: int = 5,
    output_decline_threshold: float = 0.7,
    on_warning: Callable[[str], None] | None = None,
) -> CircuitBreaker:
    """
    Create a configured circuit breaker.

    Args:
        no_progress_threshold: Iterations with no file changes before warning
        repeated_error_threshold: Repeated identical errors before warning
        output_decline_threshold: Output length decline percentage before warning
        on_warning: Callback when warning is issued

    Returns:
        Configured CircuitBreaker instance
    """
    return CircuitBreaker(
        no_progress_threshold=no_progress_threshold,
        repeated_error_threshold=repeated_error_threshold,
        output_decline_threshold=output_decline_threshold,
        on_warning=on_warning,
    )
