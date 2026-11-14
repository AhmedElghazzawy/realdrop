"""product_attributes

`product_attributes`: one row per product with canonical colours, pattern, fit, materials,
formality, season, subcategory and style tags (old_money, streetwear, ...), the basis of shop the
look, the For you feed and outfit building (Phase 5, ADR 0013). Derived data: pipeline/tagging.py
fills it after each collection run and re-tags a product when its content_hash or TAGGER_VERSION
changes, so this migration only creates the table. GIN indexes serve `style_tags && ...` and
`colors && ...` filters.

Revision ID: 394bf33a1eed
Revises: 3c7d9a1f5e20
Create Date: 2026-11-14 18:45:13.604353

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "394bf33a1eed"
down_revision: str | Sequence[str] | None = "3c7d9a1f5e20"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "product_attributes",
        sa.Column("product_id", sa.UUID(), nullable=False),
        sa.Column(
            "style_tags",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'::text[]"),
            nullable=False,
        ),
        sa.Column(
            "colors",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'::text[]"),
            nullable=False,
        ),
        sa.Column("pattern", sa.String(length=16), nullable=True),
        sa.Column("fit", sa.String(length=16), nullable=True),
        sa.Column(
            "material",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'::text[]"),
            nullable=False,
        ),
        sa.Column("formality", sa.String(length=16), nullable=True),
        sa.Column(
            "season",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'::text[]"),
            nullable=False,
        ),
        sa.Column(
            "occasion",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'::text[]"),
            nullable=False,
        ),
        sa.Column("subcategory", sa.String(length=24), nullable=True),
        sa.Column("source", sa.String(length=8), nullable=False),
        sa.Column(
            "evidence",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("tagger_version", sa.SmallInteger(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "tagged_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.CheckConstraint(
            "source IN ('rules', 'llm')", name=op.f("ck_product_attributes_source_values")
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name=op.f("fk_product_attributes_product_id_products"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("product_id", name=op.f("pk_product_attributes")),
    )
    op.create_index(
        "ix_product_attributes_colors",
        "product_attributes",
        ["colors"],
        unique=False,
        postgresql_using="gin",
    )
    op.create_index(
        "ix_product_attributes_style_tags",
        "product_attributes",
        ["style_tags"],
        unique=False,
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_product_attributes_style_tags", table_name="product_attributes", postgresql_using="gin"
    )
    op.drop_index(
        "ix_product_attributes_colors", table_name="product_attributes", postgresql_using="gin"
    )
    op.drop_table("product_attributes")
