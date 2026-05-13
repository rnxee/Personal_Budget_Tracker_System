from flask import Blueprint, flash, redirect, render_template, request, url_for
from mysql.connector import IntegrityError

from ..auth_helpers import current_user_id, login_required
from ..db import execute, fetch_all, fetch_one
from ..validation import optional_text, required_text


bp = Blueprint("categories", __name__, url_prefix="/categories")


def get_user_category(category_id, user_id):
    return fetch_one(
        """
        SELECT category_id, name, type, description
        FROM categories
        WHERE category_id = %s AND user_id = %s
        """,
        (category_id, user_id),
    )


def validate_category_form(form):
    name, error = required_text(form.get("name"), "Category name", 80)
    if error:
        return None, error

    category_type = form.get("type")
    if category_type not in {"income", "expense"}:
        return None, "Category type must be income or expense."

    description, error = optional_text(form.get("description"), 255)
    if error:
        return None, error

    return {
        "name": name,
        "type": category_type,
        "description": description,
    }, None


@bp.route("/", methods=("GET", "POST"))
@login_required
def index():
    user_id = current_user_id()

    if request.method == "POST":
        data, error = validate_category_form(request.form)
        if error:
            flash(error, "danger")
        else:
            try:
                execute(
                    """
                    INSERT INTO categories (user_id, name, type, description)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (user_id, data["name"], data["type"], data["description"]),
                )
                flash("Category added successfully.", "success")
                return redirect(url_for("categories.index"))
            except IntegrityError:
                flash("A category with the same name and type already exists.", "danger")

    categories = fetch_all(
        """
        SELECT c.category_id, c.name, c.type, c.description,
               COUNT(t.transaction_id) AS transaction_count
        FROM categories c
        LEFT JOIN transactions t ON t.category_id = c.category_id
        WHERE c.user_id = %s
        GROUP BY c.category_id, c.name, c.type, c.description
        ORDER BY c.type, c.name
        """,
        (user_id,),
    )
    return render_template("categories/index.html", categories=categories)


@bp.route("/<int:category_id>/edit", methods=("GET", "POST"))
@login_required
def edit(category_id):
    user_id = current_user_id()
    category = get_user_category(category_id, user_id)
    if category is None:
        flash("Category not found.", "warning")
        return redirect(url_for("categories.index"))

    if request.method == "POST":
        data, error = validate_category_form(request.form)
        if error:
            flash(error, "danger")
        else:
            try:
                execute(
                    """
                    UPDATE categories
                    SET name = %s, type = %s, description = %s
                    WHERE category_id = %s AND user_id = %s
                    """,
                    (
                        data["name"],
                        data["type"],
                        data["description"],
                        category_id,
                        user_id,
                    ),
                )
                flash("Category updated successfully.", "success")
                return redirect(url_for("categories.index"))
            except IntegrityError:
                flash("A category with the same name and type already exists.", "danger")

    return render_template("categories/form.html", category=category)


@bp.route("/<int:category_id>/delete", methods=("POST",))
@login_required
def delete(category_id):
    user_id = current_user_id()
    category = get_user_category(category_id, user_id)
    if category is None:
        flash("Category not found.", "warning")
        return redirect(url_for("categories.index"))

    usage = fetch_one(
        """
        SELECT
          (SELECT COUNT(*) FROM transactions WHERE category_id = %s) AS transaction_count,
          (SELECT COUNT(*) FROM budgets WHERE category_id = %s) AS budget_count
        """,
        (category_id, category_id),
    )
    if usage["transaction_count"] or usage["budget_count"]:
        flash("This category is already used and cannot be deleted.", "danger")
        return redirect(url_for("categories.index"))

    execute(
        "DELETE FROM categories WHERE category_id = %s AND user_id = %s",
        (category_id, user_id),
    )
    flash("Category deleted successfully.", "info")
    return redirect(url_for("categories.index"))