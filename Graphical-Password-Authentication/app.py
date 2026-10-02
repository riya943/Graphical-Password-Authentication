import hashlib
import os
import secrets
import smtplib
import sqlite3
from email.message import EmailMessage
from pathlib import Path
from datetime import datetime, timedelta, timezone

from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key-before-production")

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "database.db"
RESET_TOKEN_MINUTES = 30

IMAGE_CHOICES = [
    ("arc", "Arc"), ("rings", "Rings"), ("maze", "Maze"), ("waves", "Waves"),
    ("diamond", "Diamond"), ("spiral", "Spiral"), ("grid", "Grid"), ("petals", "Petals"),
    ("hex", "Hexagon"), ("sun", "Sunburst"), ("triangles", "Triangles"), ("cross", "Cross"),
    ("orbit", "Orbit"), ("zigzag", "Zigzag"), ("target", "Target"), ("lanes", "Lanes"),
]


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT,
            password_hash TEXT NOT NULL,
            graphical_password_hash TEXT NOT NULL
        )
    """)
    # Upgrade databases created by the previous version.
    columns = {row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
    if "email" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN email TEXT")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token_hash TEXT UNIQUE NOT NULL,
            expires_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    conn.commit()
    conn.close()


def token_hash(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def send_reset_email(recipient, reset_url):
    server = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    port = int(os.environ.get("MAIL_PORT", "587"))
    sender = os.environ.get("MAIL_USERNAME")
    password = os.environ.get("MAIL_PASSWORD")

    if not sender or not password:
        raise RuntimeError("Email settings are not configured. Set MAIL_USERNAME and MAIL_PASSWORD.")

    msg = EmailMessage()
    msg["Subject"] = "Reset your Graphical Auth password"
    msg["From"] = sender
    msg["To"] = recipient
    msg.set_content(
        "We received a request to reset your Graphical Auth password.\n\n"
        f"Open this link within {RESET_TOKEN_MINUTES} minutes:\n{reset_url}\n\n"
        "The link can be used once. If you did not request this, you can ignore this email."
    )

    with smtplib.SMTP(server, port, timeout=20) as smtp:
        smtp.starttls()
        smtp.login(sender, password)
        smtp.send_message(msg)


@app.route("/")
def home():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        sequence = request.form.get("graphical_password", "").strip()

        if not username or not email or not password or not sequence:
            flash("Please fill in all fields.")
            return redirect(url_for("register"))

        if "@" not in email or "." not in email.rsplit("@", 1)[-1]:
            flash("Please enter a valid email address.")
            return redirect(url_for("register"))

        selected = sequence.split(",")
        valid_names = {item[0] for item in IMAGE_CHOICES}
        if len(selected) < 3:
            flash("Choose at least 3 images for your graphical password.")
            return redirect(url_for("register"))
        if len(set(selected)) != len(selected):
            flash("Each image can be selected only once in the graphical password.")
            return redirect(url_for("register"))
        if any(item not in valid_names for item in selected):
            flash("Invalid image selection.")
            return redirect(url_for("register"))

        conn = get_db()
        try:
            conn.execute(
                "INSERT INTO users (username, email, password_hash, graphical_password_hash) VALUES (?, ?, ?, ?)",
                (username, email, generate_password_hash(password), generate_password_hash(",".join(selected))),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            flash("Username already exists.")
            return redirect(url_for("register"))
        conn.close()
        flash("Registration successful. Please log in.")
        return redirect(url_for("login"))

    return render_template("register.html", images=IMAGE_CHOICES)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        sequence = request.form.get("graphical_password", "").strip()

        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            if sequence and check_password_hash(user["graphical_password_hash"], sequence):
                session["user_id"] = user["id"]
                session["username"] = user["username"]
                return redirect(url_for("dashboard"))

        flash("Invalid username, password, or graphical password.")
        return redirect(url_for("login"))

    return render_template("login.html", images=IMAGE_CHOICES)


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        conn = get_db()
        user = conn.execute("SELECT id, email FROM users WHERE username = ?", (username,)).fetchone()

        if user and user["email"]:
            raw_token = secrets.token_urlsafe(32)
            expires = datetime.now(timezone.utc) + timedelta(minutes=RESET_TOKEN_MINUTES)
            conn.execute("DELETE FROM password_reset_tokens WHERE user_id = ?", (user["id"],))
            conn.execute(
                "INSERT INTO password_reset_tokens (user_id, token_hash, expires_at) VALUES (?, ?, ?)",
                (user["id"], token_hash(raw_token), expires.isoformat()),
            )
            conn.commit()
            reset_url = url_for("reset_password", token=raw_token, _external=True)
            try:
                send_reset_email(user["email"], reset_url)
            except Exception:
                conn.execute("DELETE FROM password_reset_tokens WHERE user_id = ?", (user["id"],))
                conn.commit()
                conn.close()
                flash("The reset email could not be sent. Check the email settings in the README.")
                return redirect(url_for("forgot_password"))

        conn.close()
        flash("If that username has a registered email, a reset link has been sent.")
        return redirect(url_for("login"))

    return render_template("forgot_password.html")


@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    conn = get_db()
    reset = conn.execute("""
        SELECT prt.*, u.username
        FROM password_reset_tokens prt
        JOIN users u ON u.id = prt.user_id
        WHERE prt.token_hash = ?
    """, (token_hash(token),)).fetchone()

    if not reset:
        conn.close()
        flash("This reset link is invalid or has already been used.")
        return redirect(url_for("login"))

    try:
        expires_at = datetime.fromisoformat(reset["expires_at"])
    except ValueError:
        expires_at = datetime.min.replace(tzinfo=timezone.utc)

    if datetime.now(timezone.utc) >= expires_at:
        conn.execute("DELETE FROM password_reset_tokens WHERE id = ?", (reset["id"],))
        conn.commit()
        conn.close()
        flash("This reset link has expired. Please request a new one.")
        return redirect(url_for("forgot_password"))

    if request.method == "POST":
        password = request.form.get("password", "")
        sequence = request.form.get("graphical_password", "").strip()
        selected = sequence.split(",") if sequence else []
        valid_names = {item[0] for item in IMAGE_CHOICES}

        if not password or len(password) < 6:
            flash("New normal password must be at least 6 characters.")
            conn.close()
            return redirect(url_for("reset_password", token=token))
        if len(selected) < 3 or len(set(selected)) != len(selected) or any(x not in valid_names for x in selected):
            flash("Choose at least 3 different images for your graphical password.")
            conn.close()
            return redirect(url_for("reset_password", token=token))

        conn.execute(
            "UPDATE users SET password_hash = ?, graphical_password_hash = ? WHERE id = ?",
            (generate_password_hash(password), generate_password_hash(",".join(selected)), reset["user_id"]),
        )
        conn.execute("DELETE FROM password_reset_tokens WHERE user_id = ?", (reset["user_id"],))
        conn.commit()
        conn.close()
        flash("Both passwords have been reset. Please log in.")
        return redirect(url_for("login"))

    conn.close()
    return render_template("reset_password.html", images=IMAGE_CHOICES, username=reset["username"])


@app.route("/dashboard")
def dashboard():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    return render_template("dashboard.html", username=session.get("username"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


init_db()

if __name__ == "__main__":
    app.run(debug=True)
