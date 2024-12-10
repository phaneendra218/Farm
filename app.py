from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# Sample items list
items = [
    {"id": 1, "name": "Tomato", "price": 2.5},
    {"id": 2, "name": "Potato", "price": 1.2},
    {"id": 3, "name": "Carrot", "price": 3.0}
]

@app.route("/")
def home():
    return render_template("items.html", items=items)

@app.route("/order/<int:item_id>")
def order(item_id):
    item = next((item for item in items if item["id"] == item_id), None)
    if item:
        return f"Order placed for {item['name']}!"
    return "Item not found."

if __name__ == "__main__":
    app.run(debug=True)
