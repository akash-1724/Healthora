# How Frontend Works

1. React starts from `frontend/src/App.jsx`.
2. Landing page (`/`) shows project details + right-side login panel.
3. Login supports Remember Me and stores JWT in localStorage or sessionStorage.
4. `/dashboard` route is protected by token check.
5. Dashboard loads role access modules from backend.
6. Sidebar tabs are shown/hidden based on role.
7. Main panel renders module views (dashboard, users, patients, drugs, inventory, ai-report, settings).
8. Inventory uses tabs (Drugs / Batches / Stock View) with permission-gated actions.
9. Dashboard includes expiry filters, notification actions, and global search.

Styling is handled by `frontend/src/styles.css`.
