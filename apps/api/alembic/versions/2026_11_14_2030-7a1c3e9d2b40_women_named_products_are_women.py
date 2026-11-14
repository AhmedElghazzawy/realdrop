"""women-named products are women

Data fix, no schema change. Some shops mis-file women's items under men: Colin's lists "Kadın ...
Şort" under "Erkek Giyim", Damat Tween files "Kadin Elbise" in a men's catalog, and Hatemoğlu's
women's line ("Koleksiyon > Saykı > Saykı Woman > ...") got the brand's men default. From now on
RawProduct sets them to women when collected (collectors/base.py); the collectors that keep men
only then skip them, so the rows already stored would never be corrected. This does it once, with
the same rule: a whole word naming women in the title or shop category, and no "unisex".

Revision ID: 7a1c3e9d2b40
Revises: 394bf33a1eed
Create Date: 2026-11-14 20:30:00

"""

from collections.abc import Sequence

from alembic import op

revision: str = "7a1c3e9d2b40"
down_revision: str | Sequence[str] | None = "394bf33a1eed"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Word boundaries spelled out: \m and \M depend on the server locale's idea of a letter, and "ı"
# must count as one (so "Kadınlar" does not match).
_TEXT = "(title_raw || ' ' || coalesce(category_raw, ''))"
_EDGE = "[^[:alnum:]ıİ]"
_WOMEN = rf"(^|{_EDGE})(kad[ıi]n|woman|women|bayan)($|{_EDGE})"


def upgrade() -> None:
    op.execute(
        f"UPDATE products SET audience = 'women' "
        f"WHERE audience = 'men' AND {_TEXT} ~* '{_WOMEN}' AND {_TEXT} !~* 'unisex'"
    )


def downgrade() -> None:
    # The old values were wrong; there is nothing worth restoring.
    pass
