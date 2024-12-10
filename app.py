from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# Sample items list
items = [
    {"id": 1, "name": "Tomato", "price": 2.5},
    {"id": 2, "name": "Potato", "price": 1.2},
    {"id": 3, "name": "Carrot", "price": 3.0}
]

users = {"admin": "password123"}  # Simple username-password pair for login

current_user = None

@app.route("/")
def home():
    if current_user:
        return render_template("items.html", items=items)
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    global current_user
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if users.get(username) == password:
            current_user = username
            return redirect(url_for("home"))
        else:
            return "Invalid credentials. Try again."
    return render_template("login.html")

@app.route("/logout")
def logout():
    global current_user
    current_user = None
    return redirect(url_for("home"))

@app.route("/order/<int:item_id>")
def order(item_id):
    if not current_user:
        return redirect(url_for("login"))
    item = next((item for item in items if item["id"] == item_id), None)
    if item:
        return f"Order placed for {item['name']}!"
    return "Item not found."

if __name__ == "__main__":
    app.run(debug=True)
