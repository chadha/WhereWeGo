"""Small in-process sliding-window rate limiter for public endpoints.

Edge protection in AWS is AWS WAF; this keeps the local service safe from accidental loops.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from collections.abc import Callable


class RateLimiter:
    def __init__(self, limit_per_minute: int, clock: Callable[[], float] = time.monotonic) -> None:
        self.limit = max(1, limit_per_minute)
        self._clock = clock
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = self._clock()
        window = self._hits[key]
        while window and now - window[0] > 60:
            window.popleft()
        if len(window) >= self.limit:
            return False
        window.append(now)
        return True
