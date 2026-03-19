from __future__ import annotations

import random
from datetime import date, timedelta

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.dim_city import DimCity
from app.models.dim_date import DimDate
from app.models.dim_product import DimProduct
from app.models.fact_sales import FactSales


def _date_id(d: date) -> int:
    return int(d.strftime("%Y%m%d"))


def seed_dim_date(db, days: int = 365) -> None:
    today = date.today()
    start = today - timedelta(days=days - 1)
    existing = db.execute(select(DimDate.date_id).limit(1)).first()
    if existing:
        return
    rows = []
    cur = start
    while cur <= today:
        rows.append(
            DimDate(
                date_id=_date_id(cur),
                full_date=cur,
                year=cur.year,
                month=cur.month,
                day=cur.day,
                week=int(cur.isocalendar().week),
            )
        )
        cur += timedelta(days=1)
    db.add_all(rows)


def seed_dim_city(db) -> None:
    existing = db.execute(select(DimCity.city_id).limit(1)).first()
    if existing:
        return
    cities = [
        ("Tashkent", "Tashkent"),
        ("Samarkand", "Samarkand"),
        ("Bukhara", "Bukhara"),
        ("Andijan", "Andijan"),
        ("Namangan", "Namangan"),
        ("Fergana", "Fergana"),
        ("Nukus", "Karakalpakstan"),
        ("Khiva", "Khorezm"),
        ("Karshi", "Kashkadarya"),
        ("Termez", "Surkhandarya"),
    ]
    db.add_all([DimCity(city_name=n, region=r) for n, r in cities])


def seed_dim_product(db) -> None:
    existing = db.execute(select(DimProduct.product_id).limit(1)).first()
    if existing:
        return
    products = [
        ("Laptop Pro 14", "Electronics"),
        ("Laptop Air 13", "Electronics"),
        ("Phone X", "Electronics"),
        ("Phone Mini", "Electronics"),
        ("Coffee Beans 1kg", "Grocery"),
        ("Green Tea 200g", "Grocery"),
        ("Office Chair", "Furniture"),
        ("Standing Desk", "Furniture"),
        ("Running Shoes", "Apparel"),
        ("Winter Jacket", "Apparel"),
        ("Book: Data Analytics", "Books"),
        ("Book: SQL Basics", "Books"),
    ]
    db.add_all([DimProduct(product_name=p, category=c) for p, c in products])


def seed_fact_sales(db, days: int = 180, orders_per_day: int = 60) -> None:
    existing = db.execute(select(FactSales.sales_id).limit(1)).first()
    if existing:
        return

    city_ids = [c[0] for c in db.execute(select(DimCity.city_id)).all()]
    product_rows = db.execute(select(DimProduct.product_id, DimProduct.category)).all()
    product_ids = [p[0] for p in product_rows]

    today = date.today()
    start = today - timedelta(days=days - 1)

    rng = random.Random(42)
    sales_rows = []
    order_id = 10_000

    # Create a mild upward revenue trend and a weekend effect.
    for i in range(days):
        d = start + timedelta(days=i)
        weekday = d.weekday()  # 0..6
        weekend_multiplier = 1.15 if weekday >= 5 else 1.0
        trend_multiplier = 0.85 + (i / max(days - 1, 1)) * 0.35

        for _ in range(orders_per_day):
            order_id += 1
            city_id = rng.choice(city_ids)
            product_id = rng.choice(product_ids)
            customer_id = rng.randint(1, 1500)
            quantity = rng.randint(1, 5)

            # Simple pricing model by category
            base_price = 20.0
            # bias: some products more expensive
            if product_id % 6 == 0:
                base_price = 250.0
            elif product_id % 5 == 0:
                base_price = 120.0
            elif product_id % 4 == 0:
                base_price = 60.0

            price = base_price * (0.9 + rng.random() * 0.3) * trend_multiplier * weekend_multiplier
            revenue = round(price * quantity, 2)
            cost = round(revenue * (0.55 + rng.random() * 0.25), 2)
            profit = round(revenue - cost, 2)

            sales_rows.append(
                FactSales(
                    order_id=order_id,
                    order_date=d,
                    date_id=_date_id(d),
                    city_id=city_id,
                    product_id=product_id,
                    customer_id=customer_id,
                    quantity=quantity,
                    revenue=revenue,
                    cost=cost,
                    profit=profit,
                )
            )

    db.add_all(sales_rows)


def main() -> None:
    db = SessionLocal()
    try:
        seed_dim_date(db)
        seed_dim_city(db)
        seed_dim_product(db)
        db.commit()

        seed_fact_sales(db)
        db.commit()
        print("Seed completed.")
    finally:
        db.close()


if __name__ == "__main__":
    main()

