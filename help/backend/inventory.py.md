# File: `backend/inventory.py`

Inventory API route with fake in-memory data.

Endpoint:

- `GET /api/inventory`

Behavior:

- Requires Bearer token.
- Returns hardcoded item list (`Paracetamol`, `Syringe`, `Bandage`).

Why:

- Keeps MVP simple while frontend inventory page works.
