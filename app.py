from flask import Flask, render_template

app = Flask(__name__)

roles = {
    "Pet Owner": [
        "User Registration",
        "User Login",
        "Create Pet Profiles",
        "Book Appointments",
        "Paying Online",
        "View past visiting and medical history",
    ],
    "Clinic Staff": [
        "User Registration",
        "Making The Schedules",
        "Managing Appointments and Sending reminders (Confirm or reschedule)",
        "Generate Invoices",
        "Update medical Records",
        "Issue Digital Prescriptions",
        "View Past records",
        "Sending Vaccination reminders",
    ],
    "System Admin": [
        "Manage Roles",
        "Financial Reporting",
    ],
}


@app.route("/")
def index():
    return render_template("index.html", roles=roles)

@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/register")
def register():
    return render_template("register.html")

@app.route("/pet-owner")
def pet_owner():
    return render_template(
        "pet_owner.html",
        role_name="Pet Owner",
        features=roles["Pet Owner"],
    )


@app.route("/clinic-staff")
def clinic_staff():
    return render_template(
        "clinic_staff.html",
        role_name="Clinic Staff",
        features=roles["Clinic Staff"],
    )


@app.route("/system-admin")
def system_admin():
    return render_template(
        "system_admin.html",
        role_name="System Admin",
        features=roles["System Admin"],
    )


if __name__ == "__main__":
    app.run(debug=True)
