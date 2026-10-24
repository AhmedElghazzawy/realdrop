"""The polite HTTP client every collector must use (CLAUDE.md rule 8).

- Identifies itself with COLLECTOR_USER_AGENT.
- At most `rate_limit_rps` requests per second, plus random jitter; honours robots.txt Crawl-delay.
- Obeys robots.txt (RFC 9309: 4xx means no rules, unreachable means stay out).
- Retries 429, 5xx and network errors with exponential backoff, honouring Retry-After.
- Stops on 401/403: raises CollectorBlockedError. Never retries, rotates, or works around a block.

`sleep`, `clock` and `rng` are injectable so tests run instantly and deterministically.
"""

import asyncio
import random
import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx


class CollectorError(Exception):
    """Base class for collection problems that end a brand's run."""


class CollectorBlockedError(CollectorError):
    """403/401, or robots.txt says no. Stop this brand and tell the owner; do not work around it."""


class CollectorGaveUpError(CollectorError):
    """Retries exhausted, or the server asked us to wait longer than we are willing to."""


class PoliteClient:
    def __init__(
        self,
        *,
        user_agent: str,
        rate_limit_rps: float = 1.0,
        max_retries: int = 4,
        backoff_base_s: float = 2.0,
        max_wait_s: float = 300.0,
        timeout_s: float = 20.0,
        transport: httpx.AsyncBaseTransport | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        clock: Callable[[], float] = time.monotonic,
        rng: Callable[[], float] = random.random,
    ) -> None:
        self._user_agent = user_agent
        self._min_interval_s = 1.0 / rate_limit_rps
        self._max_retries = max_retries
        self._backoff_base_s = backoff_base_s
        self._max_wait_s = max_wait_s
        self._sleep = sleep
        self._clock = clock
        self._rng = rng
        self._next_request_at = 0.0
        # Parsed robots.txt per origin; None means "no rules" (robots.txt was a 4xx).
        self._robots: dict[str, RobotFileParser | None] = {}
        self._http = httpx.AsyncClient(
            headers={"User-Agent": user_agent, "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.5"},
            timeout=timeout_s,
            follow_redirects=True,
            transport=transport,
        )

    async def __aenter__(self) -> "PoliteClient":
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._http.aclose()

    async def get(self, url: str, *, params: dict[str, Any] | None = None) -> httpx.Response:
        """GET a URL politely. Raises CollectorBlockedError, CollectorGaveUpError, or
        httpx.HTTPStatusError for other 4xx (e.g. a 404 product, which the caller may skip)."""
        await self._check_robots(url)
        response = await self._send(url, params)
        if response.status_code in (401, 403):
            raise CollectorBlockedError(f"HTTP {response.status_code} from {url}")
        response.raise_for_status()
        return response

    async def get_json(self, url: str, *, params: dict[str, Any] | None = None) -> Any:
        return (await self.get(url, params=params)).json()

    async def _send(self, url: str, params: dict[str, Any] | None) -> httpx.Response:
        """Rate-limited GET with retries. Returns the first non-retryable response."""
        for attempt in range(self._max_retries + 1):
            await self._wait_for_turn()
            retry_after: str | None = None
            try:
                response = await self._http.get(url, params=params)
            except httpx.TransportError as exc:
                problem = f"{type(exc).__name__}: {exc}"
            else:
                if response.status_code != 429 and response.status_code < 500:
                    return response
                problem = f"HTTP {response.status_code}"
                retry_after = response.headers.get("Retry-After")

            if attempt == self._max_retries:
                raise CollectorGaveUpError(f"{problem} from {url} after {attempt + 1} attempts")
            await self._sleep(self._backoff_s(attempt, retry_after, url))
        raise AssertionError("unreachable")

    async def _wait_for_turn(self) -> None:
        now = self._clock()
        if now < self._next_request_at:
            await self._sleep(self._next_request_at - now)
            now = self._next_request_at
        jitter = self._rng() * 0.5 * self._min_interval_s
        self._next_request_at = now + self._min_interval_s + jitter

    def _backoff_s(self, attempt: int, retry_after: str | None, url: str) -> float:
        if retry_after is not None:
            wanted = _parse_retry_after(retry_after)
            if wanted is not None:
                if wanted > self._max_wait_s:
                    raise CollectorGaveUpError(f"{url} asked us to wait {wanted:.0f}s")
                return wanted
        exponential = self._backoff_base_s * 2**attempt + self._rng() * self._backoff_base_s
        return min(exponential, self._max_wait_s)

    async def _check_robots(self, url: str) -> None:
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        if origin not in self._robots:
            self._robots[origin] = await self._load_robots(origin)
        rules = self._robots[origin]
        if rules is None:
            return
        if not rules.can_fetch(self._user_agent, url):
            raise CollectorBlockedError(f"robots.txt disallows {url}")
        delay = rules.crawl_delay(self._user_agent)
        if delay is not None and float(delay) > self._min_interval_s:
            self._min_interval_s = float(delay)

    async def _load_robots(self, origin: str) -> RobotFileParser | None:
        try:
            response = await self._send(f"{origin}/robots.txt", None)
        except CollectorGaveUpError as exc:
            raise CollectorBlockedError(f"robots.txt unreachable at {origin}: {exc}") from exc
        if 400 <= response.status_code < 500:
            return None
        rules = RobotFileParser()
        rules.parse(response.text.splitlines())
        return rules


def _parse_retry_after(value: str) -> float | None:
    """Retry-After is either delta-seconds ("120") or an HTTP date."""
    value = value.strip()
    if value.isdigit():
        return float(value)
    try:
        when = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    return max(0.0, (when - datetime.now(UTC)).total_seconds())
