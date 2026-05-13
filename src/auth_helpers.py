from functools import wraps

from flask import flash, g, redirect, session, url_for

from .db import fetch_one


def load_logged_in_user():
    user_id = session.get("user_id")
    if user_id is None:
        g.user = None
        return

    g.user = fetch_one(
        """
        SELECT user_id, username, full_name, email, role
        FROM users
        WHERE user_id = %s AND is_active = 1
        """,
        (user_id,),
    )
    if g.user is None:
        session.clear()


def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if g.get("user") is None:
            flash("Please log in to access that page.", "warning")
            return redirect(url_for("auth.login"))
        return view(**kwargs)

    return wrapped_view


def current_user_id():
    return g.user["user_id"]
