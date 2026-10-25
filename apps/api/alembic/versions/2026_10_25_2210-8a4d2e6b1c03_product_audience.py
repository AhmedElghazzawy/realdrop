"""product_audience

`products.audience` ('men' | 'women' | NULL): who a product is for, when the shop says so plainly.
Collectors set it (collectors/base.py RawProduct.audience); the catalog's men-only list filters on
it. Existing DeFacto rows are backfilled from the root of their category path, as the collector now
does: 'Erkek > ...' is men, 'Kadın > ...' is women, anything else (kids, babies) stays NULL.

Revision ID: 8a4d2e6b1c03
Revises: 5e1f0c3a9b27
Create Date: 2026-10-25 22:10:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "8a4d2e6b1c03"
down_revision: str | Sequence[str] | None = "5e1f0c3a9b27"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("products", sa.Column("audience", sa.String(length=8), nullable=True))
    op.create_check_constraint(
        op.f("ck_products_audience_values"), "products", "audience IN ('men', 'women')"
    )
    op.execute(
        """
        UPDATE products SET audience = CASE
            WHEN category_raw LIKE 'Erkek > %' THEN 'men'
            WHEN category_raw LIKE 'Kadın > %' THEN 'women'
        END
        """
    )
    op.create_index(op.f("ix_products_audience"), "products", ["audience"])


def downgrade() -> None:
    op.drop_index(op.f("ix_products_audience"), table_name="products")
    op.drop_constraint(op.f("ck_products_audience_values"), "products", type_="check")
    op.drop_column("products", "audience")
