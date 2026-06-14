"""
Seed script — build the sample SQLite database for module 12.

Creates a small "sales" schema with three tables:
  customers   — id, name, email, region, signup_date
  products    — id, name, category, price_usd
  orders      — id, customer_id, product_id, quantity, order_date, status

Inserts ~20 rows of realistic-looking sample data so all tasks have
something interesting to query.

How to run:
  uv run python modules/12-text-to-sql/py/seed_db.py

The database is written to:
  modules/12-text-to-sql/sales.db

All other scripts in this module use that path.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "sales.db"


def create_tables(conn: sqlite3.Connection) -> None:
    conn.executescript("""
    DROP TABLE IF EXISTS orders;
    DROP TABLE IF EXISTS customers;
    DROP TABLE IF EXISTS products;

    CREATE TABLE customers (
        id          INTEGER PRIMARY KEY,
        name        TEXT    NOT NULL,
        email       TEXT    NOT NULL UNIQUE,
        region      TEXT    NOT NULL,   -- 'North', 'South', 'East', 'West'
        signup_date TEXT    NOT NULL    -- ISO-8601 date
    );

    CREATE TABLE products (
        id          INTEGER PRIMARY KEY,
        name        TEXT    NOT NULL,
        category    TEXT    NOT NULL,   -- 'Electronics', 'Books', 'Clothing'
        price_usd   REAL    NOT NULL
    );

    CREATE TABLE orders (
        id          INTEGER PRIMARY KEY,
        customer_id INTEGER NOT NULL REFERENCES customers(id),
        product_id  INTEGER NOT NULL REFERENCES products(id),
        quantity    INTEGER NOT NULL DEFAULT 1,
        order_date  TEXT    NOT NULL,   -- ISO-8601 date
        status      TEXT    NOT NULL    -- 'pending', 'shipped', 'delivered', 'cancelled'
    );
    """)


def insert_data(conn: sqlite3.Connection) -> None:
    customers = [
        (1, "Alice Chen",    "alice@example.com",   "West",  "2023-01-15"),
        (2, "Bob Martinez",  "bob@example.com",     "South", "2023-02-20"),
        (3, "Carol Smith",   "carol@example.com",   "East",  "2023-03-05"),
        (4, "David Kim",     "david@example.com",   "North", "2023-04-10"),
        (5, "Eva Brown",     "eva@example.com",     "West",  "2023-05-22"),
        (6, "Frank Torres",  "frank@example.com",   "South", "2023-06-18"),
        (7, "Grace Lee",     "grace@example.com",   "East",  "2023-07-30"),
        (8, "Henry Johnson", "henry@example.com",   "North", "2023-08-14"),
    ]
    conn.executemany(
        "INSERT INTO customers VALUES (?,?,?,?,?)", customers
    )

    products = [
        (1,  "Laptop Pro 15",       "Electronics", 1299.00),
        (2,  "Wireless Headphones", "Electronics",  199.00),
        (3,  "USB-C Hub",           "Electronics",   49.00),
        (4,  "Python Cookbook",     "Books",          39.00),
        (5,  "Machine Learning 101","Books",          54.00),
        (6,  "Running Shoes",       "Clothing",      119.00),
        (7,  "Winter Jacket",       "Clothing",      189.00),
        (8,  "Mechanical Keyboard", "Electronics",  149.00),
        (9,  "Design Patterns",     "Books",          44.00),
        (10, "Yoga Mat",            "Clothing",       35.00),
    ]
    conn.executemany(
        "INSERT INTO products VALUES (?,?,?,?)", products
    )

    orders = [
        (1,  1, 1,  1, "2024-01-05", "delivered"),
        (2,  2, 3,  2, "2024-01-12", "delivered"),
        (3,  3, 4,  1, "2024-01-18", "delivered"),
        (4,  4, 2,  1, "2024-02-01", "delivered"),
        (5,  1, 8,  1, "2024-02-14", "shipped"),
        (6,  5, 6,  1, "2024-02-20", "delivered"),
        (7,  6, 5,  1, "2024-03-03", "delivered"),
        (8,  7, 7,  1, "2024-03-15", "shipped"),
        (9,  3, 9,  2, "2024-03-22", "delivered"),
        (10, 8, 10, 3, "2024-04-01", "pending"),
        (11, 2, 1,  1, "2024-04-10", "shipped"),
        (12, 4, 4,  1, "2024-04-20", "cancelled"),
        (13, 5, 2,  2, "2024-05-05", "delivered"),
        (14, 6, 8,  1, "2024-05-18", "delivered"),
        (15, 1, 5,  1, "2024-06-01", "pending"),
        (16, 7, 3,  4, "2024-06-10", "delivered"),
        (17, 8, 6,  1, "2024-06-22", "shipped"),
        (18, 3, 1,  1, "2024-07-04", "pending"),
        (19, 2, 7,  1, "2024-07-15", "delivered"),
        (20, 1, 10, 2, "2024-07-25", "delivered"),
    ]
    conn.executemany(
        "INSERT INTO orders VALUES (?,?,?,?,?,?)", orders
    )


def main() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        create_tables(conn)
        insert_data(conn)
        conn.commit()
    finally:
        conn.close()

    # Verify
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    for table in ("customers", "products", "orders"):
        (count,) = cur.execute(f"SELECT count(*) FROM {table}").fetchone()
        print(f"  {table}: {count} rows")
    conn.close()
    print(f"\nDatabase written to: {DB_PATH}")


if __name__ == "__main__":
    main()
