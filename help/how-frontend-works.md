# How Frontend Works

1. React starts from `frontend/src/App.jsx`.
2. Login page calls backend login API.
3. Token is saved in localStorage.
4. Protected routes check token existence.
5. Top navigation stays visible on all protected pages.
6. Dashboard shows stock/expiry/notification cards.
7. Inventory page shows medicine batch table and placeholder buttons.
8. Reorder page shows reorder suggestions table.
9. Reports page provides AI report placeholder input/buttons.
10. Users page shows users list and add-user form.

No advanced styling, only simple inline styles.
