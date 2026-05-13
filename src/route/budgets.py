from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, url_for
from mysql.connector import IntegrityError

from ..auth_helpers import current_user_id, login_required
from ..db import execute, fetch_all, fetch_one
from ..validation import month_start, optional_text, positive_decimal


bp = Blueprint("budgets", __name__, url_prefix="/budgets")


def expense_categories(user_id):
    return fetch_all(
        """
        SELECT category_id, name
        FROM categories
        WHERE user_id = %s AND type = 'expense'
        ORDER BY name
        """,
        (user_id,),
    )


def get_budget(budget_id, user_id):
    return fetch_one(
        """
        SELECT budget_id, category_id, month, limit_amount, notes
        FROM budgets
        WHERE budget_id = %s AND user_id = %s
        """,
        (budget_id, user_id),
    )


def validate_budget_form(form, user_id):
    try:
        category_id = int(form.get("category_id", ""))
    except ValueError:
        return None, "Expense category is required."

    category = fetch_one(
        """
        SELECT category_id
        FROM categories
        WHERE category_id = %s AND user_id = %s AND type = 'expense'
        """,
        (category_id, user_id),
    )
    if category is None:
        return None, "Selected category must be an expense category."

    month, error = month_start(form.get("month"))
    if error:
        return None, error

    limit_amount, error = positive_decimal(form.get("limit_amount"), "Budget limit")
    if error:
        return None, error

    notes, error = optional_text(form.get("notes"), 255)
    if error:
        return None, error

    return {
        "category_id": category_id,
        "month": month,
        "limit_amount": limit_amount,
        "notes": notes,
    }, None


@bp.route("/")
@login_required
def index():
    user_id = current_user_id()
    selected_month = request.args.get("month") or date.today().strftime("%Y-%m")
    month_value, error = month_start(selected_month)
    if error:
        month_value = date.today().replace(day=1).isoformat()
        selected_month = date.today().strftime("%Y-%m")

    budgets = fetch_all(
        """
        SELECT b.budget_id, b.month, b.limit_amount, b.notes,
               c.name AS category_name,
               COALESCE(SUM(t.amount), 0) AS spent_amount,
               ROUND((COALESCE(SUM(t.amount), 0) / b.limit_amount) * 100, 1) AS percent_used
        FROM budgets b
        JOIN categories c ON c.category_id = b.category_id
        LEFT JOIN transactions t
          ON t.user_id = b.user_id
         AND t.category_id = b.category_id
         AND t.transaction_type = 'expense'
         AND t.transaction_date >= b.month
         AND t.transaction_date < DATE_ADD(b.month, INTERVAL 1 MONTH)
        WHERE b.user_id = %s AND b.month = %s
        GROUP BY b.budget_id, b.month, b.limit_amount, b.notes, c.name
        ORDER BY c.name
        """,
        (user_id, month_value),
    )
    return render_template("budgets/index.html", budgets=budgets, selected_month=selected_month)


@bp.route("/new", methods=("GET", "POST"))
@login_required
def new():
    user_id = current_user_id()
    categories = expense_categories(user_id)
    if request.method == "POST":
        data, error = validate_budget_form(request.form, user_id)
        if error:
            flash(error, "danger")
        else:
            try:
                execute(
                    """
                    INSERT INTO budgets (user_id, category_id, month, limit_amount, notes)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (user_id, data["category_id"], data["month"], data["limit_amount"], data["notes"]),
                )
                flash("Budget added successfully.", "success")
                return redirect(url_for("budgets.index", month=data["month"][:7]))
            except IntegrityError:
                flash("A budget already exists for that category and month.", "danger")

    return render_template("budgets/form.html", budget=None, categories=categories)


@bp.route("/<int:budget_id>/edit", methods=("GET", "POST"))
@login_required
def edit(budget_id):
    user_id = current_user_id()
    budget = get_budget(budget_id, user_id)
    if budget is None:
        flash("Budget not found.", "warning")
        return redirect(url_for("budgets.index"))

    categories = expense_categories(user_id)
    if request.method == "POST":
        data, error = validate_budget_form(request.form, user_id)
        if error:
            flash(error, "danger")
        else:
            try:
                execute(
                    """
                    UPDATE budgets
                    SET category_id = %s, month = %s, limit_amount = %s, notes = %s
                    WHERE budget_id = %s AND user_id = %s
                    """,
                    (
                        data["category_id"],
                        data["month"],
                        data["limit_amount"],
                        data["notes"],
                        budget_id,
                        user_id,
                    ),
                )
                flash("Budget updated successfully.", "success")
                return redirect(url_for("budgets.index", month=data["month"][:7]))
            except IntegrityError:
                flash("A budget already exists for that category and month.", "danger")

    return render_template("budgets/form.html", budget=budget, categories=categories)


@bp.route("/<int:budget_id>/delete", methods=("POST",))
@login_required
def delete(budget_id):
    user_id = current_user_id()
    budget = get_budget(budget_id, user_id)
    if budget is None:
        flash("Budget not found.", "warning")
        return redirect(url_for("budgets.index"))

    execute("DELETE FROM budgets WHERE budget_id = %s AND user_id = %s", (budget_id, user_id))
    flash("Budget deleted successfully.", "info")
    return redirect(url_for("budgets.index"))