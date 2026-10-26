"""product_category

`products.category`: our own category ('tshirts', 'jeans', ...; pipeline/categorize.py), from the
shop's category and the title with fixed keyword rules, for the web app's menu and filters. NULL
when no rule matches. The store sets it on every sighting, so a rule change reaches every product
within a day; this migration fills in the rows that exist now, using today's rules.

Revision ID: 3c7d9a1f5e20
Revises: 8a4d2e6b1c03
Create Date: 2026-10-27 02:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from realdrop.pipeline.categorize import categorize

revision: str = "3c7d9a1f5e20"
down_revision: str | Sequence[str] | None = "8a4d2e6b1c03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("products", sa.Column("category", sa.String(length=16), nullable=True))
    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id, category_raw, title_raw FROM products")).all()
    updates = [
        {"id": id_, "category": category}
        for id_, raw, title in rows
        if (category := categorize(raw, title)) is not None
    ]
    if updates:
        bind.execute(sa.text("UPDATE products SET category = :category WHERE id = :id"), updates)
    op.create_index(op.f("ix_products_category"), "products", ["category"])


def downgrade() -> None:
    op.drop_index(op.f("ix_products_category"), table_name="products")
    op.drop_column("products", "category")
