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

# À changer pour la prod
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

    # Table appointments (rendez-vous)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER NOT NULL,
            pet_name TEXT NOT NULL,
            appointment_date TEXT NOT NULL,  -- format YYYY-MM-DD
            appointment_time TEXT NOT NULL,  -- format HH:MM
            reason TEXT,
            status TEXT NOT NULL CHECK(status IN ('pending','confirmed','rescheduled','cancelled')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(owner_id) REFERENCES users(id)
        )
        """
    )

    # Créer un admin par défaut si aucun admin
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


# ---------- ROUTES PUBLIQUES ----------

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

        # Validation serveur
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

        # Email déjà utilisé ?
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

        # Insertion en base
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

        # Après register → login
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

        # Redirection par rôle
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

    monthly_revenue = 0  # Pour plus tard quand tu auras une table invoices

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


# Approver / rejeter un staff (admin)

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

    appointments = []
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
        appointments.append(
            {
                "pet_name": row["pet_name"],
                "appointment_date": row["appointment_date"],
                "appointment_time": row["appointment_time"],
                "reason": row["reason"],
                "status": status,
                "badge_class": badge_class,
                "status_label": status.capitalize(),
            }
        )

    return render_template(
        "pet-owner-dashboard.html",
        user_name=session.get("user_name"),
        appointments=appointments,
    )


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

@app.route("/appointments/book", methods=["GET", "POST"])
def book_appointment():
    if "user_id" not in session:
        return redirect(url_for("login"))
    if session.get("user_role") != "pet_owner":
        abort(403)

    errors = {}
    error_message = None
    success_message = None

    # Pour limiter la date min côté HTML
    today = dt.date.today()
    today_str = today.isoformat()

    # Valeurs du formulaire (pour les réafficher en cas d'erreur)
    form_data = {
        "pet_name": "",
        "appointment_date": "",
        "appointment_time": "",
        "reason": "",
    }

    if request.method == "POST":
        pet_name = request.form.get("pet_name", "").strip()
        appointment_date = request.form.get("appointment_date", "").strip()
        appointment_time = request.form.get("appointment_time", "").strip()
        reason = request.form.get("reason", "").strip()

        form_data["pet_name"] = pet_name
        form_data["appointment_date"] = appointment_date
        form_data["appointment_time"] = appointment_time
        form_data["reason"] = reason

        # ---- VALIDATION ----
        if not pet_name:
            errors["pet_name"] = "Pet name is required."

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

        # Reason pas obligatoire, mais tu peux mettre un minimum
        # if not reason:
        #     errors["reason"] = "Please provide a reason."

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
            )

        # ---- INSERT APPOINTMENT ----
        conn = get_db_connection()
        conn.execute(
            """
            INSERT INTO appointments (owner_id, pet_name, appointment_date, appointment_time, reason, status)
            VALUES (?, ?, ?, ?, ?, 'pending')
            """,
            (session["user_id"], pet_name, appointment_date, appointment_time, reason),
        )
        conn.commit()
        conn.close()

        # Après création → retour au dashboard Pet Owner
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
