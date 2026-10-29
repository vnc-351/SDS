import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

import psycopg
from werkzeug.security import check_password_hash, generate_password_hash

from app import create_app
from database import create_admin_user, ensure_default_admin, get_db, init_db
from pg_helpers import TEST_DATABASE_URL, connect, reset_db


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        reset_db()
        self.db_url = TEST_DATABASE_URL
        self.folder = tempfile.mkdtemp()  # only used as the upload folder for create_app

    def tearDown(self):
        shutil.rmtree(self.folder, ignore_errors=True)

    def rows(self, sql, params=()):
        with connect() as conn:
            return conn.execute(sql, params).fetchall()

    def add_user(self, email, role):
        with connect() as conn:
            conn.execute(
                "INSERT INTO users (name, email, password_hash, role) VALUES ('Existing', %s, %s, %s)",
                (email, generate_password_hash("OldPassw0rd"), role),
            )

    def test_init_db_creates_all_tables_and_can_run_twice(self):
        init_db(self.db_url)
        init_db(self.db_url)
        tables = {
            row[0]
            for row in self.rows("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        }
        self.assertTrue({"users", "complaints", "status_history", "complaint_votes"} <= tables)

    def test_old_priority_labels_are_renamed(self):
        init_db(self.db_url)
        self.add_user("s@example.com", "student")
        user_id = self.rows("SELECT id FROM users")[0][0]
        with connect() as conn:
            conn.execute(
                "INSERT INTO complaints (user_id, title, category, location, description, ai_priority) "
                "VALUES (%s, 't', 'Other', 'l', 'd', 'Urgent')",
                (user_id,),
            )
        init_db(self.db_url)
        self.assertEqual(self.rows("SELECT ai_priority FROM complaints"), [("Critical",)])

    # --- foreign keys are enforced by the database itself --------------------------------------
    def test_foreign_keys_are_enforced_by_the_app_connection(self):
        app = create_app(testing=True, database_url=self.db_url, upload_folder=self.folder)
        with app.app_context():
            conn = get_db()
            with self.assertRaises(psycopg.errors.ForeignKeyViolation):
                conn.execute(
                    "INSERT INTO complaints (user_id, title, category, location, description) "
                    "VALUES (999, 't', 'Other', 'l', 'd')"
                )

    # --- admin bootstrap ---------------------------------------------------------------------------
    def test_default_admin_is_created_from_environment(self):
        init_db(self.db_url)
        env = {"ADMIN_EMAIL": "Boss@Campus.test", "ADMIN_PASSWORD": "Secret123"}
        with patch.dict(os.environ, env):
            self.assertTrue(ensure_default_admin(self.db_url))
            self.assertTrue(ensure_default_admin(self.db_url))  # second run changes nothing
        rows = self.rows("SELECT email, role, password_hash FROM users")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][:2], ("boss@campus.test", "admin"))
        self.assertTrue(check_password_hash(rows[0][2], "Secret123"))

    def test_default_admin_skipped_when_not_configured(self):
        init_db(self.db_url)
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(ensure_default_admin(self.db_url))
        self.assertEqual(self.rows("SELECT * FROM users"), [])

    def test_startup_does_not_crash_or_promote_when_admin_email_belongs_to_a_student(self):
        init_db(self.db_url)
        self.add_user("boss@campus.test", "student")
        env = {"ADMIN_EMAIL": "boss@campus.test", "ADMIN_PASSWORD": "Secret123"}
        with patch.dict(os.environ, env):
            with self.assertLogs("database", level="WARNING"):
                self.assertFalse(ensure_default_admin(self.db_url))
            create_app(testing=True, database_url=self.db_url, upload_folder=self.folder)  # must not raise
        self.assertEqual(self.rows("SELECT role FROM users"), [("student",)])

    def test_create_admin_user_creates_then_reports_existing(self):
        user_id, created = create_admin_user("new@campus.test", "Secret123", self.db_url)
        self.assertTrue(created)
        same_id, created_again = create_admin_user("NEW@campus.test", "Different1", self.db_url)
        self.assertEqual((same_id, created_again), (user_id, False))
        rows = self.rows("SELECT role, password_hash FROM users")
        self.assertEqual(len(rows), 1)
        self.assertTrue(check_password_hash(rows[0][1], "Secret123"))  # password not overwritten

    def test_create_admin_user_refuses_to_touch_a_student_account(self):
        init_db(self.db_url)
        self.add_user("kid@campus.test", "student")
        with self.assertRaises(ValueError):
            create_admin_user("kid@campus.test", "Secret123", self.db_url)
        self.assertEqual(self.rows("SELECT role FROM users"), [("student",)])


if __name__ == "__main__":
    unittest.main()