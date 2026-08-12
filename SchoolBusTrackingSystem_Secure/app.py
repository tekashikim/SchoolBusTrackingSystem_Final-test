from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import os
import sqlite3
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key-before-production")
DB = os.environ.get("DATABASE_PATH", "database.db")


def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    c = db()
    c.execute("""CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT, fullname TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL, password TEXT NOT NULL,
        role TEXT NOT NULL)""")
    c.execute("""CREATE TABLE IF NOT EXISTS buses(
        id INTEGER PRIMARY KEY AUTOINCREMENT, bus_number TEXT UNIQUE NOT NULL,
        driver_id INTEGER, route TEXT NOT NULL, status TEXT DEFAULT 'Available',
        latitude REAL DEFAULT -1.286389, longitude REAL DEFAULT 36.817223)""")
    c.execute("""CREATE TABLE IF NOT EXISTS students(
        id INTEGER PRIMARY KEY AUTOINCREMENT, admission_no TEXT UNIQUE NOT NULL,
        fullname TEXT NOT NULL, route TEXT NOT NULL, parent_id INTEGER)""")
    c.execute("""CREATE TABLE IF NOT EXISTS attendance(
        id INTEGER PRIMARY KEY AUTOINCREMENT, student_id INTEGER,
        bus_id INTEGER, status TEXT, recorded_at TEXT DEFAULT CURRENT_TIMESTAMP)""")

    
    rows = c.execute("SELECT id, password FROM users").fetchall()
    for row in rows:
        old = row["password"] or ""
        if not old.startswith(("scrypt:", "pbkdf2:")):
            c.execute("UPDATE users SET password=? WHERE id=?",
                      (generate_password_hash(old), row["id"]))

    admin_email = os.environ.get("ADMIN_EMAIL", "").strip().lower()
    admin_password = os.environ.get("ADMIN_PASSWORD", "")
    admin_name = os.environ.get("ADMIN_NAME", "School Administrator").strip() or "School Administrator"
    if admin_email and admin_password:
        exists = c.execute("SELECT id FROM users WHERE role='Admin' LIMIT 1").fetchone()
        if not exists:
            c.execute("INSERT INTO users(fullname,email,password,role) VALUES(?,?,?,?)",
                      (admin_name, admin_email, generate_password_hash(admin_password), "Admin"))

    c.commit()
    c.close()


def login_required(f):
    @wraps(f)
    def w(*a, **k):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        return f(*a, **k)
    return w


def admin_required(f):
    @wraps(f)
    def w(*a, **k):
        if session.get("role") != "Admin":
            return "Admin access required.", 403
        return f(*a, **k)
    return w


def driver_required(f):
    @wraps(f)
    def w(*a, **k):
        if session.get("role") != "Driver":
            return "Driver access required.", 403
        return f(*a, **k)
    return w


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        c = db()
        u = c.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        c.close()
        if u and check_password_hash(u["password"], password):
            session.clear()
            session.update(user_id=u["id"], fullname=u["fullname"], role=u["role"])
            if u["role"] == "Admin":
                return redirect(url_for("dashboard"))
            if u["role"] == "Driver":
                return redirect(url_for("driver"))
            return redirect(url_for("students"))
        error = "Invalid email or password."
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.route("/dashboard")
@login_required
def dashboard():
    c = db()
    stats = [
        c.execute("SELECT COUNT(*) FROM buses").fetchone()[0],
        c.execute("SELECT COUNT(*) FROM students").fetchone()[0],
        c.execute("SELECT COUNT(*) FROM users WHERE role='Driver'").fetchone()[0],
        c.execute("SELECT COUNT(*) FROM buses WHERE status='On Route'").fetchone()[0]]
    c.close()
    return render_template("dashboard.html", stats=stats)


@app.route("/map")
@login_required
def map_page():
    c = db()
    buses = c.execute("""SELECT b.*,u.fullname driver FROM buses b
        LEFT JOIN users u ON b.driver_id=u.id""").fetchall()
    c.close()
    return render_template("map.html", buses=buses)


@app.route("/api/buses")
@login_required
def api_buses():
    c = db()
    rows = c.execute("""SELECT b.*,u.fullname driver FROM buses b
        LEFT JOIN users u ON b.driver_id=u.id""").fetchall()
    c.close()
    return jsonify([dict(x) for x in rows])


@app.route("/driver")
@driver_required
def driver():
    c = db()
    bus = c.execute("SELECT * FROM buses WHERE driver_id=?", (session["user_id"],)).fetchone()
    c.close()
    return render_template("driver.html", bus=bus)


