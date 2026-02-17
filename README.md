# Healthora MVP (Very Simple)

Minimal college-level Hospital Management MVP.

## Stack

- Frontend: React + Vite
- Backend: FastAPI + SQLAlchemy
- DB: PostgreSQL
- Backend dependency manager: Poetry
- Infra: Docker + Docker Compose

## Features

- Login with plaintext password
- UUID token auth stored in DB
- `GET /api/me`
- Users: `GET /api/users`, `POST /api/users`
- Inventory: `GET /api/inventory` (fake in-memory data)
- Seed data: `admin` role and `admin/admin123` user

## Run

```bash
cp .env.example .env
docker compose up --build
```

Open:

- Frontend: http://localhost:3000
- Backend docs: http://localhost:8000/docs

## Frontend Flow

Login -> token in localStorage -> Dashboard -> Inventory / Reorder / Reports / Users

## File Explanations

Detailed explanations for each project file are in `help/`.
