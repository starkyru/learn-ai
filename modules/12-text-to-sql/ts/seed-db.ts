/**
 * Seed script — build the sample SQLite database for module 12 (TypeScript).
 *
 * Uses better-sqlite3 (synchronous SQLite bindings for Node.js) to create the
 * same "sales" schema as the Python seed script:
 *   customers, products, orders
 *
 * How to run:
 *   pnpm tsx modules/12-text-to-sql/ts/seed-db.ts
 *
 * The database is written to:
 *   modules/12-text-to-sql/sales.db
 *
 * Note: better-sqlite3 is a native Node addon. Install with:
 *   pnpm install  (from modules/12-text-to-sql/ts/ or repo root)
 */

import Database from "better-sqlite3";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
export const DB_PATH = join(__dirname, "..", "sales.db");

export function seedDatabase(dbPath = DB_PATH): void {
  const db = new Database(dbPath);

  db.exec(`
    DROP TABLE IF EXISTS orders;
    DROP TABLE IF EXISTS customers;
    DROP TABLE IF EXISTS products;

    CREATE TABLE customers (
      id          INTEGER PRIMARY KEY,
      name        TEXT    NOT NULL,
      email       TEXT    NOT NULL UNIQUE,
      region      TEXT    NOT NULL,
      signup_date TEXT    NOT NULL
    );

    CREATE TABLE products (
      id          INTEGER PRIMARY KEY,
      name        TEXT    NOT NULL,
      category    TEXT    NOT NULL,
      price_usd   REAL    NOT NULL
    );

    CREATE TABLE orders (
      id          INTEGER PRIMARY KEY,
      customer_id INTEGER NOT NULL REFERENCES customers(id),
      product_id  INTEGER NOT NULL REFERENCES products(id),
      quantity    INTEGER NOT NULL DEFAULT 1,
      order_date  TEXT    NOT NULL,
      status      TEXT    NOT NULL
    );
  `);

  const insertCustomer = db.prepare(
    "INSERT INTO customers VALUES (?,?,?,?,?)"
  );
  const customers = [
    [1, "Alice Chen",    "alice@example.com",   "West",  "2023-01-15"],
    [2, "Bob Martinez",  "bob@example.com",     "South", "2023-02-20"],
    [3, "Carol Smith",   "carol@example.com",   "East",  "2023-03-05"],
    [4, "David Kim",     "david@example.com",   "North", "2023-04-10"],
    [5, "Eva Brown",     "eva@example.com",     "West",  "2023-05-22"],
    [6, "Frank Torres",  "frank@example.com",   "South", "2023-06-18"],
    [7, "Grace Lee",     "grace@example.com",   "East",  "2023-07-30"],
    [8, "Henry Johnson", "henry@example.com",   "North", "2023-08-14"],
  ];
  for (const row of customers) insertCustomer.run(...row);

  const insertProduct = db.prepare(
    "INSERT INTO products VALUES (?,?,?,?)"
  );
  const products = [
    [1,  "Laptop Pro 15",       "Electronics", 1299.00],
    [2,  "Wireless Headphones", "Electronics",  199.00],
    [3,  "USB-C Hub",           "Electronics",   49.00],
    [4,  "Python Cookbook",     "Books",          39.00],
    [5,  "Machine Learning 101","Books",          54.00],
    [6,  "Running Shoes",       "Clothing",      119.00],
    [7,  "Winter Jacket",       "Clothing",      189.00],
    [8,  "Mechanical Keyboard", "Electronics",  149.00],
    [9,  "Design Patterns",     "Books",          44.00],
    [10, "Yoga Mat",            "Clothing",       35.00],
  ];
  for (const row of products) insertProduct.run(...row);

  const insertOrder = db.prepare(
    "INSERT INTO orders VALUES (?,?,?,?,?,?)"
  );
  const orders = [
    [1,  1, 1,  1, "2024-01-05", "delivered"],
    [2,  2, 3,  2, "2024-01-12", "delivered"],
    [3,  3, 4,  1, "2024-01-18", "delivered"],
    [4,  4, 2,  1, "2024-02-01", "delivered"],
    [5,  1, 8,  1, "2024-02-14", "shipped"],
    [6,  5, 6,  1, "2024-02-20", "delivered"],
    [7,  6, 5,  1, "2024-03-03", "delivered"],
    [8,  7, 7,  1, "2024-03-15", "shipped"],
    [9,  3, 9,  2, "2024-03-22", "delivered"],
    [10, 8, 10, 3, "2024-04-01", "pending"],
    [11, 2, 1,  1, "2024-04-10", "shipped"],
    [12, 4, 4,  1, "2024-04-20", "cancelled"],
    [13, 5, 2,  2, "2024-05-05", "delivered"],
    [14, 6, 8,  1, "2024-05-18", "delivered"],
    [15, 1, 5,  1, "2024-06-01", "pending"],
    [16, 7, 3,  4, "2024-06-10", "delivered"],
    [17, 8, 6,  1, "2024-06-22", "shipped"],
    [18, 3, 1,  1, "2024-07-04", "pending"],
    [19, 2, 7,  1, "2024-07-15", "delivered"],
    [20, 1, 10, 2, "2024-07-25", "delivered"],
  ];
  for (const row of orders) insertOrder.run(...row);

  db.close();
}

// Run as script
const isMain = process.argv[1] === fileURLToPath(import.meta.url);
if (isMain) {
  seedDatabase();
  // Verify
  const db = new Database(DB_PATH);
  for (const table of ["customers", "products", "orders"]) {
    const row = db.prepare(`SELECT count(*) as n FROM ${table}`).get() as { n: number };
    console.log(`  ${table}: ${row.n} rows`);
  }
  db.close();
  console.log(`\nDatabase written to: ${DB_PATH}`);
}
