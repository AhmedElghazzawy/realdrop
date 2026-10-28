"""PoliteClient against a fake transport and a fake clock: no network, no real waiting."""

import asyncio
from collections.abc import Callable

import httpx
import pytest

from realdrop.collectors.http import (
    CollectorBlockedError,
    CollectorGaveUpError,
    CollectorServerError,
    PoliteClient,
)

UA = "realdrop-bot/0.1 (contact: test@example.com)"
SHOP = "https://shop.example.com"


class FakeTime:
    """A clock that only moves when the client sleeps."""

    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def clock(self) -> float:
        return self.now

    async def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


Handler = Callable[[httpx.Request], httpx.Response]


def make_client(handler: Handler, fake: FakeTime, **kwargs: float) -> PoliteClient:
    return PoliteClient(
        user_agent=UA,
        transport=httpx.MockTransport(handler),
        sleep=fake.sleep,
        clock=fake.clock,
        rng=lambda: 0.0,  # no jitter: deterministic waits
        **kwargs,  # type: ignore[arg-type]
    )


def shop(robots: str = "User-agent: *\nAllow: /\n", **routes: httpx.Response) -> Handler:
    """A fake shop: serves robots.txt plus fixed responses keyed by path (slashes as '__')."""
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text=robots)
        key = request.url.path.strip("/").replace("/", "__")
        return routes.get(key, httpx.Response(404))

    handler.seen = seen  # type: ignore[attr-defined]
    return handler


async def test_sends_user_agent_and_returns_json() -> None:
    fake = FakeTime()
    handler = shop(api__products=httpx.Response(200, json={"products": []}))
    async with make_client(handler, fake) as client:
        assert await client.get_json(f"{SHOP}/api/products") == {"products": []}
    assert all(r.headers["User-Agent"] == UA for r in handler.seen)  # type: ignore[attr-defined]


async def test_rate_limit_spaces_requests() -> None:
    fake = FakeTime()
    handler = shop(a=httpx.Response(200), b=httpx.Response(200))
    async with make_client(handler, fake, rate_limit_rps=0.5) as client:
        await client.get(f"{SHOP}/a")  # robots.txt then /a
        await client.get(f"{SHOP}/b")
    # 3 requests at 0.5 rps: the 2nd and 3rd each wait 2 s.
    assert fake.sleeps == [2.0, 2.0]


class YieldingFakeTime(FakeTime):
    """Like FakeTime, but sleeping lets other tasks run, as a real sleep does."""

    async def sleep(self, seconds: float) -> None:
        await super().sleep(seconds)
        await asyncio.sleep(0)


async def test_concurrent_callers_still_start_one_request_per_interval() -> None:
    fake = YieldingFakeTime()
    starts: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        starts.append(fake.now)
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /\n")
        return httpx.Response(200)

    async with make_client(handler, fake, rate_limit_rps=0.5) as client:
        await asyncio.gather(*(client.get(f"{SHOP}/p{n}") for n in range(4)))
    # robots.txt fetched once, then every page start 2 s after the previous one.
    assert starts == [0.0, 2.0, 4.0, 6.0, 8.0]


async def test_robots_disallow_blocks_without_requesting_the_page() -> None:
    fake = FakeTime()
    handler = shop(robots="User-agent: *\nDisallow: /private/\n", private__x=httpx.Response(200))
    async with make_client(handler, fake) as client:
        with pytest.raises(CollectorBlockedError, match=r"robots\.txt disallows"):
            await client.get(f"{SHOP}/private/x")
    paths = [r.url.path for r in handler.seen]  # type: ignore[attr-defined]
    assert paths == ["/robots.txt"]


async def test_robots_rules_for_our_bot_apply() -> None:
    fake = FakeTime()
    robots = "User-agent: realdrop-bot\nDisallow: /\n\nUser-agent: *\nAllow: /\n"
    async with make_client(shop(robots=robots, a=httpx.Response(200)), fake) as client:
        with pytest.raises(CollectorBlockedError):
            await client.get(f"{SHOP}/a")


async def test_robots_crawl_delay_slows_us_down() -> None:
    fake = FakeTime()
    handler = shop(
        robots="User-agent: *\nCrawl-delay: 5\n", a=httpx.Response(200), b=httpx.Response(200)
    )
    async with make_client(handler, fake) as client:
        await client.get(f"{SHOP}/a")
        await client.get(f"{SHOP}/b")
    assert fake.sleeps[-1] == 5.0


