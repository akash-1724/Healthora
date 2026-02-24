# File: `backend/models.py`

Defines database tables.

Tables:

- `Role`: `id`, `name`, `display_name`
- `User`: `user_id`, `username`, `password`, `role_id`, `is_active`, `created_at`
- `Patient`: `patient_id`, `name`, `gender`, `contact`, `dob`
- `Drug`: `drug_id`, `drug_name`, `generic_name`, `formulation`, `strength`, `schedule_type`
- `DrugBatch`: `batch_id`, `drug_id`, `batch_no`, `expiry_date`, `purchase_price`, `selling_price`, `quantity_available`

Library used:

- SQLAlchemy ORM (Column, relationship, ForeignKey).

Note:

- Password is plain text by project requirement.
- `DrugBatch.drug_id` has FK to `Drug.drug_id`.
