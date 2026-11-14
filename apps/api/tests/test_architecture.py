"""Architecture rules, checked on every test run (docs/architecture/overview.md, "Layers").

Each rule is "modules matching X must not import Y". Imports are read with `ast`, so the rules see
exactly what the code imports, including imports inside functions. When a rule fails, fix the code;
change a rule only together with the architecture doc (and an ADR if the layering itself changes).
"""

import ast
from dataclasses import dataclass
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
PACKAGE = SRC / "realdrop"


@dataclass(frozen=True)
class Rule:
    name: str
    applies_to: tuple[str, ...]  # module prefixes, e.g. "realdrop.pricing"
    forbidden: tuple[str, ...]  # import prefixes the modules must not use
    exempt: tuple[str, ...] = ()  # modules inside applies_to that the rule skips
    allowed: tuple[str, ...] = ()  # narrower imports that stay allowed despite `forbidden`


RULES = (
    Rule(
        "pricing is pure: no database, HTTP, web framework or other app layers",
        applies_to=("realdrop.pricing",),
        forbidden=(
            "sqlalchemy",
            "httpx",
            "fastapi",
            "realdrop.db",
            "realdrop.models",
            "realdrop.services",
            "realdrop.api",
            "realdrop.pipeline",
            "realdrop.collectors",
        ),
    ),
    Rule(
        "catalog rules are pure: text in, categories and attributes out",
        applies_to=(
            "realdrop.pipeline.tagger",
            "realdrop.pipeline.categorize",
            "realdrop.pipeline.keywords",
        ),
        forbidden=(
            "sqlalchemy",
            "httpx",
            "realdrop.db",
            "realdrop.models",
            "realdrop.collectors",
            "realdrop.services",
            "realdrop.api",
        ),
    ),
    Rule(
        "parsers are pure: HTML/JSON in, RawProduct out, no IO",
        applies_to=(
            "realdrop.collectors.money",
            "realdrop.collectors.sitemap",
            "realdrop.collectors.robots",
            "realdrop.collectors.*.parser",
        ),
        forbidden=(
            "httpx",
            "sqlalchemy",
            "realdrop.db",
            "realdrop.models",
            "realdrop.pipeline",
            "realdrop.collectors.http",
        ),
    ),
    Rule(
        "collectors fetch and parse; only the run entry point touches storage",
        applies_to=("realdrop.collectors",),
        exempt=("realdrop.collectors.run",),
        forbidden=(
            "sqlalchemy",
            "realdrop.db",
            "realdrop.models",
            "realdrop.pipeline",
            "realdrop.services",
            "realdrop.api",
        ),
    ),
    Rule(
        "model calls never touch storage: text in, structured answers out (callers persist)",
        applies_to=("realdrop.ai",),
        forbidden=("sqlalchemy", "realdrop.db", "realdrop.models", "realdrop.services", "fastapi"),
    ),
    Rule(
        "routes are thin: they call services, never models, SQL or the pipeline",
        applies_to=("realdrop.api",),
        forbidden=("sqlalchemy", "realdrop.models", "realdrop.pipeline", "realdrop.collectors"),
        allowed=("sqlalchemy.ext.asyncio",),  # the AsyncSession type for dependency injection
    ),
    Rule(
        "only the HTTP layer knows about FastAPI",
        applies_to=(
            "realdrop.services",
            "realdrop.pipeline",
            "realdrop.pricing",
            "realdrop.models",
            "realdrop.schemas",
            "realdrop.collectors",
            "realdrop.db",
        ),
        forbidden=("fastapi", "starlette", "realdrop.api"),
    ),
    Rule(
        "data definitions do not depend on behaviour",
        applies_to=("realdrop.models", "realdrop.schemas", "realdrop.db"),
        forbidden=("realdrop.services", "realdrop.pipeline", "realdrop.collectors", "realdrop.api"),
    ),
)


def module_name(path: Path) -> str:
    parts = path.relative_to(SRC).with_suffix("").parts
    return ".".join(parts[:-1] if parts[-1] == "__init__" else parts)


def imports_of(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            found.add(node.module)
    return found


def matches(module: str, prefix: str) -> bool:
    if "*" in prefix:  # one wildcard segment: realdrop.collectors.*.parser
        want, got = prefix.split("."), module.split(".")
        return len(want) == len(got) and all(w in ("*", g) for w, g in zip(want, got, strict=True))
    return module == prefix or module.startswith(prefix + ".")


MODULES = {module_name(p): imports_of(p) for p in sorted(PACKAGE.rglob("*.py"))}


@pytest.mark.parametrize("rule", RULES, ids=lambda r: r.name)
def test_layering(rule: Rule) -> None:
    violations = [
        f"{module} imports {imported}"
        for module, imported_names in MODULES.items()
        if any(matches(module, p) for p in rule.applies_to)
        and not any(matches(module, e) for e in rule.exempt)
        for imported in sorted(imported_names)
        if any(matches(imported, f) for f in rule.forbidden)
        and not any(matches(imported, a) for a in rule.allowed)
    ]
    assert not violations, f"{rule.name}:\n  " + "\n  ".join(violations)


def test_every_rule_applies_to_some_module() -> None:
    """A rule whose prefixes match nothing (after a rename) would pass silently forever."""
    for rule in RULES:
        assert any(any(matches(m, p) for p in rule.applies_to) for m in MODULES), rule.name
