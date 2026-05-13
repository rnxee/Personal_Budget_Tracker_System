from decimal import Decimal

from flask import Flask, redirect, render_template, session, url_for
from mysql.connector import Error as MySQLError

from . import db
from .auth_helpers import load_logged_in_user
from .config import Config
from .routes import auth, budgets, categories, dashboard, goals, transactions


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    app.before_request(load_logged_in_user)

    app.register_blueprint(auth.bp)
    app.register_blueprint(dashboard.bp)
    app.register_blueprint(categories.bp)
    app.register_blueprint(transactions.bp)
    app.register_blueprint(budgets.bp)
    app.register_blueprint(goals.bp)

    @app.template_filter("peso")
    def peso(value):
        value = Decimal(value or 0)
        return f"PHP {value:,.2f}"

    @app.route("/")
    def index():
        if session.get("user_id"):
            return redirect(url_for("dashboard.index"))
        return redirect(url_for("auth.login"))

    @app.errorhandler(MySQLError)
    def handle_mysql_error(error):
        return render_template("error.html", error=error), 500

    return app


if __name__ == "__main__":
    create_app().run(debug=True)