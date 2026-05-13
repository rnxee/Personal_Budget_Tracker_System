from flask import Blueprint, flash, redirect, render_template, request, url_for

from ..auth_helpers import current_user_id, login_required
from ..db import execute, fetch_all, fetch_one
from ..validation import iso_date, optional_text, positive_decimal, required_text


bp = Blueprint("goals", __name__, url_prefix="/goals")

GOAL_STATUSES = {"active", "paused", "completed"}


def get_goal(goal_id, user_id):
    return fetch_one(
        """
        SELECT goal_id, goal_name, target_amount, current_amount,
               target_date, status, notes
        FROM savings_goals
        WHERE goal_id = %s AND user_id = %s
        """,
        (goal_id, user_id),
    )


def validate_goal_form(form):
    goal_name, error = required_text(form.get("goal_name"), "Goal name", 100)
    if error:
        return None, error

    target_amount, error = positive_decimal(form.get("target_amount"), "Target amount")
    if error:
        return None, error

    current_amount, error = positive_decimal(
        form.get("current_amount", "0"), "Current amount", allow_zero=True
    )
    if error:
        return None, error

    target_date, error = iso_date(form.get("target_date"), "Target date")
    if error:
        return None, error

    status = form.get("status", "active")
    if status not in GOAL_STATUSES:
        return None, "Goal status is invalid."

    if current_amount >= target_amount:
        status = "completed"
    elif status == "completed":
        return None, "A goal can only be completed when current amount reaches the target."

    notes, error = optional_text(form.get("notes"), 255)
    if error:
        return None, error

    return {
        "goal_name": goal_name,
        "target_amount": target_amount,
        "current_amount": current_amount,
        "target_date": target_date,
        "status": status,
        "notes": notes,
    }, None


@bp.route("/")
@login_required
def index():
    user_id = current_user_id()
    goals = fetch_all(
        """
        SELECT goal_id, goal_name, target_amount, current_amount,
               target_date, status, notes,
               ROUND((current_amount / target_amount) * 100, 1) AS percent_saved
        FROM savings_goals
        WHERE user_id = %s
        ORDER BY status = 'completed', target_date ASC
        """,
        (user_id,),
    )
    return render_template("goals/index.html", goals=goals)


@bp.route("/new", methods=("GET", "POST"))
@login_required
def new():
    user_id = current_user_id()
    if request.method == "POST":
        data, error = validate_goal_form(request.form)
        if error:
            flash(error, "danger")
        else:
            execute(
                """
                INSERT INTO savings_goals
                  (user_id, goal_name, target_amount, current_amount,
                   target_date, status, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    user_id,
                    data["goal_name"],
                    data["target_amount"],
                    data["current_amount"],
                    data["target_date"],
                    data["status"],
                    data["notes"],
                ),
            )
            flash("Savings goal added successfully.", "success")
            return redirect(url_for("goals.index"))

    return render_template("goals/form.html", goal=None, statuses=sorted(GOAL_STATUSES))


@bp.route("/<int:goal_id>/edit", methods=("GET", "POST"))
@login_required
def edit(goal_id):
    user_id = current_user_id()
    goal = get_goal(goal_id, user_id)
    if goal is None:
        flash("Savings goal not found.", "warning")
        return redirect(url_for("goals.index"))

    if request.method == "POST":
        data, error = validate_goal_form(request.form)
        if error:
            flash(error, "danger")
        else:
            execute(
                """
                UPDATE savings_goals
                SET goal_name = %s,
                    target_amount = %s,
                    current_amount = %s,
                    target_date = %s,
                    status = %s,
                    notes = %s
                WHERE goal_id = %s AND user_id = %s
                """,
                (
                    data["goal_name"],
                    data["target_amount"],
                    data["current_amount"],
                    data["target_date"],
                    data["status"],
                    data["notes"],
                    goal_id,
                    user_id,
                ),
            )
            flash("Savings goal updated successfully.", "success")
            return redirect(url_for("goals.index"))

    return render_template("goals/form.html", goal=goal, statuses=sorted(GOAL_STATUSES))


@bp.route("/<int:goal_id>/delete", methods=("POST",))
@login_required
def delete(goal_id):
    user_id = current_user_id()
    goal = get_goal(goal_id, user_id)
    if goal is None:
        flash("Savings goal not found.", "warning")
        return redirect(url_for("goals.index"))

    execute(
        "DELETE FROM savings_goals WHERE goal_id = %s AND user_id = %s",
        (goal_id, user_id),
    )
    flash("Savings goal deleted successfully.", "info")
    return redirect(url_for("goals.index"))