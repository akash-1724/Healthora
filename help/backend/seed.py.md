# File: `backend/seed.py`

Seed data initializer.

Source:

- Reads core datasets from `HIS (1).xlsx` using workbook XML parsing (no external Excel dependency).
- Uses sheets: `Role`, `User `, `Department`, `Paitent`, `Drug`, `Drug_Batch`.

What it seeds:

- Roles:
  - system_admin
  - chief_medical_officer
  - pharmacy_manager
  - senior_pharmacist
  - staff_pharmacist
  - inventory_clerk
- Users:
  - sysadmin/admin
  - cmo1/cmo
  - pm1/manager
  - senior1/senior
  - staff1/staff
  - clerk1/clerk
- Sample patients
- Sample drugs and drug batches

Additional behavior:

- `HIS_PATIENT_SEED_LIMIT` controls how many patient rows to load from workbook.
- Keeps required demo users (`sysadmin`, `cmo1`, `pm1`, `senior1`, `staff1`, `clerk1`) synchronized for login testing.

Data source alignment:

- Role and inventory naming follows the provided XLSX structure.
- Includes compatibility mapping for legacy role/user names.
- Synchronizes PostgreSQL sequences after seeding explicit IDs, so new inserts do not collide on primary keys.
