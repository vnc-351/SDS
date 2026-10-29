import glob
import os
import re
import shutil
import tempfile
import unittest

from werkzeug.security import generate_password_hash

from app import create_app
from pg_helpers import TEST_DATABASE_URL, connect, reset_db

TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")


class PageIntegrationTests(unittest.TestCase):
    """Checks that blueprints, templates and url_for() references fit together."""

    def setUp(self):
        reset_db()
        self.upload_dir = tempfile.mkdtemp()
        self.app = create_app(testing=True, database_url=TEST_DATABASE_URL, upload_folder=self.upload_dir)
        self.client = self.app.test_client()

        # The ids restart at 1 after reset_db(), so the student is user 1 and owns complaint 1.
        with connect() as conn:
            for email, role in (("student@example.com", "student"), ("admin@example.com", "admin")):
                conn.execute(
                    "INSERT INTO users (name, email, password_hash, role) VALUES (%s, %s, %s, %s)",
                    (role.title(), email, generate_password_hash("Passw0rd1"), role),
                )
            conn.execute(
                "INSERT INTO complaints (user_id, title, category, location, description, status, updated_at) "
                "VALUES (1, 'Leaky tap', 'Plumbing', 'Block A', 'Dripping', 'Pending', CURRENT_TIMESTAMP)"
            )

    def tearDown(self):
        shutil.rmtree(self.upload_dir, ignore_errors=True)

    def login(self, email):
        self.client.post("/login", data={"email": email, "password": "Passw0rd1"})

    def test_every_url_for_in_templates_points_to_a_real_endpoint(self):
        endpoints = set(self.app.view_functions)
        found = set()
        for path in glob.glob(os.path.join(TEMPLATE_DIR, "*.html")):
            with open(path, encoding="utf-8") as handle:
                found.update(re.findall(r"url_for\(\s*['\"]([\w.]+)['\"]", handle.read()))
        found.discard("static")
        self.assertTrue(found, "no url_for references were found; the test is not checking anything")
        self.assertEqual(found - endpoints, set(), "templates reference unknown endpoints")

    def test_expected_url_paths_are_unchanged(self):
        rules = {rule.rule for rule in self.app.url_map.iter_rules()}
        expected = {
            "/", "/register", "/login", "/logout", "/dashboard", "/report_issue", "/my_tickets",
            "/issues", "/issues/<int:ticket_id>/vote", "/archive", "/ticket/<int:ticket_id>",
            "/admin", "/admin/update_status/<int:ticket_id>", "/uploads/<path:filename>", "/health",
        }
        self.assertEqual(expected - rules, set())

    def test_public_pages_render(self):
        for path in ("/", "/login", "/register", "/health"):
            self.assertEqual(self.client.get(path).status_code, 200, path)

    def test_student_pages_render(self):
        self.login("student@example.com")
        for path in ("/dashboard", "/report_issue", "/my_tickets", "/issues", "/archive", "/ticket/1"):
            self.assertEqual(self.client.get(path).status_code, 200, path)

    def test_admin_pages_render(self):
        self.login("admin@example.com")
        for path in ("/admin", "/issues", "/archive", "/ticket/1"):
            self.assertEqual(self.client.get(path).status_code, 200, path)

    def test_logout_returns_to_home(self):
        self.login("student@example.com")
        response = self.client.get("/logout", follow_redirects=True)
        self.assertIn(b"You have been logged out", response.data)
        self.assertEqual(self.client.get("/dashboard").status_code, 302)


if __name__ == "__main__":
    unittest.main()