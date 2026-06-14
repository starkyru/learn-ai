"""
Task 1 🟢 — Natural-language to SQL.

Given a plain-English question, ask the LLM to generate a SQL SELECT statement,
execute it against the sample SQLite database, and return the rows.

What you'll learn:
  - The NL→SQL prompt pattern: provide the schema, ask for one SQL statement
  - How to extract clean SQL from a model response (fencing, whitespace)
  - How sqlite3 (stdlib) executes queries and returns results
  - Why schema grounding is essential: without the table definitions the LLM
    guesses column names and gets them wrong

How to run:
  # Seed the database first (only needed once):
  uv run python modules/12-text-to-sql/py/seed_db.py

  uv run python modules/12-text-to-sql/py/01_nl_to_sql.py
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any

from llm_core import ChatMessage, ChatOptions, get_provider

DB_PATH = Path(__file__).parent.parent / "sales.db"

# ---------------------------------------------------------------------------
# Schema description (provided to the LLM as grounding)
# ---------------------------------------------------------------------------

SCHEMA = """
Tables in the database:

customers(id INTEGER PK, name TEXT, email TEXT, region TEXT, signup_date TEXT)
  -- region: 'North' | 'South' | 'East' | 'West'

products(id INTEGER PK, name TEXT, category TEXT, price_usd REAL)
  -- category: 'Electronics' | 'Books' | 'Clothing'

orders(id INTEGER PK, customer_id INTEGER FK→customers, product_id INTEGER FK→products,
       quantity INTEGER, order_date TEXT, status TEXT)
  -- status: 'pending' | 'shipped' | 'delivered' | 'cancelled'
  -- dates are ISO-8601 strings (e.g. '2024-03-15')
""".strip()


# ---------------------------------------------------------------------------
# Step 1: generate SQL from a question
# ---------------------------------------------------------------------------


def generate_sql(question: str, provider: Any) -> str:
    """
    Ask the LLM to write a SQL SELECT for the given question.

    TODO: implement this function.

    Steps:
      1. Build a system prompt that:
         - States the LLM is a SQL expert working with SQLite.
         - Provides the schema (SCHEMA constant above).
         - Instructs: "Return ONLY the SQL statement, no explanation,
           no markdown fences."
      2. Build a user message: the plain-English question.
      3. Call provider.chat() with temperature=0 (deterministic output).
      4. Extract and return the SQL string:
         - Strip leading/trailing whitespace.
         - Remove markdown fences if present: ```sql ... ``` or ``` ... ```.
         - Return the first statement (up to the first ";") plus ";".

    Return type: str (the SQL statement, ready to execute).
    """
    raise NotImplementedError("TODO: implement generate_sql()")


def extract_sql(raw: str) -> str:
    """
    Clean raw LLM output and return a single SQL statement.

    TODO: implement this function.

    Steps:
      1. Strip whitespace.
      2. Remove markdown code fences:
           raw = re.sub(r"```(?:sql)?\\n?", "", raw, flags=re.IGNORECASE).strip()
      3. Take only the text up to (and including) the first ";".
         If no ";" found, return the whole string + ";".
      4. Strip whitespace again.
      5. Return the result.
    """
    raise NotImplementedError("TODO: implement extract_sql()")


# ---------------------------------------------------------------------------
# Step 2: execute SQL
# ---------------------------------------------------------------------------


def execute_sql(sql: str) -> tuple[list[str], list[tuple[Any, ...]]]:
    """
    Execute a SQL query against the sample database.

    TODO: implement this function.

    Steps:
      1. conn = sqlite3.connect(DB_PATH)
         conn.row_factory = sqlite3.Row  (so column names are accessible)
      2. cursor = conn.execute(sql)
      3. columns = [desc[0] for desc in cursor.description]
      4. rows = cursor.fetchall()
      5. Close connection.
      6. Return (columns, rows).

    Let sqlite3 errors propagate — task 3 will add the retry/repair logic.
    """
    raise NotImplementedError("TODO: implement execute_sql()")


# ---------------------------------------------------------------------------
# Combined pipeline
# ---------------------------------------------------------------------------


def query(question: str, provider: Any) -> dict[str, Any]:
    """
    Full NL→SQL→execute pipeline.

    TODO: implement this function.

    Steps:
      1. sql = generate_sql(question, provider)
      2. columns, rows = execute_sql(sql)
      3. Return {"sql": sql, "columns": columns, "rows": rows}
    """
    raise NotImplementedError("TODO: implement query()")


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------

QUESTIONS = [
    "How many customers are there in total?",
    "What are the top 3 most expensive products?",
    "Which customers are from the West region?",
    "What is the total revenue from delivered orders?",
]


def main() -> None:
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}")
        print("Run `uv run python modules/12-text-to-sql/py/seed_db.py` first.")
        return

    provider = get_provider()
    print(f"\nProvider: {provider.name}  |  Model: {provider.chat_model}\n")

    for q in QUESTIONS:
        print(f"Q: {q}")
        result = query(q, provider)
        print(f"   SQL: {result['sql']}")
        print(f"   Cols: {result['columns']}")
        for row in result["rows"][:5]:
            print(f"   Row: {tuple(row)}")
        print()


if __name__ == "__main__":
    main()