async def test_missing_robots_means_no_rules() -> None:
    fake = FakeTime()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404 if request.url.path == "/robots.txt" else 200)

    async with make_client(handler, fake) as client:
        assert (await client.get(f"{SHOP}/anything")).status_code == 200


async def test_unreachable_robots_means_stay_out() -> None:
    fake = FakeTime()
    async with make_client(lambda request: httpx.Response(503), fake, max_retries=1) as client:
        with pytest.raises(CollectorBlockedError, match=r"robots\.txt unreachable"):
            await client.get(f"{SHOP}/a")


@pytest.mark.parametrize("status", [401, 403])
async def test_403_stops_immediately_without_retrying(status: int) -> None:
    fake = FakeTime()
    handler = shop(a=httpx.Response(status))
    async with make_client(handler, fake) as client:
        with pytest.raises(CollectorBlockedError, match=str(status)):
            await client.get(f"{SHOP}/a")
    page_requests = [r for r in handler.seen if r.url.path == "/a"]  # type: ignore[attr-defined]
    assert len(page_requests) == 1


async def test_429_backs_off_exponentially_then_succeeds() -> None:
    fake = FakeTime()
    responses = iter([httpx.Response(429), httpx.Response(429), httpx.Response(200)])

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return next(responses)

    async with make_client(handler, fake, rate_limit_rps=1000.0) as client:
        assert (await client.get(f"{SHOP}/a")).status_code == 200
    backoffs = [s for s in fake.sleeps if s >= 1]
    assert backoffs == [2.0, 4.0]  # base 2 s, doubled


async def test_retry_after_seconds_is_honoured() -> None:
    fake = FakeTime()
    responses = iter([httpx.Response(429, headers={"Retry-After": "30"}), httpx.Response(200)])

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404) if request.url.path == "/robots.txt" else next(responses)

    async with make_client(handler, fake, rate_limit_rps=1000.0) as client:
        await client.get(f"{SHOP}/a")
    assert 30.0 in fake.sleeps


async def test_retry_after_too_long_gives_up_instead_of_hammering() -> None:
    fake = FakeTime()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(503, headers={"Retry-After": "3600"})

    async with make_client(handler, fake) as client:
        with pytest.raises(CollectorGaveUpError, match="asked us to wait 3600s"):
            await client.get(f"{SHOP}/a")


async def test_gives_up_after_max_retries() -> None:
    fake = FakeTime()
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        calls += 1
        return httpx.Response(500)

    async with make_client(handler, fake, max_retries=2) as client:
        with pytest.raises(CollectorServerError, match="after 3 attempts"):
            await client.get(f"{SHOP}/a")
    assert calls == 3


async def test_exhausted_429s_are_not_a_skippable_server_error() -> None:
    fake = FakeTime()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(429)

    async with make_client(handler, fake, max_retries=1) as client:
        with pytest.raises(CollectorGaveUpError) as caught:
            await client.get(f"{SHOP}/a")
    assert not isinstance(caught.value, CollectorServerError)


async def test_network_errors_are_retried() -> None:
    fake = FakeTime()
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        attempts += 1
        if attempts == 1:
            raise httpx.ConnectTimeout("timed out", request=request)
        return httpx.Response(200)

    async with make_client(handler, fake) as client:
        assert (await client.get(f"{SHOP}/a")).status_code == 200
    assert attempts == 2


async def test_404_raises_http_status_error_for_the_caller_to_skip() -> None:
    fake = FakeTime()
    async with make_client(shop(), fake) as client:
        with pytest.raises(httpx.HTTPStatusError):
            await client.get(f"{SHOP}/gone")


async def test_redirect_loop_is_a_skippable_server_error_without_retries() -> None:
    fake = FakeTime()
    loop = httpx.Response(301, headers={"Location": f"{SHOP}/a"})
    handler = shop(a=loop)
    async with make_client(handler, fake) as client:
        with pytest.raises(CollectorServerError, match="redirect loop"):
            await client.get(f"{SHOP}/a")
    hits = [r for r in handler.seen if r.url.path == "/a"]  # type: ignore[attr-defined]
    assert len(hits) == 6  # the first request and 5 redirects, then stop: no retries
