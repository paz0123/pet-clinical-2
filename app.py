import sqlite3
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    abort,
)
from werkzeug.security import generate_password_hash, check_password_hash
import datetime as dt

app = Flask(__name__)

# Configuration
app.config["SECRET_KEY"] = "change-this-secret-key"

DB_NAME = "pet_clinic.db"


# ---------- DB UTILS ----------

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()

    # Table users
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('pet_owner','clinic_staff','admin')),
            is_approved INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # Table appointments
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER NOT NULL,
            pet_name TEXT NOT NULL,
            appointment_date TEXT NOT NULL,  -- YYYY-MM-DD
            appointment_time TEXT NOT NULL,  -- HH:MM
            reason TEXT,
            status TEXT NOT NULL CHECK(status IN ('pending','confirmed','rescheduled','cancelled')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(owner_id) REFERENCES users(id)
        )
        """
    )

    # Table pets
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS pets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            species TEXT,
            breed TEXT,
            age INTEGER,
            sex TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(owner_id) REFERENCES users(id)
        )
        """
    )

    # Table medical_records
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS medical_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pet_id INTEGER NOT NULL,
            appointment_id INTEGER,
            staff_id INTEGER NOT NULL,
            weight REAL,
            temperature REAL,
            diagnosis TEXT NOT NULL,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(pet_id) REFERENCES pets(id),
            FOREIGN KEY(appointment_id) REFERENCES appointments(id),
            FOREIGN KEY(staff_id) REFERENCES users(id)
        )
        """
    )

    # Table prescriptions
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS prescriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pet_id INTEGER NOT NULL,
            appointment_id INTEGER,
            medical_record_id INTEGER,
            staff_id INTEGER NOT NULL,
            drug_name TEXT NOT NULL,
            dosage TEXT NOT NULL,
            frequency TEXT,
            duration TEXT,
            instructions TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(pet_id) REFERENCES pets(id),
            FOREIGN KEY(appointment_id) REFERENCES appointments(id),
            FOREIGN KEY(medical_record_id) REFERENCES medical_records(id),
            FOREIGN KEY(staff_id) REFERENCES users(id)
        )
        """
    )

    # Table invoices (simple : total + statut)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER NOT NULL,
            appointment_id INTEGER,
            total_amount REAL NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('unpaid','paid','cancelled')),
            issued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            paid_at TIMESTAMP,
            notes TEXT,
            FOREIGN KEY(owner_id) REFERENCES users(id),
            FOREIGN KEY(appointment_id) REFERENCES appointments(id)
        )
        """
    )

    # Ajouter pet_id à appointments si la colonne n'existe pas encore
    try:
        conn.execute(
            "ALTER TABLE appointments ADD COLUMN pet_id INTEGER REFERENCES pets(id)"
        )
    except sqlite3.OperationalError:
        # Colonne déjà présente
        pass

    # Admin par défaut
    cur = conn.execute("SELECT id FROM users WHERE role='admin' LIMIT 1")
    if cur.fetchone() is None:
        admin_password = generate_password_hash("admin123")
        conn.execute(
            """
            INSERT INTO users (full_name, email, password_hash, role, is_approved)
            VALUES (?, ?, ?, ?, 1)
            """,
            ("System Admin", "admin@petclinic.local", admin_password, "admin"),
        )

    conn.commit()
    conn.close()



# ---------- PUBLIC ROUTES ----------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    errors = {}
    error_message = None

    if request.method == "POST":
        full_name = request.form.get("fullName", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirmPassword", "")
        user_role = request.form.get("userRole", "")
        terms = request.form.get("terms")

        # Serveur-side validation
        if not full_name:
            errors["fullName"] = "Full name is required."

        if not email:
            errors["email"] = "Email is required."

        if not password:
            errors["password"] = "Password is required."
        elif len(password) < 8:
            errors["password"] = "Password must be at least 8 characters long."

        if not confirm_password:
            errors["confirmPassword"] = "Please confirm your password."
        elif password != confirm_password:
            errors["confirmPassword"] = "Passwords do not match."

        if user_role not in ("pet_owner", "clinic_staff"):
            errors["userRole"] = "Please select a valid role."

        if not terms:
            error_message = "You must agree to the Terms & Conditions."

        # Email already used?
        if not errors.get("email") and email:
            conn = get_db_connection()
            existing = conn.execute(
                "SELECT id FROM users WHERE email = ?", (email,)
            ).fetchone()
            conn.close()
            if existing:
                errors["email"] = "An account with this email already exists."

        if errors or error_message:
            if not error_message:
                error_message = "Please correct the errors below."
            return render_template(
                "register.html",
                errors=errors,
                error_message=error_message,
                success_message=None,
            )

        # Data OK insert user
        password_hash = generate_password_hash(password)
        is_approved = 1 if user_role == "pet_owner" else 0

        conn = get_db_connection()
        conn.execute(
            """
            INSERT INTO users (full_name, email, password_hash, role, is_approved)
            VALUES (?, ?, ?, ?, ?)
            """,
            (full_name, email, password_hash, user_role, is_approved),
        )
        conn.commit()
        conn.close()

        # After registration, redirect to login
        return redirect(url_for("login"))

    # GET
    return render_template(
        "register.html",
        errors={},
        error_message=None,
        success_message=None,
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    errors = {}
    error_message = None
    success_message = None

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "")
        remember = request.form.get("remember")

        # Validation
        if not email:
            errors["email"] = "Email is required."
        if not password:
            errors["password"] = "Password is required."
        if role not in ("pet_owner", "clinic_staff", "admin"):
            errors["role"] = "Please select a valid role."

        if errors:
            error_message = "Please correct the errors below."
            return render_template(
                "login.html",
                errors=errors,
                error_message=error_message,
                success_message=None,
            )

        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()
        conn.close()

        if not user:
            error_message = "Invalid email or password."
            return render_template(
                "login.html",
                errors={"email": "Account not found."},
                error_message=error_message,
                success_message=None,
            )

        if user["role"] != role:
            error_message = "Role mismatch for this account."
            errors["role"] = "This account is not registered with this role."
            return render_template(
                "login.html",
                errors=errors,
                error_message=error_message,
                success_message=None,
            )

        if not check_password_hash(user["password_hash"], password):
            error_message = "Invalid email or password."
            errors["password"] = "Incorrect password."
            return render_template(
                "login.html",
                errors=errors,
                error_message=error_message,
                success_message=None,
            )

        if user["role"] == "clinic_staff" and not user["is_approved"]:
            error_message = "Your account is pending approval by an admin."
            return render_template(
                "login.html",
                errors={},
                error_message=error_message,
                success_message=None,
            )

        # Session ok
        session["user_id"] = user["id"]
        session["user_name"] = user["full_name"]
        session["user_role"] = user["role"]

        # Redirect based on role
        if user["role"] == "pet_owner":
            return redirect(url_for("pet_owner_dashboard"))
        elif user["role"] == "clinic_staff":
            return redirect(url_for("staff_dashboard"))
        else:  # admin
            return redirect(url_for("dashboard"))

    # GET
    return render_template(
        "login.html",
        errors={},
        error_message=None,
        success_message=None,
    )


# ---------- DASHBOARD ADMIN ----------

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    if session.get("user_role") != "admin":
        abort(403)

    conn = get_db_connection()
    total_pet_owners = conn.execute(
        "SELECT COUNT(*) AS c FROM users WHERE role='pet_owner'"
    ).fetchone()["c"]
    approved_staff = conn.execute(
        "SELECT COUNT(*) AS c FROM users WHERE role='clinic_staff' AND is_approved=1"
    ).fetchone()["c"]
    pending_staff_count = conn.execute(
        "SELECT COUNT(*) AS c FROM users WHERE role='clinic_staff' AND is_approved=0"
    ).fetchone()["c"]
    pending_staff = conn.execute(
        """
        SELECT id, full_name, email, created_at
        FROM users
        WHERE role='clinic_staff' AND is_approved=0
        ORDER BY created_at DESC
        """
    ).fetchall()
    conn.close()

    monthly_revenue = 0  # Placeholder for future feature

    return render_template(
        "admin-dashboard.html",
        user_name=session.get("user_name"),
        user_role=session.get("user_role"),
        total_pet_owners=total_pet_owners,
        approved_staff=approved_staff,
        pending_staff_count=pending_staff_count,
        pending_staff=pending_staff,
        monthly_revenue=monthly_revenue,
    )


# Approve / Reject clinic staff

@app.route("/admin/staff/<int:user_id>/approve", methods=["POST"])
def approve_staff(user_id):
    if "user_id" not in session or session.get("user_role") != "admin":
        abort(403)
    conn = get_db_connection()
    conn.execute(
        "UPDATE users SET is_approved=1 WHERE id=? AND role='clinic_staff'", (user_id,)
    )
    conn.commit()
    conn.close()
    return redirect(url_for("dashboard"))


@app.route("/admin/staff/<int:user_id>/reject", methods=["POST"])
def reject_staff(user_id):
    if "user_id" not in session or session.get("user_role") != "admin":
        abort(403)
    conn = get_db_connection()
    conn.execute("DELETE FROM users WHERE id=? AND role='clinic_staff'", (user_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("dashboard"))


# ---------- DASHBOARD PET OWNER ----------

@app.route("/dashboard/pet-owner")
def pet_owner_dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    if session.get("user_role") != "pet_owner":
        abort(403)

    today = dt.date.today().isoformat()

    conn = get_db_connection()
    rows = conn.execute(
        """
        SELECT pet_name, appointment_date, appointment_time, reason, status
        FROM appointments
        WHERE owner_id = ?
        ORDER BY appointment_date, appointment_time
        """,
        (session["user_id"],),
    ).fetchall()
    conn.close()

    upcoming_appointments = []
    past_appointments = []

    for row in rows:
        status = row["status"]
        if status == "pending":
            badge_class = "badge-pending"
        elif status == "confirmed":
            badge_class = "badge-confirmed"
        elif status == "rescheduled":
            badge_class = "badge-rescheduled"
        elif status == "cancelled":
            badge_class = "badge-cancelled"
        else:
            badge_class = "badge-pending"

        appt_dict = {
            "pet_name": row["pet_name"],
            "appointment_date": row["appointment_date"],
            "appointment_time": row["appointment_time"],
            "reason": row["reason"],
            "status": status,
            "badge_class": badge_class,
            "status_label": status.capitalize(),
        }

        # Separate upcoming and past appointments
        if row["appointment_date"] >= today:
            upcoming_appointments.append(appt_dict)
        else:
            past_appointments.append(appt_dict)

    return render_template(
        "pet-owner-dashboard.html",
        user_name=session.get("user_name"),
        upcoming_appointments=upcoming_appointments,
        past_appointments=past_appointments,
        today_str=today,
    )

# ---------- MY PETS ----------
@app.route("/owner/pets")
def my_pets():
    if "user_id" not in session:
        return redirect(url_for("login"))
    if session.get("user_role") != "pet_owner":
        abort(403)

    conn = get_db_connection()
    pets = conn.execute(
        """
        SELECT id, name, species, breed, age, sex, notes, created_at
        FROM pets
        WHERE owner_id = ?
        ORDER BY created_at DESC
        """,
        (session["user_id"],),
    ).fetchall()
    conn.close()

    return render_template(
        "my-pets.html",
        user_name=session.get("user_name"),
        pets=pets,
    )

# ---------- ADD PET ----------
@app.route("/owner/pets/add", methods=["GET", "POST"])
def add_pet():
    if "user_id" not in session:
        return redirect(url_for("login"))
    if session.get("user_role") != "pet_owner":
        abort(403)

    errors = {}
    error_message = None
    success_message = None
    form_data = {
        "name": "",
        "species": "",
        "breed": "",
        "age": "",
        "sex": "",
        "notes": "",
    }

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        species = request.form.get("species", "").strip()
        breed = request.form.get("breed", "").strip()
        age_raw = request.form.get("age", "").strip()
        sex = request.form.get("sex", "").strip()
        notes = request.form.get("notes", "").strip()

        form_data.update({
            "name": name,
            "species": species,
            "breed": breed,
            "age": age_raw,
            "sex": sex,
            "notes": notes,
        })

        # Validation
        if not name:
            errors["name"] = "Pet name is required."

        age = None
        if age_raw:
            try:
                age = int(age_raw)
                if age < 0:
                    errors["age"] = "Age cannot be negative."
            except ValueError:
                errors["age"] = "Age must be a number."

        if errors:
            error_message = "Please correct the errors below."
            return render_template(
                "pet-form.html",
                mode="add",
                errors=errors,
                error_message=error_message,
                success_message=None,
                form_data=form_data,
                user_name=session.get("user_name"),
            )

        # Insert
        conn = get_db_connection()
        conn.execute(
            """
            INSERT INTO pets (owner_id, name, species, breed, age, sex, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (session["user_id"], name, species, breed, age, sex, notes),
        )
        conn.commit()
        conn.close()

        return redirect(url_for("my_pets"))

    # GET
    return render_template(
        "pet-form.html",
        mode="add",
        errors=errors,
        error_message=error_message,
        success_message=success_message,
        form_data=form_data,
        user_name=session.get("user_name"),
    )


