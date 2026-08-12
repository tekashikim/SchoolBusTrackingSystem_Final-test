import sqlite3
from getpass import getpass
from werkzeug.security import generate_password_hash

DB = "database.db"

c = sqlite3.connect(DB)
c.execute("""CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fullname TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL)""")
existing = c.execute("SELECT id FROM users WHERE role='Admin' LIMIT 1").fetchone()
if existing:
    c.close()
    print("An Admin account already exists. No new account was created.")
    raise SystemExit(0)

email = input("Private admin email: ").strip().lower()
fullname = input("Admin full name: ").strip()
password = getpass("Admin password (8+ characters): ")
confirm = getpass("Confirm password: ")

if not email or not fullname:
    c.close(); raise SystemExit("Name and email are required.")
if password != confirm:
    c.close(); raise SystemExit("Passwords do not match.")
if len(password) < 8:
    c.close(); raise SystemExit("Password must be at least 8 characters.")

try:
    c.execute("INSERT INTO users(fullname,email,password,role) VALUES(?,?,?,?)",
              (fullname, email, generate_password_hash(password), "Admin"))
    c.commit()
    print("Private Admin account created successfully.")
except sqlite3.IntegrityError:
    print("That email is already registered.")
finally:
    c.close()