@app.route("/driver/location", methods=["POST"])
@driver_required
def location():
    data = request.get_json(silent=True) or {}
    try:
        lat = float(data["latitude"])
        lon = float(data["longitude"])
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise ValueError
    except (KeyError, TypeError, ValueError):
        return jsonify(success=False, message="Invalid location"), 400
    c = db()
    c.execute("UPDATE buses SET latitude=?,longitude=?,status='On Route' WHERE driver_id=?",
              (lat, lon, session["user_id"]))
    c.commit()
    c.close()
    return jsonify(success=True, message="Bus location updated successfully.")


@app.route("/driver/status", methods=["POST"])
@driver_required
def status():
    c = db()
    c.execute("UPDATE buses SET status=? WHERE driver_id=?",
              (request.form["status"], session["user_id"]))
    c.commit()
    c.close()
    return redirect(url_for("driver"))


@app.route("/buses")
@admin_required
def buses():
    c = db()
    rows = c.execute("""SELECT b.*,u.fullname driver FROM buses b
        LEFT JOIN users u ON b.driver_id=u.id""").fetchall()
    drivers = c.execute("SELECT id,fullname FROM users WHERE role='Driver'").fetchall()
    c.close()
    return render_template("buses.html", buses=rows, drivers=drivers)


@app.route("/add_bus", methods=["POST"])
@admin_required
def add_bus():
    c = db()
    try:
        c.execute("INSERT INTO buses(bus_number,driver_id,route) VALUES(?,?,?)",
                  (request.form["bus_number"], request.form.get("driver_id") or None, request.form["route"]))
        c.commit()
    except sqlite3.IntegrityError:
        return "That bus number already exists."
    finally:
        c.close()
    return redirect(url_for("buses"))


@app.route("/admin/users", methods=["GET", "POST"])
@admin_required
def manage_users():
    message = None
    error = None
    if request.method == "POST":
        fullname = request.form.get("fullname", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "").strip()
        if role not in ("Driver", "Parent"):
            error = "Only Driver or Parent accounts can be created here."
        elif len(password) < 8:
            error = "Password must be at least 8 characters."
        else:
            c = db()
            try:
                c.execute("INSERT INTO users(fullname,email,password,role) VALUES(?,?,?,?)",
                          (fullname, email, generate_password_hash(password), role))
                c.commit()
                message = f"{role} account created successfully."
            except sqlite3.IntegrityError:
                error = "That email is already registered."
            finally:
                c.close()
    c = db()
    users = c.execute("SELECT id,fullname,email,role FROM users ORDER BY id DESC").fetchall()
    c.close()
    return render_template("users.html", users=users, message=message, error=error)


@app.route("/students")
@login_required
def students():
    c = db()
    if session["role"] == "Parent":
        rows = c.execute("SELECT * FROM students WHERE parent_id=?", (session["user_id"],)).fetchall()
    else:
        rows = c.execute("SELECT * FROM students").fetchall()
    c.close()
    return render_template("students.html", students=rows)


@app.route("/add_student", methods=["POST"])
@admin_required
def add_student():
    c = db()
    try:
        c.execute("INSERT INTO students(admission_no,fullname,route,parent_id) VALUES(?,?,?,?)",
                  (request.form["admission_no"], request.form["fullname"], request.form["route"], request.form.get("parent_id") or None))
        c.commit()
    except sqlite3.IntegrityError:
        return "Admission number already exists."
    finally:
        c.close()
    return redirect(url_for("students"))


@app.route("/attendance")
@login_required
def attendance():
    c = db()
    records = c.execute("""SELECT a.*,s.fullname,b.bus_number FROM attendance a
        JOIN students s ON a.student_id=s.id JOIN buses b ON a.bus_id=b.id
        ORDER BY a.id DESC""").fetchall()
    ss = c.execute("SELECT * FROM students").fetchall()
    bs = c.execute("SELECT * FROM buses").fetchall()
    c.close()
    return render_template("attendance.html", records=records, students=ss, buses=bs)


@app.route("/attendance/add", methods=["POST"])
@login_required
def add_attendance():
    if session["role"] not in ("Admin", "Driver"):
        return "Access denied.", 403
    c = db()
    c.execute("INSERT INTO attendance(student_id,bus_id,status) VALUES(?,?,?)",
              (request.form["student_id"], request.form["bus_id"], request.form["status"]))
    c.commit()
    c.close()
    return redirect(url_for("attendance"))


@app.route("/reports")
@admin_required
def reports():
    c = db()
    stats = [
        c.execute("SELECT COUNT(*) FROM buses").fetchone()[0],
        c.execute("SELECT COUNT(*) FROM users WHERE role='Driver'").fetchone()[0],
        c.execute("SELECT COUNT(*) FROM students").fetchone()[0],
        c.execute("SELECT COUNT(*) FROM attendance").fetchone()[0]]
    c.close()
    return render_template("reports.html", stats=stats)


if __name__ == "__main__":
    init_db()
    app.run(debug=False, host="0.0.0.0", port=int(os.environ.get("PORT", 5002)))
