"""
Rate limiting for fireteam API calls.

Implements per-hour API call quotas to prevent runaway costs.
Tracks call counts and can pause execution when quota is exhausted.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta


@dataclass
class RateLimiter:
    """
    Rate limiter for API call budget management.

    Tracks calls per hour and can optionally pause when quota
    is exhausted, waiting for the next hour window.

    Attributes:
        calls_per_hour: Maximum calls allowed per hour
        wait_on_limit: If True, wait for reset instead of raising
        calls_this_hour: Current count of calls this hour
        hour_started: When the current hour window started
    """

    calls_per_hour: int = 100
    wait_on_limit: bool = True
    calls_this_hour: int = 0
    hour_started: float = field(default_factory=time.time)
    total_calls: int = 0

    def __post_init__(self):
        self.log = logging.getLogger("fireteam.rate_limiter")
        self._lock = asyncio.Lock()

    def _is_new_hour(self) -> bool:
        """Check if we've entered a new hour window."""
        elapsed = time.time() - self.hour_started
        return elapsed >= 3600  # 1 hour

    def _reset(self) -> None:
        """Reset counters for new hour."""
        self.calls_this_hour = 0
        self.hour_started = time.time()
        self.log.info("Rate limiter: Hour window reset")

    def _seconds_until_reset(self) -> float:
        """Calculate seconds until next hour window."""
        elapsed = time.time() - self.hour_started
        remaining = 3600 - elapsed
        return max(0, remaining)

    async def acquire(self) -> None:
        """
        Acquire permission to make an API call.

        If quota is exhausted and wait_on_limit is True, waits
        for the next hour window. Otherwise raises RateLimitExceeded.

        Raises:
            RateLimitExceeded: If quota exhausted and wait_on_limit is False
        """
        async with self._lock:
            # Check if new hour
            if self._is_new_hour():
                self._reset()

            # Check quota
            if self.calls_this_hour >= self.calls_per_hour:
                if self.wait_on_limit:
                    await self._wait_for_reset()
                else:
                    raise RateLimitExceeded(
                        f"Rate limit exceeded: {self.calls_this_hour}/{self.calls_per_hour} calls this hour"
                    )

            # Increment counter
            self.calls_this_hour += 1
            self.total_calls += 1

            remaining = self.calls_per_hour - self.calls_this_hour
            if remaining <= 10:
                self.log.warning(f"Rate limiter: {remaining} calls remaining this hour")

    async def _wait_for_reset(self) -> None:
        """Wait for the next hour window."""
        wait_seconds = self._seconds_until_reset()
        if wait_seconds > 0:
            self.log.warning(
                f"Rate limit reached. Waiting {wait_seconds:.0f}s for next hour window..."
            )
            await asyncio.sleep(wait_seconds)
            self._reset()

    def get_status(self) -> dict:
        """Get current rate limiter status."""
        return {
            "calls_this_hour": self.calls_this_hour,
            "calls_per_hour": self.calls_per_hour,
            "remaining": max(0, self.calls_per_hour - self.calls_this_hour),
            "total_calls": self.total_calls,
            "seconds_until_reset": self._seconds_until_reset(),
            "quota_exhausted": self.calls_this_hour >= self.calls_per_hour,
        }

    def can_make_call(self) -> bool:
        """Check if a call can be made without waiting."""
        if self._is_new_hour():
            return True
        return self.calls_this_hour < self.calls_per_hour


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded and waiting is disabled."""
    pass


# Global rate limiter instance (can be configured per-execution)
_global_limiter: RateLimiter | None = None


def get_rate_limiter(
    calls_per_hour: int | None = None,
    wait_on_limit: bool = True,
) -> RateLimiter:
    """
    Get or create the global rate limiter.

    Args:
        calls_per_hour: Max calls per hour (None uses default/existing)
        wait_on_limit: Whether to wait when limit reached

    Returns:
        RateLimiter instance
    """
    global _global_limiter

    if _global_limiter is None or calls_per_hour is not None:
        _global_limiter = RateLimiter(
            calls_per_hour=calls_per_hour or 100,
            wait_on_limit=wait_on_limit,
        )

    return _global_limiter


def reset_rate_limiter() -> None:
    """Reset the global rate limiter."""
    global _global_limiter
    if _global_limiter:
        _global_limiter._reset()
        _global_limiter.total_calls = 0
