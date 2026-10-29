"""Shared PostgreSQL helpers for the CampusFix tests (lives in tests/pg_helpers.py)."""
import os

import psycopg
from dotenv import load_dotenv
from psycopg.conninfo import conninfo_to_dict

from database import init_db

load_dotenv()

# Tests create their own users. Never let the real admin from .env be added to the test database.
os.environ.pop("ADMIN_EMAIL", None)
os.environ.pop("ADMIN_PASSWORD", None)

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
TABLES = "users, complaints, status_history, complaint_votes"


def _check_safe():
    """Refuse to run if the tests could wipe the real database."""
    if not TEST_DATABASE_URL:
        raise RuntimeError("TEST_DATABASE_URL is not set in .env")
    if TEST_DATABASE_URL == os.getenv("DATABASE_URL"):
        raise RuntimeError("TEST_DATABASE_URL must not be the same as DATABASE_URL")
    database_name = conninfo_to_dict(TEST_DATABASE_URL).get("dbname", "")
    if not database_name.endswith("_test"):
        raise RuntimeError("The test database name must end with _test")


def connect():
    """Plain connection to the test database (rows are tuples, so row[0] works).

    Use it as `with connect() as conn:` so it commits and closes by itself.
    """
    _check_safe()
    return psycopg.connect(TEST_DATABASE_URL)


def reset_db():
    """Make sure the tables exist, then empty them and restart the ids at 1."""
    _check_safe()
    init_db(TEST_DATABASE_URL)
    with psycopg.connect(TEST_DATABASE_URL) as conn:
        conn.execute(f"TRUNCATE {TABLES} RESTART IDENTITY CASCADE")