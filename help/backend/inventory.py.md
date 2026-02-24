# File: `backend/inventory.py`

Inventory and operational data routes.

Endpoints:

- `GET /api/inventory` (drug batch list)
- `GET /api/drugs`
- `POST /api/drugs` (add drug)
- `PUT /api/drugs/{drug_id}` (edit drug)
- `PATCH /api/drugs/{drug_id}/disable`
- `POST /api/drug-batches` (add batch)
- `PATCH /api/drug-batches/{batch_id}/mark-expired`
- `PUT /api/inventory/{batch_id}` (update quantity)
- `GET /api/patients`
- `POST /api/patients` (add patient)
- `PUT /api/patients/{patient_id}` (edit patient)
- `PATCH /api/patients/{patient_id}/archive`
- `GET /api/dashboard-summary`
- `GET /api/ai-report` (stub)

Behavior:

- Requires Bearer token.
- Enforces permission checks by endpoint.
- Reads real PostgreSQL data from `drugs`, `drug_batches`, and `patients`.
- Dashboard summary includes low stock alerts using each drug's low stock threshold.

Special note:

- `/api/ai-report` intentionally returns `{ "message": "Coming soon" }`.
