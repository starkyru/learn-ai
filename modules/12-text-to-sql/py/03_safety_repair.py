"""
Task 3 🟡 — Safety & repair.

LLM-generated SQL can be dangerous (DROP TABLE) or broken (syntax error,
wrong column name). This task adds three defences:
  1. Read-only guard: reject any SQL that is not a SELECT statement.
  2. Injection guard: basic parameterisation check.
  3. Error-and-retry: if the DB raises an error, feed it back to the LLM
     and ask for a corrected query (up to N retries).

What you'll learn:
  - Why you must NEVER execute untrusted LLM SQL without validation
  - The read-only guard pattern (whitelist on statement type)
  - Self-healing agents: the LLM can fix its own mistakes if you tell it what
    went wrong
  - The limits of self-repair (some errors are beyond the LLM's reach)

How to run:
  uv run python modules/12-text-to-sql/py/03_safety_repair.py
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any

from llm_core import ChatMessage, ChatOptions, get_provider

DB_PATH = Path(__file__).parent.parent / "sales.db"

# Reuse schema from task 1 for simplicity
SCHEMA = """
customers(id, name, email, region, signup_date)
products(id, name, category, price_usd)
orders(id, customer_id→customers, product_id→products, quantity, order_date, status)
""".strip()


# ---------------------------------------------------------------------------
# Safety validators
# ---------------------------------------------------------------------------


class UnsafeSQLError(Exception):
    """Raised when generated SQL fails safety validation."""


def validate_read_only(sql: str) -> None:
    """
    Reject any SQL that is not a plain SELECT.

    TODO: implement this function.

    Steps:
      1. Strip leading whitespace and comments (lines starting with "--").
      2. Extract the first keyword (split on whitespace, take index 0, upper()).
      3. If the first keyword is NOT "SELECT", raise UnsafeSQLError:
           f"Rejected: statement starts with '{keyword}', not SELECT."
      4. Additionally scan the full SQL for these forbidden keywords
         (as standalone words, case-insensitive):
           DROP, DELETE, UPDATE, INSERT, ALTER, CREATE, REPLACE, TRUNCATE
         and raise UnsafeSQLError if any are found.

    Regex hint: use r"\\b(DROP|DELETE|...)\\b" with re.IGNORECASE.
    """
    raise NotImplementedError("TODO: implement validate_read_only()")


def validate_no_stacked_queries(sql: str) -> None:
    """
    Reject SQL that contains multiple statements (stacked queries / injection).

    TODO: implement this function.

    Steps:
      1. Count the number of ";" characters in the SQL.
      2. If there is more than one ";", or if a ";" appears before the end of
         the string (excluding trailing whitespace), raise UnsafeSQLError:
           "Rejected: SQL contains multiple statements."

    This prevents classic injection like:
      SELECT 1; DROP TABLE customers; --
    """
    raise NotImplementedError("TODO: implement validate_no_stacked_queries()")


# ---------------------------------------------------------------------------
# Error-and-retry loop
# ---------------------------------------------------------------------------


def generate_sql(question: str, provider: Any) -> str:
    """Generate SQL using a simple prompt (same as task 1)."""
    messages = [
        ChatMessage("system",
            f"You are a SQL expert. Schema:\n{SCHEMA}\n"
            "Return ONLY a SQL SELECT statement, no explanation, no fences."),
        ChatMessage("user", question),
    ]
    result = provider.chat(messages, ChatOptions(temperature=0))
    raw = result.text.strip()
    raw = re.sub(r"```(?:sql)?\n?", "", raw, flags=re.IGNORECASE).strip("` \n")
    if ";" in raw:
        raw = raw[: raw.index(";") + 1]
    return raw.strip()


def repair_sql(
    question: str,
    bad_sql: str,
    error_message: str,
    provider: Any,
) -> str:
    """
    Ask the LLM to fix a broken SQL statement given the database error.

    TODO: implement this function.

    Steps:
      1. Build messages:
         - System: same as generate_sql's system prompt.
         - User (first turn): original question.
         - Assistant (first turn): bad_sql  (the LLM's previous attempt).
         - User (second turn): a repair instruction, e.g.:
             "That SQL produced this error: <error_message>\\n\\n
              Please fix it and return ONLY the corrected SQL statement."
      2. Call provider.chat(messages, ChatOptions(temperature=0)).
      3. Clean and return the SQL (same as generate_sql).

    This multi-turn structure shows the LLM what went wrong and lets it
    reason about the fix in context.
    """
    raise NotImplementedError("TODO: implement repair_sql()")


def safe_query(
    question: str,
    provider: Any,
    max_retries: int = 2,
) -> dict[str, Any]:
    """
    Full safe pipeline: generate → validate → execute → repair on error.

    TODO: implement this function.

    Steps:
      1. sql = generate_sql(question, provider).
      2. validate_read_only(sql)  — raise immediately if unsafe (no retry).
      3. validate_no_stacked_queries(sql).
      4. For attempt in range(max_retries + 1):
         a. Try: conn = sqlite3.connect(DB_PATH); cursor = conn.execute(sql);
                 columns = ...; rows = cursor.fetchall(); conn.close().
         b. On success: return {"sql": sql, "columns": columns, "rows": rows,
                                 "retries": attempt}.
         c. On sqlite3.Error: if attempt < max_retries:
                 sql = repair_sql(question, sql, str(error), provider)
                 validate_read_only(sql)  # re-validate after repair
                 validate_no_stacked_queries(sql)
              else: raise.
      5. (Unreachable — for type safety) raise RuntimeError.

    Note: UnsafeSQLError propagates immediately (no retry).
    """
    raise NotImplementedError("TODO: implement safe_query()")


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------

# Mix of safe questions and intentionally adversarial inputs to test guards.
TEST_CASES = [
    # Normal questions — should succeed
    ("How many products are in the Electronics category?", True),
    ("What is the average price of all products?",         True),
    # Adversarial inputs — should be blocked by the read-only guard
    # (These are passed as the "question" to see if a naive LLM would comply.)
    ("DROP TABLE customers",                               False),
    ("DELETE FROM orders WHERE 1=1",                       False),
]


def main() -> None:
    if not DB_PATH.exists():
        print(f"Database not found: {DB_PATH}")
        print("Run `uv run python modules/12-text-to-sql/py/seed_db.py` first.")
        return

    provider = get_provider()
    print(f"\nProvider: {provider.name}  |  Model: {provider.chat_model}\n")

    for question, expect_success in TEST_CASES:
        print(f"Q: {question}")
        try:
            result = safe_query(question, provider)
            if expect_success:
                print(f"   OK — SQL: {result['sql']}")
                print(f"   Retries: {result.get('retries', 0)}")
                for row in result["rows"][:3]:
                    print(f"   Row: {tuple(row)}")
            else:
                print("   UNEXPECTED SUCCESS (guard should have blocked this)")
        except UnsafeSQLError as e:
            if not expect_success:
                print(f"   BLOCKED (expected): {e}")
            else:
                print(f"   UNEXPECTED BLOCK: {e}")
        except Exception as e:
            print(f"   ERROR: {e}")
        print()


if __name__ == "__main__":
    main()
