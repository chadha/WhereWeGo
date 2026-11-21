"""Bounded retries and a simple circuit breaker.

No unlimited loops: retries are capped and only transient failures are retried.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field


class TransientProviderError(Exception):
    """Timeout, connection error, 429 or 5xx: worth retrying."""


class PermanentProviderError(Exception):
    """Bad credentials, bad request or malformed payload: never retried."""


class CircuitOpenError(Exception):
    """The provider has failed repeatedly; calls are short-circuited until cooldown ends."""


@dataclass
class CircuitBreaker:
    failure_threshold: int = 5
    cooldown_seconds: float = 30.0
    clock: Callable[[], float] = time.monotonic
    _failures: int = field(default=0, init=False)
    _opened_at: float | None = field(default=None, init=False)

    @property
    def is_open(self) -> bool:
        if self._opened_at is None:
            return False
        if self.clock() - self._opened_at >= self.cooldown_seconds:
            # Half-open: allow one trial call.
            self._opened_at = None
            self._failures = self.failure_threshold - 1
            return False
        return True

    def record_success(self) -> None:
        self._failures = 0
        self._opened_at = None

    def record_failure(self) -> None:
        self._failures += 1
        if self._failures >= self.failure_threshold:
            self._opened_at = self.clock()


@dataclass
class RetryStats:
    attempts: int = 0
    retries: int = 0


async def call_with_retries[T](
    operation: Callable[[], Awaitable[T]],
    *,
    max_retries: int,
    base_delay_seconds: float = 0.25,
    max_delay_seconds: float = 2.0,
    stats: RetryStats | None = None,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> T:
    """Run ``operation`` with at most ``max_retries`` extra attempts on transient errors."""
    max_retries = max(0, min(max_retries, 3))
    stats = stats if stats is not None else RetryStats()
    attempt = 0
    while True:
        attempt += 1
        stats.attempts = attempt
        try:
            return await operation()
        except TransientProviderError:
            if attempt > max_retries:
                raise
            stats.retries += 1
            delay = min(base_delay_seconds * (2 ** (attempt - 1)), max_delay_seconds)
            await sleep(delay)
