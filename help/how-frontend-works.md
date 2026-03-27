# How Frontend Works (Simple)

Think of frontend as the hospital face.

1. React starts in `frontend/src/App.jsx`.
2. User opens login page and signs in.
3. Frontend saves JWT token (local or session storage).
4. User enters `/dashboard`.
5. Frontend asks backend: "What can this role access?"
6. Sidebar shows only allowed modules.
7. Clicking a module loads that screen (patients, inventory, AI report, reorder, etc.).
8. Each button (add/edit/delete) is shown only if permission is allowed.

Important idea:

- Frontend is for display and user actions.
- Backend is final authority for security and data.
