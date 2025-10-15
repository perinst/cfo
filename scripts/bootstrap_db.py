"""
scripts/bootstrap_db.py

Bootstraps the Supabase database for local development.
It checks for required tables and if missing, applies db/schema.sql using the SQL RPC endpoint.

Requirements:
- SUPABASE_URL
- SUPABASE_KEY (service role preferred for schema changes)
"""

import os
from pathlib import Path
from supabase import create_client
from dotenv import load_dotenv

REQUIRED_TABLES = [
    "organizations",
    "transactions",
    "budgets",
    "invoices",
    "chat_history",
]


def main():
    load_dotenv()
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise SystemExit("SUPABASE_URL and SUPABASE_KEY must be set in environment.")

    client = create_client(url, key)

    # Quick existence check: try selecting from each table
    missing = []
    for table in REQUIRED_TABLES:
        try:
            client.table(table).select("*").limit(1).execute()
        except Exception:
            missing.append(table)

    if missing:
        print(f"Missing tables: {', '.join(missing)}. Applying schema.sql ...")

        schema_path = Path(__file__).resolve().parents[1] / "db" / "schema.sql"
        sql = schema_path.read_text(encoding="utf-8")

        try:
            client.rpc("pg_exec", {"sql": sql}).execute()
            print("Schema applied via pg_exec RPC.")
        except Exception:
            try:
                client.rpc("sql", {"query": sql}).execute()
                print("Schema applied via sql RPC.")
            except Exception:
                print(
                    "Could not apply schema via RPC.\n"
                    "- Option 1: Open Supabase SQL editor and run db/schema.sql manually.\n"
                    "- Option 2: Install/enable a SQL RPC such as pg_exec."
                )
                return

    # Optionally seed
    if os.getenv("SEED") == "1":
        seed_path = Path(__file__).resolve().parents[1] / "db" / "seed.sql"
        if seed_path.exists():
            print("Seeding database with sample data ...")
            seed_sql = seed_path.read_text(encoding="utf-8")
            try:
                client.rpc("pg_exec", {"sql": seed_sql}).execute()
                print("Seed applied via pg_exec RPC.")
            except Exception:
                try:
                    client.rpc("sql", {"query": seed_sql}).execute()
                    print("Seed applied via sql RPC.")
                except Exception:
                    print(
                        "Could not apply seed via RPC. You can paste db/seed.sql in SQL editor."
                    )
        else:
            print("Seed file not found: db/seed.sql")
    else:
        print("Skipping seed. Set SEED=1 to seed sample data.")


if __name__ == "__main__":
    main()
