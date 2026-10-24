"""Every brand collector that runs in production, by slug.

Adding a brand is an explicit line here (add-brand-collector skill, step 5), never automatic
discovery, so it is always obvious what the scheduler will run. `_example` is a template and is
deliberately not registered.
"""

from realdrop.collectors.base import BrandCollector
from realdrop.collectors.defacto.collector import DefactoCollector

COLLECTORS: dict[str, type[BrandCollector]] = {
    DefactoCollector.slug: DefactoCollector,
}


def get_collector_class(slug: str) -> type[BrandCollector]:
    try:
        return COLLECTORS[slug]
    except KeyError:
        known = ", ".join(sorted(COLLECTORS)) or "none yet"
        raise KeyError(f"unknown brand {slug!r} (registered: {known})") from None
