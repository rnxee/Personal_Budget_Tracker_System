from datetime import date

from flask import Blueprint, render_template

from ..auth_helpers import current_user_id, login_required
from ..db import fetch_all, fetch_one


bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


@bp.route("/")
@login_required
def index():
    user_id = current_user_id()
    month_start = date.today().replace(day=1).isoformat()

    totals = fetch_one(
        """
        SELECT
          COALESCE(SUM(CASE WHEN transaction_type = 'income' THEN amount ELSE 0 END), 0) AS income_total,
          COALESCE(SUM(CASE WHEN transaction_type = 'expense' THEN amount ELSE 0 END), 0) AS expense_total
        FROM transactions
        WHERE user_id = %s
        """,
        (user_id,),
    )

    monthly = fetch_one(
        """
        SELECT
          COALESCE(SUM(CASE WHEN transaction_type = 'income' THEN amount ELSE 0 END), 0) AS month_income,
          COALESCE(SUM(CASE WHEN transaction_type = 'expense' THEN amount ELSE 0 END), 0) AS month_expense
        FROM transactions
        WHERE user_id = %s
          AND transaction_date >= %s
          AND transaction_date < DATE_ADD(%s, INTERVAL 1 MONTH)
        """,
        (user_id, month_start, month_start),
    )

    recent_transactions = fetch_all(
        """
        SELECT t.transaction_id, t.transaction_type, t.amount, t.transaction_date,
               t.description, t.payment_method, c.name AS category_name
        FROM transactions t
        JOIN categories c ON c.category_id = t.category_id
        WHERE t.user_id = %s
        ORDER BY t.transaction_date DESC, t.transaction_id DESC
        LIMIT 8
        """,
        (user_id,),
    )

    budget_usage = fetch_all(
        """
        SELECT b.budget_id, c.name AS category_name, b.limit_amount,
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
        WHERE b.user_id = %s
          AND b.month = %s
        GROUP BY b.budget_id, c.name, b.limit_amount
        ORDER BY percent_used DESC
        LIMIT 6
        """,
        (user_id, month_start),
    )

    savings_goals = fetch_all(
        """
        SELECT goal_id, goal_name, target_amount, current_amount, target_date, status,
               ROUND((current_amount / target_amount) * 100, 1) AS percent_saved
        FROM savings_goals
        WHERE user_id = %s
        ORDER BY status = 'completed', target_date ASC
        LIMIT 5
        """,
        (user_id,),
    )

    income_total = totals["income_total"]
    expense_total = totals["expense_total"]
    balance = income_total - expense_total

    return render_template(
        "dashboard.html",
        totals=totals,
        monthly=monthly,
        balance=balance,
        recent_transactions=recent_transactions,
        budget_usage=budget_usage,
        savings_goals=savings_goals,
    )