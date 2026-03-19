"""init star schema

Revision ID: 0001_init
Revises: 
Create Date: 2026-03-19

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dim_city",
        sa.Column("city_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("city_name", sa.String(length=200), nullable=False),
        sa.Column("region", sa.String(length=200), nullable=True),
    )
    op.create_index("ix_dim_city_city_name", "dim_city", ["city_name"], unique=True)
    op.create_index("ix_dim_city_region", "dim_city", ["region"], unique=False)

    op.create_table(
        "dim_product",
        sa.Column("product_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("product_name", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=200), nullable=False),
    )
    op.create_index("ix_dim_product_product_name", "dim_product", ["product_name"], unique=True)
    op.create_index("ix_dim_product_category", "dim_product", ["category"], unique=False)

    op.create_table(
        "dim_date",
        sa.Column("date_id", sa.Integer(), primary_key=True, autoincrement=False),
        sa.Column("full_date", sa.Date(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("day", sa.Integer(), nullable=False),
        sa.Column("week", sa.Integer(), nullable=False),
    )
    op.create_index("ix_dim_date_full_date", "dim_date", ["full_date"], unique=True)
    op.create_index("ix_dim_date_year", "dim_date", ["year"], unique=False)
    op.create_index("ix_dim_date_month", "dim_date", ["month"], unique=False)
    op.create_index("ix_dim_date_day", "dim_date", ["day"], unique=False)
    op.create_index("ix_dim_date_week", "dim_date", ["week"], unique=False)

    op.create_table(
        "fact_sales",
        sa.Column("sales_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("order_date", sa.Date(), nullable=False),
        sa.Column("date_id", sa.Integer(), sa.ForeignKey("dim_date.date_id"), nullable=False),
        sa.Column("city_id", sa.Integer(), sa.ForeignKey("dim_city.city_id"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("dim_product.product_id"), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("revenue", sa.Numeric(14, 2), nullable=False),
        sa.Column("cost", sa.Numeric(14, 2), nullable=False),
        sa.Column("profit", sa.Numeric(14, 2), nullable=False),
    )
    op.create_index("ix_fact_sales_order_id", "fact_sales", ["order_id"], unique=False)
    op.create_index("ix_fact_sales_order_date", "fact_sales", ["order_date"], unique=False)
    op.create_index("ix_fact_sales_date_id", "fact_sales", ["date_id"], unique=False)
    op.create_index("ix_fact_sales_city_id", "fact_sales", ["city_id"], unique=False)
    op.create_index("ix_fact_sales_product_id", "fact_sales", ["product_id"], unique=False)
    op.create_index("ix_fact_sales_customer_id", "fact_sales", ["customer_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_fact_sales_customer_id", table_name="fact_sales")
    op.drop_index("ix_fact_sales_product_id", table_name="fact_sales")
    op.drop_index("ix_fact_sales_city_id", table_name="fact_sales")
    op.drop_index("ix_fact_sales_date_id", table_name="fact_sales")
    op.drop_index("ix_fact_sales_order_date", table_name="fact_sales")
    op.drop_index("ix_fact_sales_order_id", table_name="fact_sales")
    op.drop_table("fact_sales")

    op.drop_index("ix_dim_date_week", table_name="dim_date")
    op.drop_index("ix_dim_date_day", table_name="dim_date")
    op.drop_index("ix_dim_date_month", table_name="dim_date")
    op.drop_index("ix_dim_date_year", table_name="dim_date")
    op.drop_index("ix_dim_date_full_date", table_name="dim_date")
    op.drop_table("dim_date")

    op.drop_index("ix_dim_product_category", table_name="dim_product")
    op.drop_index("ix_dim_product_product_name", table_name="dim_product")
    op.drop_table("dim_product")

    op.drop_index("ix_dim_city_region", table_name="dim_city")
    op.drop_index("ix_dim_city_city_name", table_name="dim_city")
    op.drop_table("dim_city")

