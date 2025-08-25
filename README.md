# Foundations of Resilience Tracker API

This project implements a RESTful API for tracking wellbeing habits and
weekly assessments for counselling clients. Built with Flask and
SQLAlchemy, it provides endpoints to create, read, update and delete
clients, habits, weekly assessments and individual habit scores. Role
based access control ensures that counsellors can manage the system
while clients can only view and update their own data.

## Features

* **Custom habits for each client** – assign any master habit to a client
  with optional custom labels and display ordering.
* **Weekly check‑ins** – clients (or their counsellor) create
  assessments for each week and enter scores (0–10) for each habit.
  The average wellbeing score is calculated automatically.
* **Optional reflections** – assessments can include a free‑form
  comment to capture context for that week.
* **Soft deletes** – deleting clients, assessments or scores marks
  them as inactive rather than removing them from the database. This
  supports auditing and historical trend analysis.
* **Pagination and filtering** – list endpoints accept `limit` and
  `offset` query parameters, and assessments can be filtered by date
  range (`from` and `to`) to support efficient data retrieval.
* **Derived insights** – an `/api/clients/<id>/insights/latest`
  endpoint returns the latest wellbeing score and the change relative
  to the previous assessment, enabling simple trend analysis.
* **CRUD operations** – endpoints exist for creating, reading,
  updating and deleting clients, habits, assessments and scores.
* **Role based access control** – two user roles (`client` and
  `counsellor`) control who can perform which actions.
* **JSON Web Token authentication** – clients and counsellors log in
  via `/api/login` to receive an access token for subsequent requests.
* **Deployed on Render** – the included `render.yaml` provisions a
  PostgreSQL database and runs the app with Gunicorn.

## Running Locally

To get started locally:

1. Install dependencies using `pip install -r requirements.txt`.
2. Export environment variables. At minimum set `JWT_SECRET_KEY` and
   optionally `DATABASE_URL` (defaults to a SQLite file `resilience.db`).
3. Run the development server:

   ```bash
   python -m resilience_tracker.run
   ```

4. Access the API at `http://localhost:5000/api`.

Authentication is required for most endpoints. Register a user via
`/api/register`, then log in via `/api/login` to obtain a JWT token
(include it in the `Authorization: Bearer <token>` header).

## Deployment to Render

The project includes a `render.yaml` file that declares a free web
service and a free PostgreSQL database. When deploying the repository
to Render:

1. Create a new **Web Service** and select **Import from GitHub**.
2. On the "Name of service" screen choose a name and ensure the branch
   includes `render.yaml` at the root.
3. Render will automatically provision a database, install the
   dependencies, set environment variables and run `gunicorn
   resilience_tracker.run:app`.

All environment variables required for operation are managed by
Render, including `DATABASE_URL` (pointing at the provisioned
PostgreSQL instance) and a generated `JWT_SECRET_KEY`.

## API Overview

| Endpoint | Method | Description | Access |
|---|---|---|---|
| `/api/register` | POST | Register a new user (client or counsellor) | Public |
| `/api/login` | POST | Authenticate and receive a JWT | Public |
| `/api/clients` | GET | List all clients | Counsellor |
| `/api/clients` | POST | Create a new client | Counsellor |
| `/api/clients/<id>` | GET | View client profile | Counsellor / Self |
| `/api/clients/<id>` | PUT | Update client details | Counsellor / Self |
| `/api/clients/<id>` | DELETE | Delete client and related data | Counsellor |
| `/api/clients/<id>/habits` | GET | List a client's habits | Counsellor / Self |
| `/api/clients/<id>/habits` | POST | Assign a habit to a client | Counsellor |
| `/api/clients/<id>/assessments` | GET | List weekly assessments | Counsellor / Self |
| `/api/clients/<id>/assessments` | POST | Create a weekly assessment | Counsellor / Self |
| `/api/habits` | GET | List all master habits | Authenticated |
| `/api/habits` | POST | Create a new habit | Counsellor |
| `/api/habits/<id>` | PUT | Update a habit | Counsellor |
| `/api/habits/<id>` | DELETE | Delete a habit if unused | Counsellor |
| `/api/assessments/<id>` | GET | View assessment with scores | Counsellor / Self |
| `/api/assessments/<id>` | PUT | Update assessment comment | Counsellor / Self |
| `/api/assessments/<id>` | DELETE | Delete assessment | Counsellor / Self |
| `/api/assessments/<id>/scores` | GET | List scores for assessment | Counsellor / Self |
| `/api/assessments/<id>/scores` | POST | Add a score | Counsellor / Self |
| `/api/scores/<id>` | PUT | Update a score | Counsellor / Self |
| `/api/scores/<id>` | DELETE | Delete a score | Counsellor / Self |
| `/api/client-habits/<id>` | PUT | Update habit label/order | Counsellor / Self |
| `/api/client-habits/<id>` | DELETE | Unassign habit from client | Counsellor / Self |
| `/api/client-habits/<id>/scores` | GET | List scores for a habit across weeks | Counsellor / Self |
| `/api/clients/<id>/insights/latest` | GET | Latest wellbeing score and delta | Counsellor / Self |

Refer to the source code for detailed request/response structures and
error conditions.

## Error Handling

The API always returns JSON for errors. This makes it easier for clients and front-ends to understand what went wrong.

- 400 Bad Request – invalid payloads or missing fields.

{ "error": "VALIDATION_ERROR", "message": "Score must be between 1 and 10." }


- 401 Unauthorized / 403 Forbidden – login required or invalid token.

{ "error": "AUTH_ERROR", "message": "Invalid or expired access token." }


- 404 Not Found – when a resource doesn’t exist or has been soft-deleted.

{ "error": "NOT_FOUND", "message": "Client not found." }


- 409 Conflict – uniqueness constraint violations (e.g. duplicate email, duplicate habit order).

{ "error": "CONFLICT", "message": "Client already has a habit at order 1." }


- 422 Unprocessable Entity – semantically valid but fails business rules (e.g. more than 7 scores in a week).

{ "error": "SEMANTIC_ERROR", "message": "A habit can only have up to 7 scores per week." }


All other unexpected issues return a 500 Internal Server Error with a safe generic message, and the details are logged on the server for debugging.
