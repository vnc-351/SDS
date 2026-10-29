# CampusFix

CampusFix is a web app for reporting and tracking campus maintenance issues. Students report a problem with a photo, the community votes on what matters most, and administrators triage tickets and update their status. Google Gemini suggests a category and a priority to help administrators, but a human always makes the final decision.

## Features

**Students**
- Register and log in (new accounts are always students).
- Report an issue with a title, category, location, description and a JPG or PNG photo.
- Follow their own tickets from Pending to In Progress to Resolved, with a timestamped status history.
- Vote on open issues on the campus issue board (one vote per issue; it can be changed or removed).

**Administrators**
- Dashboard with live counts (total, pending, in progress, resolved).
- Search by title, location or ticket ID (`CF-00012`, `cf12`, `12`), and filter by status and category.
- Change a ticket's status (every change is recorded in the status history).
- See the AI suggestion (category, priority, short explanation) for each ticket. It is advisory only.

**For everyone**
- Resolved tickets stay in normal lists for one day, then move to the archive.
- Uploaded photos are private: only the student who reported the issue and administrators can view them.

## Tech stack

| Part | Technology |
|---|---|
| Backend | Python 3.12 or 3.13, Flask |
| Database | PostgreSQL, accessed with `psycopg` 3 |
| Authentication | Flask signed-cookie sessions, Werkzeug password hashing, role-based access control |
| Forms and security | Flask-WTF (CSRF), Pillow (image validation) |
| AI | Google Gemini through the `google-genai` SDK |
| Frontend | Jinja2 templates, Bootstrap 5, a little JavaScript |
| Tests | `unittest` |

## Project structure

```
SDS-main/
├── app.py               # App factory, error handlers, command-line entry point
├── config.py            # Reads .env; limits and shared lists (statuses, categories, priorities)
├── database.py          # PostgreSQL connection, schema creation, admin bootstrap
├── requirements.txt
├── .env.example         # Template for your private .env file
├── routes/              # Flask blueprints (auth, student, issues, admin, main)
├── services/            # Gemini integration
├── templates/           # Jinja2 pages
├── static/              # CSS, JavaScript, images
├── tests/               # 7 test files + pg_helpers.py
├── uploads/             # Uploaded photos (contents are not committed)
└── docs/                # Database notes and design documents
```

## Getting started (Windows, PowerShell)

### 1. Install the requirements
- Python 3.12 or 3.13. Python 3.14 is not supported yet because Pillow has no prebuilt package for it.
- PostgreSQL (any recent version), with its SQL Shell (`psql`).

### 2. Create the databases
Open SQL Shell, press Enter for server, database, port and user, type your password, then run:

```sql
CREATE DATABASE campusfix;
CREATE DATABASE campusfix_test;
```

`campusfix` is used by the app. `campusfix_test` is used only by the tests, which empty it on every run.

### 3. Create a virtual environment and install packages

```powershell
py -3.12 -m venv .venv
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned   # only if Activate.ps1 is blocked
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 4. Configure your environment

```powershell
Copy-Item .env.example .env
```

Edit `.env` and fill in the real values. This file is private and is never committed.

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Signs the session cookie. If missing, a random key is used and everyone is logged out on every restart. |
| `DATABASE_URL` | Connection URL of the app database, for example `postgresql://postgres:PASSWORD@localhost:5432/campusfix` |
| `TEST_DATABASE_URL` | Connection URL of the test database. Its name must end with `_test`. |
| `GEMINI_API_KEY` | Optional. Without it, tickets are still created but have no AI suggestion. |
| `ADMIN_EMAIL`, `ADMIN_PASSWORD` | Optional. If both are set, that admin account is created at startup. |

If your password contains special characters, write them percent-encoded in the URL, for example `@` as `%40`, `:` as `%3A`, `/` as `%2F`, `#` as `%23`.

### 5. Create an administrator (if you did not set ADMIN_EMAIL / ADMIN_PASSWORD)

```powershell
python app.py --create-admin --email admin@example.com --password YourPassword123
```

This never changes an existing student account.

### 6. Run the app

```powershell
python app.py
```

Open http://127.0.0.1:5000. Tables are created automatically on first start.

## Running the tests

```powershell
python -m unittest discover tests
```

The suite has 67 tests and takes about a minute. It uses the `campusfix_test` database and refuses to run if `TEST_DATABASE_URL` is missing, equals `DATABASE_URL`, or does not end in `_test`. The tests that use Gemini mock the API, so no key or internet is needed.

The line `ADMIN_EMAIL ... already registered as a student` that may appear in the output is a deliberate warning from `test_database.py`, not an error.

## Pages and access

| Path | Who | Purpose |
|---|---|---|
| `/` | everyone | Home page |
| `/register`, `/login`, `/logout` | everyone | Account pages |
| `/dashboard`, `/my_tickets` | logged-in users | A student's own tickets |
| `/report_issue` | logged-in users | Submit a new issue |
| `/issues` | logged-in users | Campus issue board |
| `/issues/<id>/vote` | students | Vote on an issue (POST) |
| `/ticket/<id>` | owner or admin | Ticket details and status history |
| `/archive` | logged-in users | Resolved tickets older than one day |
| `/admin` | admins | Dashboard, search and filters |
| `/admin/update_status/<id>` | admins | Change a ticket's status (POST) |
| `/uploads/<file>` | owner or admin | Protected photo download |
| `/health` | everyone | Health check, returns `{"status": "ok"}` |

## Security summary

- Passwords are hashed with Werkzeug. New registrations are always students.
- All forms carry CSRF tokens.
- Uploaded images are checked for extension, size (5 MB), pixel count (25 million) and real content with Pillow. The stored file gets a random name and an extension taken from the detected format.
- Photos are served only to the reporter and to administrators.
- Database access uses parameterised queries only.
- Known limits, planned for later: no login rate limiting, logout works through a GET request, sessions have no server-side revocation or lifetime.

## Team workflow

- Never commit directly to `main`. Use a feature branch and open a Pull Request.
- Before merging, check the **Files changed** tab for unintended deletions.
- Secrets are never pushed. `.env`, `.venv/`, `*.db` and the contents of `uploads/` are ignored.

## Roadmap

1. Server-side sessions stored in PostgreSQL.
2. Login rate limiting, logout through POST, pagination and filters, admin comments, password reset.
3. Deployment with `gunicorn`, a hosted PostgreSQL, environment variables on the host, persistent storage for `uploads/`, and `SESSION_COOKIE_SECURE`.

## Attribution

The home page photo is credited in `static/images/ATTRIBUTION.md` (CC BY-SA 4.0, Wikimedia Commons).
