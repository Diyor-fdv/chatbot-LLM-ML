from __future__ import annotations

from sqlalchemy import Date, Float, ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FactSales(Base):
    __tablename__ = "fact_sales"

    sales_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    order_id: Mapped[int] = mapped_column(Integer, index=True)
    order_date: Mapped[object] = mapped_column(Date, index=True)

    date_id: Mapped[int] = mapped_column(ForeignKey("dim_date.date_id"), index=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("dim_city.city_id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("dim_product.product_id"), index=True)

    customer_id: Mapped[int] = mapped_column(Integer, index=True)
    quantity: Mapped[int] = mapped_column(Integer)

    revenue: Mapped[float] = mapped_column(Numeric(14, 2))
    cost: Mapped[float] = mapped_column(Numeric(14, 2))
    profit: Mapped[float] = mapped_column(Numeric(14, 2))

