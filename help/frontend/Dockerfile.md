# File: `frontend/Dockerfile`

Builds frontend container.

Steps:

1. Use `node:20-alpine`
2. Install npm packages
3. Copy source code
4. Run `npm run dev`

Port:

- Exposes `3000`.
