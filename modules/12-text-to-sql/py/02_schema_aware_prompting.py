"""
Task 2 🟡 — Schema-aware prompting.

A richer schema prompt — with table descriptions, sample rows, and explicit
JOIN hints — dramatically improves LLM-generated SQL for multi-table queries.

What you'll learn:
  - How few-shot examples in the schema prompt steer the LLM away from common
    mistakes (wrong column names, wrong JOIN conditions)
  - How to auto-generate a schema description from live database metadata
    (sqlite_master + PRAGMA table_info) instead of hardcoding it
  - How to handle multi-table queries with explicit JOIN instructions

How to run:
  uv run python modules/12-text-to-sql/py/02_schema_aware_prompting.py
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from llm_core import ChatMessage, ChatOptions, get_provider

DB_PATH = Path(__file__).parent.parent / "sales.db"


# ---------------------------------------------------------------------------
# Dynamic schema extraction
# ---------------------------------------------------------------------------


def get_schema_description(conn: sqlite3.Connection) -> str:
    """
    Auto-generate a schema description from the live database.

    TODO: implement this function.

    Steps:
      1. Query sqlite_master for user tables:
           SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'
      2. For each table:
         a. PRAGMA table_info(<table>) → rows with (cid, name, type, notnull, dflt, pk)
         b. Fetch 3 sample rows: SELECT * FROM <table> LIMIT 3
         c. Format:
              TABLE: <name>
              COLUMNS: col1 (TYPE), col2 (TYPE), ...
              SAMPLE ROWS:
                (val1, val2, ...)
                (val1, val2, ...)
      3. Join all table descriptions with "\\n\\n".
      4. Return the full schema string.

    This way the schema stays in sync with the database automatically.
    """
    raise NotImplementedError("TODO: implement get_schema_description()")


# ---------------------------------------------------------------------------
# Rich system prompt
# ---------------------------------------------------------------------------


def build_system_prompt(schema: str) -> str:
    """
    Build a detailed system prompt for multi-table SQL generation.

    TODO: implement this function.

    The prompt should include:
      1. Role: "You are an expert SQL analyst working with SQLite."
      2. The schema description (from get_schema_description).
      3. JOIN guidance:
         - orders JOIN customers ON orders.customer_id = customers.id
         - orders JOIN products  ON orders.product_id  = products.id
      4. Rules:
         - Return ONLY a single SQL SELECT statement.
         - No markdown, no explanation.
         - Use table aliases for readability (e.g. o for orders).
         - Always use explicit column names, never SELECT *.
      5. One or two few-shot examples showing a question and the correct SQL.

    Return the system prompt string.
    """
    raise NotImplementedError("TODO: implement build_system_prompt()")


# ---------------------------------------------------------------------------
# Generation + execution
# ---------------------------------------------------------------------------


def generate_sql_rich(question: str, schema: str, provider: Any) -> str:
    """
    Generate SQL using the rich schema-aware prompt.

    TODO: implement this function.

    Steps:
      1. system = build_system_prompt(schema).
      2. Call provider.chat([system_msg, user_msg], options=ChatOptions(temperature=0)).
      3. Clean and return the SQL (same logic as task 1's extract_sql).
    """
    raise NotImplementedError("TODO: implement generate_sql_rich()")


def execute_sql(sql: str) -> tuple[list[str], list[tuple[Any, ...]]]:
    """Execute SQL against the sample DB and return (columns, rows)."""
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.execute(sql)
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
    finally:
        conn.close()
    return columns, rows


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------

# These questions require JOINs across multiple tables.
MULTI_TABLE_QUESTIONS = [
    "Which customers placed orders for Electronics products?",
    "What is the total spend per customer, sorted from highest to lowest?",
    "List all orders with the customer name and product name, for orders that are 'shipped'.",
    "Which product category generates the most revenue from delivered orders?",
]


def main() -> None:
    if not DB_PATH.exists():
        print(f"Database not found: {DB_PATH}")
        print("Run `uv run python modules/12-text-to-sql/py/seed_db.py` first.")
        return

    conn = sqlite3.connect(DB_PATH)
    schema = get_schema_description(conn)
    conn.close()

    print("\n--- Live Schema ---")
    print(schema)
    print("---\n")

    provider = get_provider()
    print(f"Provider: {provider.name}  |  Model: {provider.chat_model}\n")

    for q in MULTI_TABLE_QUESTIONS:
        print(f"Q: {q}")
        sql = generate_sql_rich(q, schema, provider)
        print(f"   SQL: {sql}")
        try:
            cols, rows = execute_sql(sql)
            print(f"   Cols: {cols}")
            for row in rows[:5]:
                print(f"   Row: {tuple(row)}")
        except Exception as e:
            print(f"   ERROR: {e}")
        print()


if __name__ == "__main__":
    main()
