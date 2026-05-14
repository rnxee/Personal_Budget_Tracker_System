import re

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from mysql.connector import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from ..db import execute, fetch_one
from ..validation import required_text


bp = Blueprint("auth", __name__, url_prefix="/auth")

DEFAULT_CATEGORIES = [
    ("Salary", "income", "Monthly salary or allowance"),
    ("Freelance", "income", "Part-time and project income"),
    ("Business", "income", "Small business income"),
    ("Gift", "income", "Gifts and other support"),
    ("Food", "expense", "Meals, groceries, and snacks"),
    ("Transportation", "expense", "Fare, fuel, and commute expenses"),
    ("School", "expense", "School supplies and academic expenses"),
    ("Utilities", "expense", "Electricity, internet, and phone bills"),
    ("Health", "expense", "Medicine, checkups, and wellness"),
    ("Entertainment", "expense", "Streaming, games, and leisure"),
]


def validate_registration_form(form):
    full_name, error = required_text(form.get("full_name"), "Full name", 100)
    if error:
        return None, error

    username, error = required_text(form.get("username"), "Username", 50)
    if error:
        return None, error
    username = username.lower()
    if not re.fullmatch(r"[a-z0-9_]{3,50}", username):
        return None, "Username must be 3-50 characters and use only letters, numbers, or underscores."

    email, error = required_text(form.get("email"), "Email", 120)
    if error:
        return None, error
    email = email.lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        return None, "Email address is invalid."

    password = form.get("password", "")
    confirm_password = form.get("confirm_password", "")
    if len(password) < 8:
        return None, "Password must be at least 8 characters."
    if password != confirm_password:
        return None, "Passwords do not match."

    return {
        "full_name": full_name,
        "username": username,
        "email": email,
        "password": password,
    }, None


def create_default_categories(user_id):
    for name, category_type, description in DEFAULT_CATEGORIES:
        execute(
            """
            INSERT INTO categories (user_id, name, type, description)
            VALUES (%s, %s, %s, %s)
            """,
            (user_id, name, category_type, description),
        )


@bp.route("/login", methods=("GET", "POST"))
def login():
    if session.get("user_id"):
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = fetch_one(
            """
            SELECT user_id, username, full_name, email, role, password_hash
            FROM users
            WHERE username = %s AND is_active = 1
            """,
            (username,),
        )

        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Invalid username or password.", "danger")
        else:
            session.clear()
            session["user_id"] = user["user_id"]
            session["username"] = user["username"]
            session["full_name"] = user["full_name"]
            session["role"] = user["role"]
            flash(f"Welcome back, {user['full_name']}.", "success")
            return redirect(url_for("dashboard.index"))

    return render_template("auth/login.html")


@bp.route("/register", methods=("GET", "POST"))
def register():
    if session.get("user_id"):
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        data, error = validate_registration_form(request.form)
        if error:
            flash(error, "danger")
        else:
            try:
                user_id = execute(
                    """
                    INSERT INTO users
                      (username, full_name, email, password_hash, role, is_active)
                    VALUES (%s, %s, %s, %s, 'member', 1)
                    """,
                    (
                        data["username"],
                        data["full_name"],
                        data["email"],
                        generate_password_hash(data["password"]),
                    ),
                )
                create_default_categories(user_id)
                session.clear()
                session["user_id"] = user_id
                session["username"] = data["username"]
                session["full_name"] = data["full_name"]
                session["role"] = "member"
                flash("Account created successfully.", "success")
                return redirect(url_for("dashboard.index"))
            except IntegrityError:
                flash("Username or email is already registered.", "danger")

    return render_template("auth/register.html")


@bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
