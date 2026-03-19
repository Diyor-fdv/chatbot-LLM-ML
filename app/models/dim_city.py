from __future__ import annotations

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DimCity(Base):
    __tablename__ = "dim_city"

    city_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    city_name: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    region: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)