# ---------- EDIT PET ----------
@app.route("/owner/pets/<int:pet_id>/edit", methods=["GET", "POST"])
def edit_pet(pet_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    if session.get("user_role") != "pet_owner":
        abort(403)

    conn = get_db_connection()
    pet = conn.execute(
        """
        SELECT id, owner_id, name, species, breed, age, sex, notes
        FROM pets
        WHERE id = ?
        """,
        (pet_id,),
    ).fetchone()
    conn.close()

    if not pet or pet["owner_id"] != session["user_id"]:
        abort(404)

    errors = {}
    error_message = None
    success_message = None

    form_data = {
        "name": pet["name"],
        "species": pet["species"] or "",
        "breed": pet["breed"] or "",
        "age": pet["age"] if pet["age"] is not None else "",
        "sex": pet["sex"] or "",
        "notes": pet["notes"] or "",
    }

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        species = request.form.get("species", "").strip()
        breed = request.form.get("breed", "").strip()
        age_raw = request.form.get("age", "").strip()
        sex = request.form.get("sex", "").strip()
        notes = request.form.get("notes", "").strip()

        form_data.update({
            "name": name,
            "species": species,
            "breed": breed,
            "age": age_raw,
            "sex": sex,
            "notes": notes,
        })

        # Validation
        if not name:
            errors["name"] = "Pet name is required."

        age = None
        if age_raw:
            try:
                age = int(age_raw)
                if age < 0:
                    errors["age"] = "Age cannot be negative."
            except ValueError:
                errors["age"] = "Age must be a number."

        if errors:
            error_message = "Please correct the errors below."
            return render_template(
                "pet-form.html",
                mode="edit",
                errors=errors,
                error_message=error_message,
                success_message=None,
                form_data=form_data,
                user_name=session.get("user_name"),
                pet_id=pet_id,
            )

        # Update
        conn = get_db_connection()
        conn.execute(
            """
            UPDATE pets
            SET name = ?, species = ?, breed = ?, age = ?, sex = ?, notes = ?
            WHERE id = ? AND owner_id = ?
            """,
            (name, species, breed, age, sex, notes, pet_id, session["user_id"]),
        )
        conn.commit()
        conn.close()

        return redirect(url_for("my_pets"))

    # GET
    return render_template(
        "pet-form.html",
        mode="edit",
        errors=errors,
        error_message=error_message,
        success_message=success_message,
        form_data=form_data,
        user_name=session.get("user_name"),
        pet_id=pet_id,
    )


# ---------- DELETE PET ----------
@app.route("/owner/pets/<int:pet_id>/delete", methods=["POST"])
def delete_pet(pet_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    if session.get("user_role") != "pet_owner":
        abort(403)

    conn = get_db_connection()
    conn.execute(
        "DELETE FROM pets WHERE id = ? AND owner_id = ?",
        (pet_id, session["user_id"]),
    )
    conn.commit()
    conn.close()

    return redirect(url_for("my_pets"))

# ---------- DASHBOARD STAFF ----------

@app.route("/dashboard/staff")
def staff_dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    if session.get("user_role") != "clinic_staff":
        abort(403)

    today = dt.date.today().isoformat()

    conn = get_db_connection()
    rows = conn.execute(
        """
        SELECT a.id, a.pet_name, a.appointment_date, a.appointment_time,
               a.reason, a.status, u.full_name AS owner_name
        FROM appointments a
        JOIN users u ON a.owner_id = u.id
        WHERE a.appointment_date = ?
        ORDER BY a.appointment_time
        """,
        (today,),
    ).fetchall()
    conn.close()

    today_appointments = []
    for row in rows:
        status = row["status"]
        if status == "pending":
            badge_class = "badge-pending"
        elif status == "confirmed":
            badge_class = "badge-confirmed"
        elif status == "rescheduled":
            badge_class = "badge-rescheduled"
        else:
            badge_class = "badge-pending"
        today_appointments.append(
            {
                "id": row["id"],
                "pet_name": row["pet_name"],
                "owner_name": row["owner_name"],
                "appointment_date": row["appointment_date"],
                "appointment_time": row["appointment_time"],
                "reason": row["reason"],
                "status": status,
                "badge_class": badge_class,
                "status_label": status.capitalize(),
            }
        )

    return render_template(
        "staff-dashboard.html",
        user_name=session.get("user_name"),
        today_appointments=today_appointments,
        today_str=today,
    )


# ---------- CREATE MEDICAL RECORD ----------
@app.route("/staff/appointments/<int:appointment_id>/record", methods=["GET", "POST"])
def create_medical_record(appointment_id):
    if "user_id" not in session or session.get("user_role") != "clinic_staff":
        abort(403)

    today = dt.date.today().isoformat()

    conn = get_db_connection()
    appt = conn.execute(
        """
        SELECT a.id, a.owner_id, a.pet_id, a.pet_name, a.appointment_date,
               a.appointment_time, a.reason, a.status,
               u.full_name AS owner_name
        FROM appointments a
        JOIN users u ON a.owner_id = u.id
        WHERE a.id = ?
        """,
        (appointment_id,),
    ).fetchone()
    conn.close()

    if not appt:
        abort(404)

    # On vérifie qu'il y a bien un pet_id
    if appt["pet_id"] is None:
        # Dans un vrai projet on gérerait mieux ce cas, mais ici on bloque.
        abort(400)

    errors = {}
    error_message = None
    success_message = None

    form_data = {
        "weight": "",
        "temperature": "",
        "diagnosis": "",
        "notes": "",
    }

    if request.method == "POST":
        weight_raw = request.form.get("weight", "").strip()
        temperature_raw = request.form.get("temperature", "").strip()
        diagnosis = request.form.get("diagnosis", "").strip()
        notes = request.form.get("notes", "").strip()

        form_data.update({
            "weight": weight_raw,
            "temperature": temperature_raw,
            "diagnosis": diagnosis,
            "notes": notes,
        })

        # Validation
        weight = None
        if weight_raw:
            try:
                weight = float(weight_raw)
                if weight <= 0:
                    errors["weight"] = "Weight must be positive."
            except ValueError:
                errors["weight"] = "Weight must be a number."

        temperature = None
        if temperature_raw:
            try:
                temperature = float(temperature_raw)
            except ValueError:
                errors["temperature"] = "Temperature must be a number."

        if not diagnosis:
            errors["diagnosis"] = "Diagnosis is required."

        if errors:
            error_message = "Please correct the errors below."
            return render_template(
                "staff-medical-record.html",
                appointment=appt,
                form_data=form_data,
                errors=errors,
                error_message=error_message,
                success_message=None,
                user_name=session.get("user_name"),
                today_str=today,
            )

        # Insert medical record
        conn = get_db_connection()
        conn.execute(
            """
            INSERT INTO medical_records (
                pet_id, appointment_id, staff_id,
                weight, temperature, diagnosis, notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                appt["pet_id"],
                appt["id"],
                session["user_id"],
                weight,
                temperature,
                diagnosis,
                notes,
            ),
        )
        # Option : marquer le rendez-vous comme confirmé si ce n'est pas déjà le cas
        if appt["status"] == "pending":
            conn.execute(
                "UPDATE appointments SET status = 'confirmed' WHERE id = ?",
                (appt["id"],),
            )
        conn.commit()
        conn.close()

        return redirect(url_for("staff_dashboard"))

    # GET
    return render_template(
        "staff-medical-record.html",
        appointment=appt,
        form_data=form_data,
        errors=errors,
        error_message=error_message,
        success_message=success_message,
        user_name=session.get("user_name"),
        today_str=today,
    )


# ---------- PET MEDICAL HISTORY ----------
@app.route("/owner/pets/<int:pet_id>/history")
def pet_medical_history(pet_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    if session.get("user_role") != "pet_owner":
        abort(403)

    conn = get_db_connection()
    pet = conn.execute(
        """
        SELECT id, owner_id, name, species, breed, age, sex, notes
        FROM pets
        WHERE id = ?
        """,
        (pet_id,),
    ).fetchone()

    if not pet or pet["owner_id"] != session["user_id"]:
        conn.close()
        abort(404)

    records = conn.execute(
        """
        SELECT mr.id,
               mr.weight, mr.temperature, mr.diagnosis, mr.notes, mr.created_at,
               a.appointment_date, a.appointment_time,
               s.full_name AS staff_name
        FROM medical_records mr
        LEFT JOIN appointments a ON mr.appointment_id = a.id
        JOIN users s ON mr.staff_id = s.id
        WHERE mr.pet_id = ?
        ORDER BY mr.created_at DESC
        """,
        (pet_id,),
    ).fetchall()
    conn.close()

    return render_template(
        "pet-medical-history.html",
        user_name=session.get("user_name"),
        pet=pet,
        records=records,
    )



# ---------- BOOK APPOINTMENT ----------
@app.route("/appointments/book", methods=["GET", "POST"])
def book_appointment():
    if "user_id" not in session:
        return redirect(url_for("login"))
    if session.get("user_role") != "pet_owner":
        abort(403)

    today = dt.date.today()
    today_str = today.isoformat()

    # Get user pets
    conn = get_db_connection()
    pets = conn.execute(
        """
        SELECT id, name, species, breed
        FROM pets
        WHERE owner_id = ?
        ORDER BY created_at DESC
        """,
        (session["user_id"],),
    ).fetchall()
    conn.close()

    errors = {}
    error_message = None
    success_message = None

    form_data = {
        "pet_id": "",
        "appointment_date": "",
        "appointment_time": "",
        "reason": "",
    }

    if request.method == "POST":
        pet_id_raw = request.form.get("pet_id", "").strip()
        appointment_date = request.form.get("appointment_date", "").strip()
        appointment_time = request.form.get("appointment_time", "").strip()
        reason = request.form.get("reason", "").strip()

        form_data.update({
            "pet_id": pet_id_raw,
            "appointment_date": appointment_date,
            "appointment_time": appointment_time,
            "reason": reason,
        })

        # If no pets, cannot book
        if not pets:
            error_message = "You must add a pet before booking an appointment."
            return render_template(
                "book-appointment.html",
                errors=errors,
                error_message=error_message,
                success_message=None,
                form_data=form_data,
                today_str=today_str,
                user_name=session.get("user_name"),
                pets=pets,
            )

        # Validation pet_id
        pet_id = None
        if not pet_id_raw:
            errors["pet_id"] = "Please select a pet."
        else:
            try:
                pet_id = int(pet_id_raw)
            except ValueError:
                errors["pet_id"] = "Invalid pet selection."

        # Validation date
        if not appointment_date:
            errors["appointment_date"] = "Date is required."
        else:
            try:
                date_obj = dt.date.fromisoformat(appointment_date)
                if date_obj < today:
                    errors["appointment_date"] = "Date cannot be in the past."
            except ValueError:
                errors["appointment_date"] = "Invalid date format."

        # Validation time
        if not appointment_time:
            errors["appointment_time"] = "Time is required."

        if errors:
            error_message = "Please correct the errors below."
            return render_template(
                "book-appointment.html",
                errors=errors,
                error_message=error_message,
                success_message=None,
                form_data=form_data,
                today_str=today_str,
                user_name=session.get("user_name"),
                pets=pets,
            )

        # Verify pet belongs to owner
        conn = get_db_connection()
        pet = conn.execute(
            """
            SELECT id, name
            FROM pets
            WHERE id = ? AND owner_id = ?
            """,
            (pet_id, session["user_id"]),
        ).fetchone()

        if not pet:
            conn.close()
            errors["pet_id"] = "Please select a valid pet."
            error_message = "Please correct the errors below."
            return render_template(
                "book-appointment.html",
                errors=errors,
                error_message=error_message,
                success_message=None,
                form_data=form_data,
                today_str=today_str,
                user_name=session.get("user_name"),
                pets=pets,
            )

        # Insert appointment
        conn.execute(
            """
            INSERT INTO appointments (
                owner_id, pet_id, pet_name,
                appointment_date, appointment_time, reason, status
            )
            VALUES (?, ?, ?, ?, ?, ?, 'pending')
            """,
            (
                session["user_id"],
                pet["id"],
                pet["name"],
                appointment_date,
                appointment_time,
                reason,
            ),
        )
        conn.commit()
        conn.close()

        # Redirect to dashboard
        return redirect(url_for("pet_owner_dashboard"))

    # GET
    return render_template(
        "book-appointment.html",
        errors=errors,
        error_message=error_message,
        success_message=success_message,
        form_data=form_data,
        today_str=today_str,
        user_name=session.get("user_name"),
        pets=pets,
    )


# ---------- ADMIN USERS ----------
@app.route("/admin/users")
def admin_users():
    """Liste de tous les utilisateurs + filtres (réservé à l'admin)."""
    if "user_id" not in session:
        return redirect(url_for("login"))
    if session.get("user_role") != "admin":
        abort(403)

    role_filter = request.args.get("role_filter", "all")
    approval_filter = request.args.get("approval_filter", "all")

    conn = get_db_connection()

    query = """
        SELECT id, full_name, email, role, is_approved, created_at
        FROM users
        WHERE 1=1
    """
    params = []

    # Filter role
    if role_filter in ("pet_owner", "clinic_staff", "admin"):
        query += " AND role = ?"
        params.append(role_filter)

    # Filter approval (useful especially for clinic_staff)
    if approval_filter == "approved":
        query += " AND is_approved = 1"
    elif approval_filter == "pending":
        query += " AND is_approved = 0"

    query += " ORDER BY created_at DESC"

    all_users = conn.execute(query, params).fetchall()
    conn.close()

    return render_template(
        "admin-users.html",
        user_name=session.get("user_name"),
        all_users=all_users,
        role_filter=role_filter,
        approval_filter=approval_filter,
    )


# ---------- MODIFY USER ROLE ----------
@app.route("/admin/users/<int:user_id>/role", methods=["POST"])
def update_user_role(user_id):
    """Changer le rôle d’un utilisateur (admin uniquement)."""
    if "user_id" not in session:
        return redirect(url_for("login"))
    if session.get("user_role") != "admin":
        abort(403)

    new_role = request.form.get("role", "")

    if new_role not in ("pet_owner", "clinic_staff", "admin"):
        # Invalid role
        return redirect(url_for("admin_users"))

    conn = get_db_connection()
    user = conn.execute(
        "SELECT id FROM users WHERE id = ?", (user_id,)
    ).fetchone()

    if not user:
        conn.close()
        abort(404)

    conn.execute(
        "UPDATE users SET role = ? WHERE id = ?",
        (new_role, user_id),
    )
    conn.commit()
    conn.close()

    return redirect(url_for("admin_users"))


# ---------- MODIFY APPOINTMENT STATUS ----------
@app.route("/staff/appointments/<int:appointment_id>/status", methods=["POST"])
def update_appointment_status(appointment_id):
    if "user_id" not in session or session.get("user_role") != "clinic_staff":
        abort(403)

    new_status = request.form.get("status")
    if new_status not in ("pending", "confirmed", "rescheduled", "cancelled"):
        return redirect(url_for("staff_dashboard"))

    conn = get_db_connection()
    conn.execute(
        "UPDATE appointments SET status = ? WHERE id = ?",
        (new_status, appointment_id),
    )
    conn.commit()
    conn.close()

    return redirect(url_for("staff_dashboard"))

# ---------- RESCHEDULE APPOINTMENT ----------
@app.route("/staff/appointments/<int:appointment_id>/reschedule", methods=["GET", "POST"])
def reschedule_appointment(appointment_id):
    if "user_id" not in session or session.get("user_role") != "clinic_staff":
        abort(403)

    today = dt.date.today()
    today_str = today.isoformat()

    conn = get_db_connection()
    row = conn.execute(
        """
        SELECT a.id, a.pet_name, a.appointment_date, a.appointment_time,
               a.reason, a.status, u.full_name AS owner_name
        FROM appointments a
        JOIN users u ON a.owner_id = u.id
        WHERE a.id = ?
        """,
        (appointment_id,),
    ).fetchone()
    conn.close()

    if not row:
        abort(404)

    errors = {}
    error_message = None
    success_message = None

    # Pre-fill form data
    form_data = {
        "appointment_date": row["appointment_date"],
        "appointment_time": row["appointment_time"],
        "reason": row["reason"] or "",
    }

    if request.method == "POST":
        appointment_date = request.form.get("appointment_date", "").strip()
        appointment_time = request.form.get("appointment_time", "").strip()
        reason = request.form.get("reason", "").strip()

        form_data["appointment_date"] = appointment_date
        form_data["appointment_time"] = appointment_time
        form_data["reason"] = reason

        # Validation
        if not appointment_date:
            errors["appointment_date"] = "Date is required."
        else:
            try:
                date_obj = dt.date.fromisoformat(appointment_date)
                if date_obj < today:
                    errors["appointment_date"] = "Date cannot be in the past."
            except ValueError:
                errors["appointment_date"] = "Invalid date format."

        if not appointment_time:
            errors["appointment_time"] = "Time is required."

        
        # if not reason:
        #     errors["reason"] = "Please provide a reason.

        if errors:
            error_message = "Please correct the errors below."
            return render_template(
                "staff-reschedule.html",
                appointment=row,
                form_data=form_data,
                errors=errors,
                error_message=error_message,
                success_message=None,
                today_str=today_str,
                user_name=session.get("user_name"),
            )

        # Update appointment
        conn = get_db_connection()
        conn.execute(
            """
            UPDATE appointments
            SET appointment_date = ?, appointment_time = ?, reason = ?, status = 'rescheduled'
            WHERE id = ?
            """,
            (appointment_date, appointment_time, reason, appointment_id),
        )
        conn.commit()
        conn.close()

        return redirect(url_for("staff_dashboard"))

    # GET
    return render_template(
        "staff-reschedule.html",
        appointment=row,
        form_data=form_data,
        errors=errors,
        error_message=error_message,
        success_message=success_message,
        today_str=today_str,
        user_name=session.get("user_name"),
    )


# ---------- CREATE PRESCRIPTION ----------
@app.route("/staff/appointments/<int:appointment_id>/prescription/new", methods=["GET", "POST"])
def create_prescription(appointment_id):
    if "user_id" not in session or session.get("user_role") != "clinic_staff":
        abort(403)

    conn = get_db_connection()
    appt = conn.execute(
        """
        SELECT a.id, a.owner_id, a.pet_id, a.pet_name,
               a.appointment_date, a.appointment_time, a.reason, a.status,
               u.full_name AS owner_name
        FROM appointments a
        JOIN users u ON a.owner_id = u.id
        WHERE a.id = ?
        """,
        (appointment_id,),
    ).fetchone()
    conn.close()

    if not appt:
        abort(404)
    if appt["pet_id"] is None:
        abort(400)  # On a besoin d'un pet lié

    errors = {}
    error_message = None
    success_message = None

    form_data = {
        "drug_name": "",
        "dosage": "",
        "frequency": "",
        "duration": "",
        "instructions": "",
    }

    if request.method == "POST":
        drug_name = request.form.get("drug_name", "").strip()
        dosage = request.form.get("dosage", "").strip()
        frequency = request.form.get("frequency", "").strip()
        duration = request.form.get("duration", "").strip()
        instructions = request.form.get("instructions", "").strip()

        form_data.update({
            "drug_name": drug_name,
            "dosage": dosage,
            "frequency": frequency,
            "duration": duration,
            "instructions": instructions,
        })

        if not drug_name:
            errors["drug_name"] = "Drug name is required."
        if not dosage:
            errors["dosage"] = "Dosage is required."

        if errors:
            error_message = "Please correct the errors below."
            return render_template(
                "staff-prescription.html",
                appointment=appt,
                form_data=form_data,
                errors=errors,
                error_message=error_message,
                success_message=None,
                user_name=session.get("user_name"),
            )

        conn = get_db_connection()
        conn.execute(
            """
            INSERT INTO prescriptions (
                pet_id, appointment_id, medical_record_id,
                staff_id, drug_name, dosage, frequency, duration, instructions
            )
            VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?)
            """,
            (
                appt["pet_id"],
                appt["id"],
                session["user_id"],
                drug_name,
                dosage,
                frequency,
                duration,
                instructions,
            ),
        )
        conn.commit()
        conn.close()

        return redirect(url_for("staff_dashboard"))

    return render_template(
        "staff-prescription.html",
        appointment=appt,
        form_data=form_data,
        errors=errors,
        error_message=error_message,
        success_message=success_message,
        user_name=session.get("user_name"),
    )


# ---------- PET PRESCRIPTIONS ----------
@app.route("/owner/pets/<int:pet_id>/prescriptions")
def pet_prescriptions(pet_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    if session.get("user_role") != "pet_owner":
        abort(403)

    conn = get_db_connection()
    pet = conn.execute(
        """
        SELECT id, owner_id, name, species, breed, age, sex, notes
        FROM pets
        WHERE id = ?
        """,
        (pet_id,),
    ).fetchone()

    if not pet or pet["owner_id"] != session["user_id"]:
        conn.close()
        abort(404)

    rows = conn.execute(
        """
        SELECT p.id, p.drug_name, p.dosage, p.frequency, p.duration,
               p.instructions, p.created_at,
               a.appointment_date, a.appointment_time,
               s.full_name AS staff_name
        FROM prescriptions p
        LEFT JOIN appointments a ON p.appointment_id = a.id
        JOIN users s ON p.staff_id = s.id
        WHERE p.pet_id = ?
        ORDER BY p.created_at DESC
        """,
        (pet_id,),
    ).fetchall()
    conn.close()

    return render_template(
        "pet-prescriptions.html",
        user_name=session.get("user_name"),
        pet=pet,
        prescriptions=rows,
    )


# ---------- CREATE INVOICE ----------
@app.route("/staff/appointments/<int:appointment_id>/invoice/new", methods=["GET", "POST"])
def create_invoice(appointment_id):
    if "user_id" not in session or session.get("user_role") != "clinic_staff":
        abort(403)

    conn = get_db_connection()
    appt = conn.execute(
        """
        SELECT a.id, a.owner_id, a.pet_name, a.appointment_date, a.appointment_time,
               u.full_name AS owner_name
        FROM appointments a
        JOIN users u ON a.owner_id = u.id
        WHERE a.id = ?
        """,
        (appointment_id,),
    ).fetchone()
    conn.close()

    if not appt:
        abort(404)

    errors = {}
    error_message = None
    success_message = None

    form_data = {
        "total_amount": "",
        "status": "unpaid",
        "notes": "",
    }

    if request.method == "POST":
        total_raw = request.form.get("total_amount", "").strip()
        status = request.form.get("status", "unpaid")
        notes = request.form.get("notes", "").strip()

        form_data.update({
            "total_amount": total_raw,
            "status": status,
            "notes": notes,
        })

        total_amount = None
        if not total_raw:
            errors["total_amount"] = "Total amount is required."
        else:
            try:
                total_amount = float(total_raw)
                if total_amount <= 0:
                    errors["total_amount"] = "Total amount must be positive."
            except ValueError:
                errors["total_amount"] = "Total amount must be a number."

        if status not in ("unpaid", "paid", "cancelled"):
            errors["status"] = "Invalid status."

        if errors:
            error_message = "Please correct the errors below."
            return render_template(
                "staff-invoice-form.html",
                appointment=appt,
                form_data=form_data,
                errors=errors,
                error_message=error_message,
                success_message=None,
                user_name=session.get("user_name"),
            )

        conn = get_db_connection()
        paid_at = None
        if status == "paid":
            paid_at = dt.datetime.now().isoformat(timespec="seconds")

        conn.execute(
            """
            INSERT INTO invoices (
                owner_id, appointment_id, total_amount,
                status, issued_at, paid_at, notes
            )
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?)
            """,
            (
                appt["owner_id"],
                appt["id"],
                total_amount,
                status,
                paid_at,
                notes,
            ),
        )
        conn.commit()
        conn.close()

        return redirect(url_for("staff_dashboard"))

    return render_template(
        "staff-invoice-form.html",
        appointment=appt,
        form_data=form_data,
        errors=errors,
        error_message=error_message,
        success_message=success_message,
        user_name=session.get("user_name"),
    )

# ---------- OWNER INVOICES ----------
@app.route("/owner/invoices")
def owner_invoices():
    if "user_id" not in session:
        return redirect(url_for("login"))
    if session.get("user_role") != "pet_owner":
        abort(403)

    conn = get_db_connection()
    rows = conn.execute(
        """
        SELECT inv.id, inv.total_amount, inv.status, inv.issued_at, inv.paid_at,
               a.appointment_date, a.appointment_time, a.pet_name
        FROM invoices inv
        LEFT JOIN appointments a ON inv.appointment_id = a.id
        WHERE inv.owner_id = ?
        ORDER BY inv.issued_at DESC
        """,
        (session["user_id"],),
    ).fetchall()
    conn.close()

    return render_template(
        "owner-invoices.html",
        user_name=session.get("user_name"),
        invoices=rows,
    )


# ---------- LOGOUT ----------

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


# ---------- MAIN ----------

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
