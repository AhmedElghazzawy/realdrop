"""robots.txt rules per RFC 9309.

Python's `urllib.robotparser` is not used: it ignores `*` and `$` wildcards and takes the first
matching rule instead of the most specific one. Real shops rely on both (DeFacto: `Disallow: *q=*`),
so with the stdlib parser we would quietly fetch pages the site asked us not to.

- Our group is every group naming our product token, case-insensitively
  (`realdrop-bot/0.1 (...)` -> `realdrop-bot`); if none does, the `*` group(s).
- `*` matches any run of characters, a trailing `$` anchors the end of the URL.
- The longest matching pattern wins; on a tie, Allow wins. No match means allowed.
"""

import contextlib
import re
from dataclasses import dataclass, field
from urllib.parse import urlsplit


@dataclass(frozen=True)
class _Rule:
    allow: bool
    pattern: str
    regex: re.Pattern[str]


@dataclass
class _Group:
    agents: list[str] = field(default_factory=list)
    rules: list[_Rule] = field(default_factory=list)
    crawl_delay: float | None = None


def _compile(pattern: str) -> re.Pattern[str]:
    anchored = pattern.endswith("$")
    body = pattern[:-1] if anchored else pattern
    regex = ".*".join(re.escape(part) for part in body.split("*"))
    return re.compile(regex + ("$" if anchored else ""))


def _product_token(user_agent: str) -> str:
    return user_agent.split("/", 1)[0].split(" ", 1)[0].strip().lower()


class RobotsRules:
    def __init__(self, text: str, user_agent: str) -> None:
        token = _product_token(user_agent)
        groups = _parse(text)
        ours = [g for g in groups if token in g.agents]
        if not ours:
            ours = [g for g in groups if "*" in g.agents]
        self._rules = [rule for g in ours for rule in g.rules]
        delays = [g.crawl_delay for g in ours if g.crawl_delay is not None]
        self.crawl_delay: float | None = max(delays) if delays else None

    def can_fetch(self, url: str) -> bool:
        parts = urlsplit(url)
        target = (parts.path or "/") + (f"?{parts.query}" if parts.query else "")
        if target == "/robots.txt":
            return True
        best: _Rule | None = None
        for rule in self._rules:
            if not rule.regex.match(target):
                continue
            if (
                best is None
                or len(rule.pattern) > len(best.pattern)
                or (len(rule.pattern) == len(best.pattern) and rule.allow)
            ):
                best = rule
        return best is None or best.allow


def _parse(text: str) -> list[_Group]:
    groups: list[_Group] = []
    current: _Group | None = None
    last_was_agent = False
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if ":" not in line:
            continue
        key, value = (part.strip() for part in line.split(":", 1))
        key = key.lower()
        if key == "user-agent":
            if current is None or not last_was_agent:
                current = _Group()
                groups.append(current)
            current.agents.append(value.lower())
            last_was_agent = True
            continue
        last_was_agent = False
        if current is None:
            continue
        if key in ("allow", "disallow") and value:
            current.rules.append(_Rule(key == "allow", value, _compile(value)))
        elif key == "crawl-delay":
            with contextlib.suppress(ValueError):
                current.crawl_delay = float(value)
    return groups
