# Intelligent Telecom Operations Platform

A React and FastAPI application for customer complaints, staff complaint management, telecom measurement exploration, and latency classification. Network measurements come from the project dataset and may include synthetic rows added by the seed script; this is not a live carrier feed.

## Requirements

- Python 3.11 or later
- Node.js and npm
- MySQL 8
- The Python packages listed in `backend/requirements.txt`; development tests additionally use `backend/requirements-dev.txt`

## MySQL Setup

Create the application schema using `database/schema/schema.sql`. The schema creates the `telecom_operations` database and its `users`, `complaints`, and `network_measurements` tables. The SQL migration under `database/migrations/` is for older installations; do not run it on a database that already has those columns.

## Environment

If `backend/.env` does not already exist, copy `.env.example` there and replace its placeholders locally. Do not overwrite an existing environment file. The backend reads `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, and `MYSQL_DATABASE`. `ML_MODEL_PATH` is optional and defaults to `ml/models/latency_classifier.joblib` relative to the repository root.

The frontend defaults to `http://localhost:8000`. To override it, set `VITE_API_BASE` in `frontend/.env` and restart Vite. Do not commit either `.env` file.

## Backend Setup and Run

From PowerShell at the repository root:

```powershell
python -m venv backend/venv
backend/venv/Scripts/Activate.ps1
python -m pip install -r backend/requirements.txt
python -m pip install -r backend/requirements-dev.txt
if (!(Test-Path backend/.env)) { Copy-Item .env.example backend/.env }
Set-Location backend
python -m uvicorn app.main:app --reload
```

Configure MySQL and the local environment file before starting the API. FastAPI serves on `http://localhost:8000` by default; the health endpoint is `/health`.

## Frontend Setup and Run

In another terminal from the repository root:

```powershell
Set-Location frontend
npm install
npm run dev
```

Vite prints the local URL, normally `http://localhost:5173`.

## Users (No Login)

Authentication has been removed: there is no login page, JWT, or role check, and every page and API endpoint is open. Customer actions run as one shared guest customer (`guest@local.invalid`), which the backend creates automatically on first use.

The "Assign Complaint" page lists rows in `users` with `role = 'staff'`. To get some, run `database/seed/seed_staff.sql` (see below). Do not expose this version to the public internet.

## Complaint Workflow

Customers submit complaints with type, subject, description, priority, and optional coordinates. All complaints are owned by the shared guest customer. New complaints start as `Pending`. The company side can assign a complaint and department, which sets it to `Assigned`, then update status among `Pending`, `Assigned`, `In Progress`, `Resolved`, and `Closed`. "My Complaints" shows the guest customer's complaints; "All Complaints" shows everything.

## ML Classifier Setup and Training

The API uses the latency classifier, not the older experimental RTT regressor. From the repository root, with the ML dependencies available:

```powershell
python -m ml.src.preprocessing
python -m ml.src.feature_engineering
python -m ml.src.classify
```

These commands clean the tracked source dataset, derive model features, train/evaluate the classifier, and generate `ml/models/latency_classifier.joblib`. The model and generated intermediate CSVs are ignored by Git; regenerate them locally after cloning. The older regressor scripts and exploratory notebooks are not used by the prediction API.

## Tests

Install test dependencies with `python -m pip install -r backend/requirements-dev.txt`, then run from the `backend` directory:

```powershell
python -m pytest tests
```

The API tests use an isolated in-memory SQLite database and do not modify MySQL. Prediction tests use a temporary model artifact. They do not require a provisioned account or a local trained model. Run `backend/test_db.py` separately only when intentionally checking a live MySQL connection.