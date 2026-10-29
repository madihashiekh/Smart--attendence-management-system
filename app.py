
from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from datetime import date
from functools import wraps

app = Flask(__name__)

app.secret_key = "smart_attendance_secret_key"

DATABASE = "attendance.db"


# Database Connection
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# Create Database Tables
def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            roll_no TEXT UNIQUE NOT NULL,
            course TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            attendance_date TEXT NOT NULL,
            status TEXT NOT NULL,
            UNIQUE(student_id, attendance_date),
            FOREIGN KEY(student_id) REFERENCES students(id)
        )
    """)

    conn.commit()
    conn.close()


# Login Required
def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))

        return func(*args, **kwargs)

    return wrapper


# Admin Login
@app.route("/", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        if username == "admin" and password == "admin123":

            session["logged_in"] = True

            return redirect(url_for("dashboard"))

        flash("Invalid username or password")

    return render_template("login.html")


# Dashboard
@app.route("/dashboard")
@login_required
def dashboard():

    conn = get_db()

    students = conn.execute(
        "SELECT * FROM students ORDER BY roll_no"
    ).fetchall()

    today = date.today().isoformat()

    records = conn.execute("""
        SELECT students.name,
               students.roll_no,
               attendance.status
        FROM attendance
        JOIN students
        ON attendance.student_id = students.id
        WHERE attendance.attendance_date = ?
        ORDER BY students.roll_no
    """, (today,)).fetchall()

    total_students = len(students)

    present = sum(
        1 for record in records
        if record["status"] == "Present"
    )

    absent = sum(
        1 for record in records
        if record["status"] == "Absent"
    )

    conn.close()

    return render_template(
        "dashboard.html",
        students=students,
        records=records,
        today=today,
        total=total_students,
        present=present,
        absent=absent
    )


# Add Student
@app.route("/add_student", methods=["POST"])
@login_required
def add_student():

    name = request.form["name"].strip()
    roll_no = request.form["roll_no"].strip()
    course = request.form["course"].strip()

    if not name or not roll_no or not course:
        flash("Please fill all student details")
        return redirect(url_for("dashboard"))

    conn = get_db()

    try:

        conn.execute("""
            INSERT INTO students (name, roll_no, course)
            VALUES (?, ?, ?)
        """, (name, roll_no, course))

        conn.commit()

        flash("Student added successfully!")

    except sqlite3.IntegrityError:

        flash("Roll number already exists")

    finally:

        conn.close()

    return redirect(url_for("dashboard"))


# Mark Attendance
@app.route("/mark_attendance", methods=["POST"])
@login_required
def mark_attendance():

    student_id = request.form["student_id"]
    attendance_date = request.form["attendance_date"]
    status = request.form["status"]

    if status not in ["Present", "Absent"]:
        flash("Invalid attendance status")
        return redirect(url_for("dashboard"))

    conn = get_db()

    conn.execute("""
        INSERT INTO attendance (
            student_id,
            attendance_date,
            status
        )
        VALUES (?, ?, ?)

        ON CONFLICT(student_id, attendance_date)
        DO UPDATE SET status = excluded.status
    """, (student_id, attendance_date, status))

    conn.commit()
    conn.close()

    flash("Attendance saved successfully!")

    return redirect(url_for("dashboard"))


# Attendance History
@app.route("/records")
@login_required
def records():

    conn = get_db()

    attendance_records = conn.execute("""
        SELECT students.name,
               students.roll_no,
               students.course,
               attendance.attendance_date,
               attendance.status
        FROM attendance
        JOIN students
        ON attendance.student_id = students.id
        ORDER BY attendance.attendance_date DESC
    """).fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        students=[],
        records=attendance_records,
        history=True,
        today=date.today().isoformat(),
        total=0,
        present=0,
        absent=0
    )


# Admin Logout
@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


# Initialize Database
init_db()


# Run Application
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
      )
      
