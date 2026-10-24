"""catalog_prices_runs

Tables: brands, products, variants, collection_runs, price_observations, price_daily.
Reviewed by hand after autogenerate: extensions added, enum types dropped on downgrade,
index renamed.

Revision ID: cc0bdde53854
Revises:
Create Date: 2026-10-24 17:21:56.587690

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "cc0bdde53854"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Extensions are also installed by infra/initdb in local Docker, but a fresh server or test
    # database only gets them here. Never dropped on downgrade: other objects may depend on them.
    for extension in ("vector", "unaccent", "pg_trgm"):
        op.execute(f"CREATE EXTENSION IF NOT EXISTS {extension}")

    op.create_table(
        "brands",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("country", sa.String(length=2), server_default="TR", nullable=False),
        sa.Column("currency", sa.String(length=3), server_default="TRY", nullable=False),
        sa.Column("base_url", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "collector_config",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_brands")),
        sa.UniqueConstraint("slug", name=op.f("uq_brands_slug")),
    )
    op.create_table(
        "collection_runs",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("brand_id", sa.UUID(), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            sa.Enum("running", "succeeded", "partial", "failed", name="run_status"),
            server_default="running",
            nullable=False,
        ),
        sa.Column("items_seen", sa.Integer(), server_default="0", nullable=False),
        sa.Column("items_failed", sa.Integer(), server_default="0", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["brand_id"],
            ["brands.id"],
            name=op.f("fk_collection_runs_brand_id_brands"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_collection_runs")),
    )
    op.create_table(
        "products",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("brand_id", sa.UUID(), nullable=False),
        sa.Column("external_id", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("title_raw", sa.Text(), nullable=False),
        sa.Column("description_raw", sa.Text(), nullable=True),
        sa.Column(
            "image_urls",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'::text[]"),
            nullable=False,
        ),
        sa.Column("category_raw", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.ForeignKeyConstraint(
            ["brand_id"],
            ["brands.id"],
            name=op.f("fk_products_brand_id_brands"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_products")),
        sa.UniqueConstraint(
            "brand_id", "external_id", name=op.f("uq_products_brand_id_external_id")
        ),
    )
    op.create_table(
        "variants",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("product_id", sa.UUID(), nullable=False),
        sa.Column("external_sku", sa.Text(), nullable=False),
        sa.Column("size_label", sa.Text(), nullable=True),
        sa.Column("size_normalized", sa.Text(), nullable=True),
        sa.Column("color_raw", sa.Text(), nullable=True),
        sa.Column("color_normalized", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name=op.f("fk_variants_product_id_products"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_variants")),
        sa.UniqueConstraint(
            "product_id", "external_sku", name=op.f("uq_variants_product_id_external_sku")
        ),
    )
    op.create_table(
        "price_daily",
        sa.Column("variant_id", sa.UUID(), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("close_price_minor", sa.BigInteger(), nullable=False),
        sa.Column("low_price_minor", sa.BigInteger(), nullable=False),
        sa.Column("high_price_minor", sa.BigInteger(), nullable=False),
        sa.Column("claimed_original_minor", sa.BigInteger(), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("in_stock_close", sa.Boolean(), nullable=False),
        sa.CheckConstraint(
            "low_price_minor <= close_price_minor AND close_price_minor <= high_price_minor",
            name=op.f("ck_price_daily_low_close_high_order"),
        ),
        sa.CheckConstraint("low_price_minor > 0", name=op.f("ck_price_daily_low_positive")),
        sa.ForeignKeyConstraint(
            ["variant_id"],
            ["variants.id"],
            name=op.f("fk_price_daily_variant_id_variants"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("variant_id", "snapshot_date", name=op.f("pk_price_daily")),
    )
    op.create_table(
        "price_observations",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("variant_id", sa.UUID(), nullable=False),
        sa.Column("run_id", sa.UUID(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("price_minor", sa.BigInteger(), nullable=False),
        sa.Column("original_price_minor", sa.BigInteger(), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("in_stock", sa.Boolean(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("confirmed", "pending", "rejected", name="price_status"),
            nullable=False,
        ),
        sa.Column("reject_reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["collection_runs.id"],
            name=op.f("fk_price_observations_run_id_collection_runs"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["variant_id"],
            ["variants.id"],
            name=op.f("fk_price_observations_variant_id_variants"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_price_observations")),
    )
    op.create_index(
        op.f("ix_price_observations_variant_id_observed_at"),
        "price_observations",
        ["variant_id", "observed_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_price_observations_variant_id_observed_at"), table_name="price_observations"
    )
    op.drop_table("price_observations")
    op.drop_table("price_daily")
    op.drop_table("variants")
    op.drop_table("products")
    op.drop_table("collection_runs")
    op.drop_table("brands")
    # Autogenerate does not drop Postgres enum types; without this a downgrade + upgrade fails.
    sa.Enum(name="price_status").drop(op.get_bind(), checkfirst=False)
    sa.Enum(name="run_status").drop(op.get_bind(), checkfirst=False)
