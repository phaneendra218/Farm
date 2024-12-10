from flask import Flask, render_template
from items import items  # Importing items from the items module

app = Flask(__name__)

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
