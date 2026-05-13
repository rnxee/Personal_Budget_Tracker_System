from flask import current_app, g
import mysql.connector


def get_db():
    if "db_connection" not in g:
        g.db_connection = mysql.connector.connect(
            host=current_app.config["MYSQL_HOST"],
            port=current_app.config["MYSQL_PORT"],
            database=current_app.config["MYSQL_DATABASE"],
            user=current_app.config["MYSQL_USER"],
            password=current_app.config["MYSQL_PASSWORD"],
        )
    return g.db_connection


def close_db(error=None):
    connection = g.pop("db_connection", None)
    if connection is not None and connection.is_connected():
        connection.close()


def init_app(app):
    app.teardown_appcontext(close_db)


def fetch_one(query, params=None):
    connection = get_db()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(query, params or ())
        return cursor.fetchone()
    finally:
        cursor.close()


def fetch_all(query, params=None):
    connection = get_db()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(query, params or ())
        return cursor.fetchall()
    finally:
        cursor.close()


def execute(query, params=None):
    connection = get_db()
    cursor = connection.cursor()
    try:
        cursor.execute(query, params or ())
        connection.commit()
        return cursor.lastrowid
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()