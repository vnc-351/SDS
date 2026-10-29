"""Database helpers for CampusFix (PostgreSQL): connections, schema setup and admin bootstrap."""
import logging
import os

import psycopg
from flask import current_app, g
from psycopg.rows import dict_row
from werkzeug.security import generate_password_hash

from config import DATABASE

logger = logging.getLogger(__name__)

# Resolved tickets stay in normal lists for one day, then appear only in the archive.
ACTIVE_TICKET_SQL = "(status != 'Resolved' OR updated_at > NOW() - INTERVAL '1 day')"

# Arbitrary number used so that several app workers starting at once do not create tables at the same time.
SCHEMA_LOCK_ID = 724801

SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'student',
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS complaints (
        id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id),
        title TEXT NOT NULL,
        category TEXT NOT NULL,
        location TEXT NOT NULL,
        description TEXT NOT NULL,
        image_filename TEXT,
        status TEXT NOT NULL DEFAULT 'Pending',
        ai_category TEXT,
        ai_priority TEXT,
        ai_explanation TEXT,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS status_history (
        id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        complaint_id INTEGER NOT NULL REFERENCES complaints(id),
        previous_status TEXT,
        new_status TEXT NOT NULL,
        changed_by INTEGER REFERENCES users(id),
        changed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS complaint_votes (
        id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        complaint_id INTEGER NOT NULL REFERENCES complaints(id),
        user_id INTEGER NOT NULL REFERENCES users(id),
        vote INTEGER NOT NULL CHECK (vote IN (-1, 1)),
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (complaint_id, user_id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_complaints_user_id ON complaints (user_id)",
    "CREATE INDEX IF NOT EXISTS idx_status_history_complaint_id ON status_history (complaint_id)",
    # One-time rename of the old priority labels to the current ones.
    """
    UPDATE complaints
    SET ai_priority = CASE ai_priority
        WHEN 'Urgent' THEN 'Critical'
        WHEN 'High' THEN 'Important'
        WHEN 'Medium' THEN 'Normal'
        ELSE ai_priority
    END
    WHERE ai_priority IN ('Urgent', 'High', 'Medium')
    """,
]


def ticket_ref(ticket_id):
    """Readable ticket ID such as CF-00001."""
    return f"CF-{ticket_id:05d}"


def get_db():
    """Return the PostgreSQL connection for the current request (opened on first use).

    Rows come back as dictionaries, so row["name"] works like it did with sqlite3.Row.
    """
    db = getattr(g, "_database", None)
    if db is None:
        db = psycopg.connect(current_app.config["DATABASE"], row_factory=dict_row)
        g._database = db
    return db


def close_db(_error=None):
    # Closing a connection with an unfinished transaction rolls it back.
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()
        g._database = None


def init_db(database_url):
    """Create tables if they do not exist yet."""
    # "with" commits when the block ends normally and closes the connection.
    with psycopg.connect(database_url) as conn:
        conn.execute("SELECT pg_advisory_xact_lock(%s)", (SCHEMA_LOCK_ID,))
        for statement in SCHEMA_STATEMENTS:
            conn.execute(statement)


def ensure_default_admin(database_url):
    """Create the admin from ADMIN_EMAIL / ADMIN_PASSWORD if both are set."""
    admin_email = os.getenv("ADMIN_EMAIL")
    admin_password = os.getenv("ADMIN_PASSWORD")
    if not admin_email or not admin_password:
        return False
    admin_email = admin_email.lower()
    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        existing = conn.execute(
            "SELECT id, role FROM users WHERE email = %s",
            (admin_email,),
        ).fetchone()
        if existing is not None and existing["role"] != "admin":
            # Never silently promote a student account, and never crash the app at startup.
            logger.warning(
                "ADMIN_EMAIL %s is already registered as a %s account; no admin was created.",
                admin_email,
                existing["role"],
            )
            return False
        if existing is None:
            # ON CONFLICT covers two workers starting at the same moment.
            conn.execute(
                "INSERT INTO users (name, email, password_hash, role) VALUES (%s, %s, %s, 'admin') "
                "ON CONFLICT (email) DO NOTHING",
                ("CampusFix Admin", admin_email, generate_password_hash(admin_password)),
            )
        return True


def create_admin_user(email, password, database_url=DATABASE):
    """Create an admin account (used by `python app.py --create-admin`).

    Returns (user_id, created). Raises ValueError if the email already belongs to a non-admin.
    """
    init_db(database_url)
    email = email.lower()
    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        user = conn.execute("SELECT id, role FROM users WHERE email = %s", (email,)).fetchone()
        if user is not None:
            if user["role"] != "admin":
                raise ValueError(f"{email} is already registered as a {user['role']} account; nothing was changed.")
            return user["id"], False
        row = conn.execute(
            "INSERT INTO users (name, email, password_hash, role) VALUES (%s, %s, %s, 'admin') RETURNING id",
            ("CampusFix Admin", email, generate_password_hash(password)),
        ).fetchone()
        return row["id"], True


def init_app(app):
    """Hook the database into the Flask app: close connections, create tables, seed admin."""
    app.teardown_appcontext(close_db)
    init_db(app.config["DATABASE"])
    ensure_default_admin(app.config["DATABASE"])