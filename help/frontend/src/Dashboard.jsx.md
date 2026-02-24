# File: `frontend/src/Dashboard.jsx`

Role-based dashboard shell and module renderer.

- Left sidebar with modules filtered by backend role access.
- Top header with user role and logout/home actions.
- Uses backend-provided permissions to show/hide actions.
- Dashboard cards:
  - Usable Stock
  - Total Stock
  - Expiry Risk
  - Low Stock Alerts
  - Total Patients (CMO only)
- Role modules rendered in same page:
  - dashboard
  - users
  - patients
  - drugs
  - inventory
  - ai_report
  - settings

Permission-driven actions:

- `add_drug` shows Add Drug form.
- `add_batch` shows Add Batch form.
- `update_inventory` shows inventory quantity update form.
- `add_patients` shows Add Patient form.
- `view_ai_report` shows AI report stub message.

UI behavior:

- Inventory has tabs: `drugs`, `batches`, `stock`.
- Uses modal forms for add user/patient/drug/batch.
- Includes global search in header.
- Expiry section supports 30/60/90 day filters and risk badges.
- Notifications support Mark as Read and Clear All.
- Action buttons are wired to backend APIs for user/patient/drug/batch operations.

Data is loaded from backend APIs in `api.js`.
