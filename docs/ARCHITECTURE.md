# Architecture Notes

CampusFix uses a simple layered architecture built with Flask, PostgreSQL, and an optional Gemini integration.

## Layers

- **Presentation layer:** HTML templates rendered by Flask, styled with Bootstrap.
- **Application layer:** Flask routes and blueprints handle requests, authentication, authorization, input validation, complaint workflows, voting, and admin status updates.
- **Data layer:** PostgreSQL stores application data in the `users`, `complaints`, `status_history`, and `complaint_votes` tables. The application accesses PostgreSQL through Psycopg 3, using parameterized SQL queries.
- **AI layer:** The optional Gemini service provides complaint category and priority recommendations. These suggestions are advisory; administrators retain responsibility for final decisions.

## Request flow

1. A user interacts with a page in the presentation layer.
2. A Flask route validates the request and checks authentication and permissions where required.
3. The application reads or writes records in PostgreSQL through the database helper functions.
4. Where relevant and configured, the Gemini service may provide suggestions for a complaint.
5. Flask returns the rendered page or appropriate response to the user.

## Configuration

- `DATABASE_URL` identifies the PostgreSQL database used by the application.
- `TEST_DATABASE_URL` identifies the separate test database. The test helper requires its database name to end with `_test` to reduce the risk of running tests against a non-test database.
- Gemini integration is optional and depends on the configured API key.

The layers keep presentation, application logic, database access, and AI integration separated, making the project easier to maintain and test.
