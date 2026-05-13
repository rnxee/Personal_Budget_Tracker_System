import csv
import io

from flask import Blueprint, Response, flash, redirect, render_template, request, url_for

from ..auth_helpers import current_user_id, login_required
from ..db import execute, fetch_all, fetch_one
from ..validation import iso_date, positive_decimal, required_text


bp = Blueprint("transactions", __name__, url_prefix="/transactions")

PAYMENT_METHODS = ["cash", "gcash", "card", "bank_transfer", "other"]
TRANSACTION_TYPES = {"income", "expense"}


def get_transaction(transaction_id, user_id):
    return fetch_one(
        """
        SELECT transaction_id, user_id, category_id, transaction_type, amount,
               transaction_date, description, payment_method
        FROM transactions
        WHERE transaction_id = %s AND user_id = %s
        """,
        (transaction_id, user_id),
    )


def categories_for_user(user_id):
    return fetch_all(
        """
        SELECT category_id, name, type
        FROM categories
        WHERE user_id = %s
        ORDER BY type, name
        """,
        (user_id,),
    )


def validate_transaction_form(form, user_id):
    transaction_type = form.get("transaction_type")
    if transaction_type not in TRANSACTION_TYPES:
        return None, "Transaction type must be income or expense."

    amount, error = positive_decimal(form.get("amount"), "Amount")
    if error:
        return None, error

    transaction_date, error = iso_date(form.get("transaction_date"), "Transaction date")
    if error:
        return None, error

    description, error = required_text(form.get("description"), "Description", 255)
    if error:
        return None, error

    payment_method = form.get("payment_method")
    if payment_method not in PAYMENT_METHODS:
        return None, "Payment method is invalid."

    try:
        category_id = int(form.get("category_id", ""))
    except ValueError:
        return None, "Category is required."

    category = fetch_one(
        """
        SELECT category_id
        FROM categories
        WHERE category_id = %s AND user_id = %s AND type = %s
        """,
        (category_id, user_id, transaction_type),
    )
    if category is None:
        return None, "Selected category does not match the transaction type."

    return {
        "category_id": category_id,
        "transaction_type": transaction_type,
        "amount": amount,
        "transaction_date": transaction_date,
        "description": description,
        "payment_method": payment_method,
    }, None


def build_filter_query(user_id, args):
    query = [
        """
        SELECT t.transaction_id, t.transaction_type, t.amount, t.transaction_date,
               t.description, t.payment_method, c.name AS category_name
        FROM transactions t
        JOIN categories c ON c.category_id = t.category_id
        WHERE t.user_id = %s
        """
    ]
    params = [user_id]

    keyword = args.get("q", "").strip()
    if keyword:
        query.append("AND (t.description LIKE %s OR c.name LIKE %s OR t.payment_method LIKE %s)")
        like_keyword = f"%{keyword}%"
        params.extend([like_keyword, like_keyword, like_keyword])

    transaction_type = args.get("type", "")
    if transaction_type in TRANSACTION_TYPES:
        query.append("AND t.transaction_type = %s")
        params.append(transaction_type)

    category_id = args.get("category_id", "")
    if category_id.isdigit():
        query.append("AND t.category_id = %s")
        params.append(int(category_id))

    start_date = args.get("start_date", "")
    if start_date:
        query.append("AND t.transaction_date >= %s")
        params.append(start_date)

    end_date = args.get("end_date", "")
    if end_date:
        query.append("AND t.transaction_date <= %s")
        params.append(end_date)

    query.append("ORDER BY t.transaction_date DESC, t.transaction_id DESC")
    return "\n".join(query), params


@bp.route("/")
@login_required
def index():
    user_id = current_user_id()
    query, params = build_filter_query(user_id, request.args)
    transactions = fetch_all(query, params)
    categories = categories_for_user(user_id)
    return render_template(
        "transactions/index.html",
        transactions=transactions,
        categories=categories,
        filters=request.args,
    )


@bp.route("/new", methods=("GET", "POST"))
@login_required
def new():
    user_id = current_user_id()
    categories = categories_for_user(user_id)

    if request.method == "POST":
        data, error = validate_transaction_form(request.form, user_id)
        if error:
            flash(error, "danger")
        else:
            execute(
                """
                INSERT INTO transactions
                  (user_id, category_id, transaction_type, amount, transaction_date,
                   description, payment_method)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    user_id,
                    data["category_id"],
                    data["transaction_type"],
                    data["amount"],
                    data["transaction_date"],
                    data["description"],
                    data["payment_method"],
                ),
            )
            flash("Transaction added successfully.", "success")
            return redirect(url_for("transactions.index"))

    return render_template(
        "transactions/form.html",
        transaction=None,
        categories=categories,
        payment_methods=PAYMENT_METHODS,
    )


@bp.route("/<int:transaction_id>/edit", methods=("GET", "POST"))
@login_required
def edit(transaction_id):
    user_id = current_user_id()
    transaction = get_transaction(transaction_id, user_id)
    if transaction is None:
        flash("Transaction not found.", "warning")
        return redirect(url_for("transactions.index"))

    categories = categories_for_user(user_id)
    if request.method == "POST":
        data, error = validate_transaction_form(request.form, user_id)
        if error:
            flash(error, "danger")
        else:
            execute(
                """
                UPDATE transactions
                SET category_id = %s,
                    transaction_type = %s,
                    amount = %s,
                    transaction_date = %s,
                    description = %s,
                    payment_method = %s
                WHERE transaction_id = %s AND user_id = %s
                """,
                (
                    data["category_id"],
                    data["transaction_type"],
                    data["amount"],
                    data["transaction_date"],
                    data["description"],
                    data["payment_method"],
                    transaction_id,
                    user_id,
                ),
            )
            flash("Transaction updated successfully.", "success")
            return redirect(url_for("transactions.index"))

    return render_template(
        "transactions/form.html",
        transaction=transaction,
        categories=categories,
        payment_methods=PAYMENT_METHODS,
    )


@bp.route("/<int:transaction_id>/delete", methods=("POST",))
@login_required
def delete(transaction_id):
    user_id = current_user_id()
    transaction = get_transaction(transaction_id, user_id)
    if transaction is None:
        flash("Transaction not found.", "warning")
        return redirect(url_for("transactions.index"))

    execute(
        "DELETE FROM transactions WHERE transaction_id = %s AND user_id = %s",
        (transaction_id, user_id),
    )
    flash("Transaction deleted successfully.", "info")
    return redirect(url_for("transactions.index"))


@bp.route("/export")
@login_required
def export():
    user_id = current_user_id()
    query, params = build_filter_query(user_id, request.args)
    transactions = fetch_all(query, params)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Type", "Category", "Description", "Payment Method", "Amount"])
    for row in transactions:
        writer.writerow(
            [
                row["transaction_date"],
                row["transaction_type"],
                row["category_name"],
                row["description"],
                row["payment_method"],
                row["amount"],
            ]
        )

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=transactions_export.csv"},
    )