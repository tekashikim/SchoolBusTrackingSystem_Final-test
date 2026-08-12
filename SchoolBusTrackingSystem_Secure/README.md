# School Bus Tracking System

A Flask + SQLite school transport prototype with Admin, Driver and Parent roles, bus management, student records, attendance and GPS live tracking.

## Security before going live
- There are **no public demo accounts** in the login page.
- Passwords are stored using Werkzeug password hashing.
- Do not publish passwords, database credentials or your `SECRET_KEY`.
- Set `SECRET_KEY`, `ADMIN_EMAIL`, `ADMIN_PASSWORD` and optionally `ADMIN_NAME` as private environment variables on your hosting provider. The first startup creates the Admin only when these variables are present and no Admin exists.
- Driver and Parent accounts can be created by an Admin from **Manage Users**.
- For a local project without environment variables, run `python create_admin.py` once to create your private Admin account.

## Local Windows setup
1. Open this folder in VS Code.
2. Run `run.bat` or:
   `python -m venv venv`
   `venv\\Scripts\\activate`
   `pip install -r requirements.txt`
   `python create_admin.py`
   `python app.py`
3. Open http://127.0.0.1:5002

## Live deployment
Use a production WSGI server such as Gunicorn on Linux hosting, configure the environment variables in the host dashboard, and use the host-provided `PORT` variable. Do not use Flask debug mode in production.

## Important
The included SQLite database may contain records from the local development version. Review or replace it before deployment. Never upload a database containing real student information to a public repository.
