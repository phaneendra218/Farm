import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "2f61d8dd0a2c18bd0ccec4f4727e6012")  # Replace with a strong secret key

# Database connection settings from Render environment variables
DB_URL = os.environ.get("DATABASE_URL")  # This should be set in Render

def get_db_connection():
    return psycopg2.connect(DB_URL, sslmode='require', cursor_factory=RealDictCursor)

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        hashed_password = generate_password_hash(password)

        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO users (username, password) VALUES (%s, %s)",
                        (username, hashed_password)
                    )
                    conn.commit()
            flash("Registration successful! Please login.", "success")
            return redirect(url_for("login"))
        except psycopg2.IntegrityError:
            flash("Username already exists. Try a different one.", "error")
        except Exception as e:
            flash(f"An error occurred: {e}", "error")

    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM users WHERE username = %s", (username,))
                    user = cur.fetchone()
                    
                    if user and check_password_hash(user["password"], password):
                        session["user_id"] = user["id"]
                        session["username"] = user["username"]
                        flash("Login successful!", "success")
                        return redirect(url_for("home"))
                    else:
                        flash("Invalid username or password.", "error")
        except Exception as e:
            flash(f"An error occurred: {e}", "error")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))

@app.route("/")
def home():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("items.html", items=[])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
