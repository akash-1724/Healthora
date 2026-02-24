# HEALTHORA Smart Pharmacy Management System

Full-stack RBAC pharmacy dashboard with React frontend, FastAPI backend, PostgreSQL, JWT auth, and Alembic migrations.

## Stack

- Frontend: React + Vite
- Backend: FastAPI + SQLAlchemy + Alembic
- Database: PostgreSQL
- Auth: JWT (Bearer token)
- Infra: Docker + docker-compose
- Python dependency manager: Poetry

## Implemented Tables

- `roles`
- `users`
- `patients`
- `drugs`
- `drug_batches`

## Seed Data

Startup seed reads core sheets from `HIS (1).xlsx` (mounted into backend container) for:

- roles
- users
- patients (capped by `HIS_PATIENT_SEED_LIMIT`, default `300`)
- drugs
- drug batches

Roles:

- system_admin
- chief_medical_officer
- pharmacy_manager
- senior_pharmacist
- staff_pharmacist
- inventory_clerk

Users:

- sysadmin / admin
- cmo1 / cmo
- pm1 / manager
- senior1 / senior
- staff1 / staff
- clerk1 / clerk

## API Highlights

Public:

- `POST /api/login`

Protected (Bearer token required):

- `GET /api/me`
- `GET /api/dashboard-access`
- `GET /api/dashboard-summary`
- `GET /api/dashboard-expiry`
- `GET /api/dashboard-notifications`
- `GET /api/inventory`
- `GET /api/drugs`
- `GET /api/patients`
- `GET /api/users` (admin only)
- `POST /api/users` (admin only)
- `PUT /api/users/{user_id}` (admin only)
- `PATCH /api/users/{user_id}/deactivate` (admin only)
- `PATCH /api/users/{user_id}/reset-password` (admin only)
- `DELETE /api/users/{user_id}` (admin only)
- `GET /api/roles` (admin only)
- `GET /api/departments` (admin only)
- `POST /api/patients` (CMO only)
- `PUT /api/patients/{patient_id}` (CMO + System Admin)
- `PATCH /api/patients/{patient_id}/archive` (CMO + System Admin)
- `POST /api/drugs` (Pharmacy Manager only)
- `PUT /api/drugs/{drug_id}` (Pharmacy Manager only)
- `PATCH /api/drugs/{drug_id}/disable` (Pharmacy Manager only)
- `POST /api/drug-batches` (Pharmacy Manager + Senior Pharmacist)
- `PATCH /api/drug-batches/{batch_id}/mark-expired` (Pharmacy Manager + Senior Pharmacist)
- `PUT /api/inventory/{batch_id}` (Manager/Senior/Staff/Clerk)
- `GET /api/ai-report` (stub: `{"message": "Coming soon"}`)

## Frontend Routes

- `/` -> Landing
- `/login` -> Login
- `/dashboard` -> Role-based dashboard

Sidebar modules are filtered based on role access returned from backend.

Current modules:

- `dashboard`
- `users` (system_admin)
- `patients` (system_admin, chief_medical_officer)
- `drugs` (all six roles)
- `inventory` (system_admin, pharmacy_manager, senior_pharmacist, staff_pharmacist, inventory_clerk)
- `ai_report` (system_admin, chief_medical_officer, pharmacy_manager)
- `settings` (system_admin)

## RBAC Matrix

- System Admin: Manage Users, View Dashboard, View Patients, View Drugs, View Inventory, AI report stub
- CMO: View/Add Patients, View Dashboard, View Drugs, AI report stub
- Pharmacy Manager: Dashboard, View/Add Drugs, Add Batch, Update Inventory, AI report stub
- Senior Pharmacist: Dashboard, View Drugs, Add Batch, Update Inventory
- Staff Pharmacist: Dashboard, View Drugs, Update Inventory
- Inventory Clerk: Dashboard, View Drugs, Update Inventory

## Run with Docker

```bash
cp .env.example .env
docker compose up --build
```

Open:

- Frontend: http://localhost:3000
- Backend docs: http://localhost:8000/docs

## Migration

Backend container runs:

```bash
alembic upgrade head
```

before starting Uvicorn.

## Documentation

Detailed file explanations are available in `help/`.
