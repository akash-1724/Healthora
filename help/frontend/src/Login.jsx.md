# File: `frontend/src/Login.jsx`

Simple login page.

- Takes username and password.
- Calls `POST /api/login`.
- Saves JWT (`access_token`) and profile values in localStorage.
- Redirects to dashboard on success.

Default credentials to use manually:

- `sysadmin` / `admin`
- `cmo1` / `cmo`
- `pm1` / `manager`
- `senior1` / `senior`
- `staff1` / `staff`
- `clerk1` / `clerk`
