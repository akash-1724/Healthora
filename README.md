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

Data is expected to already exist in PostgreSQL.

Current default mode:

- `ENABLE_STARTUP_SEED=false` (no file-based loading on startup)
- `SEED_FAIL_OPEN=true` -> if seed fails, backend logs error and still starts (dev-friendly)

Use one-time manual SQL import to load data into database, then run the app normally.

Roles:

- system_admin
- chief_medical_officer
- pharmacy_manager
- senior_pharmacist
- staff_pharmacist
- inventory_clerk

Users:

- a.sharma / $123q (System Admin)
- j.doe / $123q (Chief Medical Officer)
- pharm.chief / $123q (Pharmacy Manager)
- s.patel / $123q (Senior Pharmacist)
- r.jones / $123q (Staff Pharmacist)
- inv.clerk1 / $123q (Inventory Clerk)

## API Highlights

Public:

- `POST /api/login`
- `GET /api/setup-status`
- `POST /api/register-sysadmin` (one-time bootstrap only)
- `POST /api/create-sysadmin` (system_admin only, for already initialized systems)

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
- `POST /api/drug-batches/bulk-upload` (CSV/XLSX upload for batch intake)
- `PATCH /api/drug-batches/{batch_id}/mark-expired` (Pharmacy Manager + Senior Pharmacist)
- `PUT /api/inventory/{batch_id}` (Manager/Senior/Staff/Clerk)

Bulk upload required columns: `drug_name,batch_no,expiry_date,purchase_price,selling_price,quantity_available`.
Optional columns: `generic_name,formulation,strength,schedule_type,low_stock_threshold,supplier_id,supplier_name`.
- `GET /api/ai-report` (AI status + schema readiness)
- `POST /api/ai-report/query` (natural language to SQL report)
- `POST /api/ai-report/generate-report` (preview report with KPIs + charts + narrative)
- `GET /api/ai-report/{report_id}/preview` (reload report preview)
- `POST /api/ai-report/{report_id}/download` (download report as `pdf` or `csv`)
- `GET /api/ai-report/rag/stats` (query cache stats)
- `DELETE /api/ai-report/rag/clear` (admin only, clear AI cache)

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

- System Admin: Manage Users, View Dashboard, View Patients, View Drugs, View Inventory, AI report
- CMO: View/Add Patients, View Dashboard, View Drugs, AI report
- Pharmacy Manager: Dashboard, View/Add Drugs, Add Batch, Update Inventory, AI report
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

## Sharing DB Data With a Friend

Important: PostgreSQL data is stored in Docker volume `postgres_data`; it is **not** included in git by default.

### Option A (recommended for consistent demo): regenerate seeded dataset

```bash
docker compose down -v
docker compose up --build
```

This recreates DB and applies the SQL dataset from `hospital_complete_v2.sql`.

By default, `docker-compose.yml` mounts `../hospital_complete_v2.sql` into the backend container at `/app/hospital_complete_v2.sql`.

### Option B (exact copy): export/import your DB

On your machine:

```bash
bash scripts/db_export.sh
```

This writes a dump under `backups/`.

On your friend's machine (after copying that dump file):

```bash
bash scripts/db_import.sh backups/<your_dump_file>.dump
```

Then verify quickly:

```bash
docker compose exec postgres psql -U healthora_user -d healthora -c "SELECT COUNT(*) FROM dispensing_records;"
docker compose exec postgres psql -U healthora_user -d healthora -c "SELECT MIN(dispensed_at), MAX(dispensed_at) FROM dispensing_records;"
```

## Migration

Backend container runs:

```bash
alembic upgrade head
```

before starting Uvicorn.

## Documentation

Detailed file explanations are available in `help/`.
