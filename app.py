from flask import Flask, render_template, request, redirect, session
import sqlite3
import os

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.jinja_env.cache = {}
app.secret_key = "replace_with_a_strong_secret"

DB_PATH = "database.db"

# Ensure uploads folder exists (not heavily used here)
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "static", "uploads")
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# ---------- DATABASE SETUP ----------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # users table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('admin','user'))
    )''')

    # events table
    c.execute('''CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        date TEXT NOT NULL,
        description TEXT
    )''')

    # registrations table
    c.execute('''CREATE TABLE IF NOT EXISTS registrations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id INTEGER,
        name TEXT,
        email TEXT,
        FOREIGN KEY(event_id) REFERENCES events(id)
    )''')

    conn.commit()
    conn.close()


def get_db():
    return sqlite3.connect(DB_PATH)


# ---------- ROUTES ----------
@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        role = request.form.get("role")

        if not username or not password or not role:
            return render_template("login.html", error="Please fill all fields.")

        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=? AND role=?", (username, password, role))
        user = c.fetchone()
        conn.close()

        if user:
            session["user_id"] = user[0]
            session["username"] = user[1]
            session["role"] = user[3]
            return redirect("/home")
        else:
            return render_template("login.html", error="Invalid credentials. Try again.")

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        role = request.form.get("role")

        if not username or not password or not role:
            return render_template("register.html", error="Please fill all fields.")

        conn = get_db()
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", (username, password, role))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return render_template("register.html", error="Username already exists.")
        conn.close()
        return redirect("/login")
    return render_template("register.html")


@app.route("/home")
def home():
    if "user_id" not in session:
        return redirect("/login")
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM events")
    events = c.fetchall()
    conn.close()
    return render_template("home.html", events=events, role=session.get("role"), username=session.get("username"))


@app.route("/add", methods=["GET", "POST"])
def add_event():
    if "role" not in session or session.get("role") != "admin":
        return redirect("/home")

    if request.method == "POST":
        name = request.form.get("name")
        date = request.form.get("date")
        description = request.form.get("description")

        conn = get_db()
        c = conn.cursor()
        c.execute("INSERT INTO events (name, date, description) VALUES (?, ?, ?)", (name, date, description))
        conn.commit()
        conn.close()
        return redirect("/home")

    return render_template("add_event.html")


@app.route("/edit/<int:event_id>", methods=["GET", "POST"])
def edit_event(event_id):
    if "role" not in session or session.get("role") != "admin":
        return redirect("/home")

    conn = get_db()
    c = conn.cursor()

    if request.method == "POST":
        c.execute("UPDATE events SET name=?, date=?, description=? WHERE id=?",
                  (request.form.get("name"), request.form.get("date"), request.form.get("description"), event_id))
        conn.commit()
        conn.close()
        return redirect("/home")

    c.execute("SELECT * FROM events WHERE id=?", (event_id,))
    event = c.fetchone()
    conn.close()
    return render_template("edit_event.html", event=event)


@app.route("/delete/<int:event_id>")
def delete_event(event_id):
    if "role" not in session or session.get("role") != "admin":
        return redirect("/home")

    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM events WHERE id=?", (event_id,))
    conn.commit()
    conn.close()
    return redirect("/home")


@app.route("/register_event/<int:event_id>", methods=["GET", "POST"])
def register_event(event_id):
    conn = get_db()
    c = conn.cursor()

    # Get event details
    c.execute("SELECT * FROM events WHERE id=?", (event_id,))
    event = c.fetchone()

    success = None
    error = None

    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")

        if not name or not email:
            error = "⚠️ Please fill all fields."
        else:
            # Insert registration
            c.execute("INSERT INTO registrations (event_id, name, email) VALUES (?, ?, ?)", (event_id, name, email))
            conn.commit()
            success = "✅ Registration completed successfully!"

    conn.close()
    return render_template("register_event.html", event=event, success=success, error=error)


@app.route("/view_registrations/<int:event_id>")
def view_registrations(event_id):
    if "user_id" not in session or session["role"] != "admin":
        return redirect("/home")

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT name FROM events WHERE id=?", (event_id,))
    event = c.fetchone()

    c.execute("SELECT name, email FROM registrations WHERE event_id=?", (event_id,))
    registrations = c.fetchall()
    conn.close()
    return render_template("view_registrations.html", event=event, registrations=registrations)


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


if __name__ == "__main__":
    init_db()
    print("Available routes:")
    for r in app.url_map.iter_rules():
        print(r)
    print("✅ Flask app running...")
    app.run(debug=True)
