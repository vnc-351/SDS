# CampusFix: Low-Level Design (LLD)

## 1. Pages and routes

### Public pages
- `/` — home page.
- `/register` — student registration form.
- `/login` — login page.

### Student pages
- `/dashboard` — summary of the student's complaints.
- `/report_issue` — complaint submission form.
- `/my_tickets` — ticket list for the logged-in student.
- `/issues` — shared list of unresolved issues with upvote/downvote controls.
- `/issues/<id>/vote` — POST route to record, change, or remove a student's vote.
- `/archive` — resolved tickets that have been resolved for at least one day.
- `/ticket/<id>` — ticket detail page.

### Admin pages
- `/admin` — all complaints with filters and search.
- `/admin/update_status/<id>` — POST route for status changes.

## 2. Important functions and modules

- `create_app()` (`app.py`) — configures the Flask application, CSRF protection and error handlers, registers the blueprints, and provides the application entry point.
- `init_db()` (`database.py`) — creates the PostgreSQL tables if they do not already exist.
- `ensure_default_admin()` (`database.py`) — creates the configured administrator when `ADMIN_EMAIL` and `ADMIN_PASSWORD` are provided.
- `get_db()` / `close_db()` (`database.py`) — manages the database connection for the current Flask request.
- `login_required()` (`routes/auth_routes.py`) — checks that a user is logged in and that the account still exists.
- `role_required()` (`routes/auth_routes.py`) — checks access permissions by user role.
- `read_valid_image()` (`routes/issue_routes.py`) — validates an uploaded image's type, size, and actual image content.
- `ticket_ref()` (`database.py`) — creates a readable ticket ID such as `CF-00001`.
- `get_ticket_ai_suggestions()` (`services/gemini_service.py`) — calls Gemini and validates its response.
- `vote_for_issue()` — records a student's vote for an issue, allowing the vote to be changed or removed.

## 3. Database tables

CampusFix uses PostgreSQL through Psycopg 3. Connections use `dict_row`, so query results can be accessed by column name, for example `row["title"]`.

### `users`

- `id` — integer identity primary key.
- `name` — student's full name.
- `email` — unique email address, stored in lower case.
- `password_hash` — Werkzeug password hash; the original password is not stored.
- `role` — account role, such as `student` or `admin`.
- `created_at` — account creation timestamp.

### `complaints`

- `id` — integer identity primary key.
- `user_id` — foreign key referencing `users.id`.
- `title` — short issue title.
- `category` — issue category.
- `location` — location of the issue on campus.
- `description` — issue details.
- `image_filename` — generated filename for the uploaded image.
- `status` — complaint status, such as `Pending`, `In Progress`, or `Resolved`.
- `ai_category` — category suggested by Gemini.
- `ai_priority` — priority suggested by Gemini.
- `ai_explanation` — explanation for the AI suggestion.
- `created_at` — complaint creation timestamp.
- `updated_at` — last status/update timestamp.

### `status_history`

- `id` — integer identity primary key.
- `complaint_id` — foreign key referencing `complaints.id`.
- `previous_status` — status before the change.
- `new_status` — status after the change.
- `changed_by` — user/admin responsible for the change.
- `changed_at` — timestamp of the status change.

### `complaint_votes`

- `id` — integer identity primary key.
- `complaint_id` — foreign key referencing `complaints.id`.
- `user_id` — foreign key referencing `users.id`.
- `vote` — `1` for an upvote or `-1` for a downvote.
- `created_at` — vote creation timestamp.

A student should have at most one vote per complaint. The database constraints and voting logic prevent duplicate votes for the same student and complaint.

## 4. Database access and SQL conventions

- `DATABASE_URL` configures the main PostgreSQL database.
- `TEST_DATABASE_URL` configures the separate test database; its database name must end in `_test`.
- Psycopg 3 is used for database connections, with `dict_row` for dictionary-style results.
- SQL query parameters use `%s` placeholders. User input is passed as parameters rather than concatenated into SQL statements.
- New identity values are retrieved using `INSERT ... RETURNING id` instead of SQLite's `lastrowid`.
- PostgreSQL date/time expressions use syntax such as `NOW() - INTERVAL '1 day'`.
- Writes are committed explicitly. Failed operations should be rolled back rather than leaving partial changes.
- Database initialization uses `IF NOT EXISTS` and a PostgreSQL advisory lock to reduce conflicts when multiple application workers start together.

## 5. Validation and access-control rules

- Student registration requires a full name, email, password, and password confirmation.
- Complaint submission requires a title, category, location, description, and image.
- Image uploads accept JPG and PNG files and are checked for size and valid image content.
- Admin-only routes enforce permissions on the server, not only in the user interface.
- Students can access only their own private tickets and uploaded photos; administrators can access all tickets.
- Each student has at most one vote per issue and can change or remove that vote.
- Resolved complaints older than one day are shown in the archive and remain stored in the database.
- Database queries use parameterized values to reduce SQL injection risk.

## 6. AI priority levels

Gemini suggests one of four priority levels: `Critical`, `Important`, `Normal`, or `Low`. These suggestions are advisory only; an administrator makes the final decision.

## 7. Gemini integration

The Gemini integration is separated into `services/gemini_service.py` so AI logic remains distinct from route logic. The service handles a missing API key and validates the returned JSON before the application saves AI suggestions. If the AI service is unavailable, complaint reporting should still be able to continue without AI suggestions.
