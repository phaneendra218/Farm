from flask import Flask, render_template, request, redirect, session, url_for, flash
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://farmpsql_user:ilFpRrHEzsedKGwtrOtweM0ToOV6YmIW@dpg-ctc8ap5ds78s73flqmpg-a.oregon-postgres.render.com/farmpsql'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)  # Admin flag

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    price = db.Column(db.Float, nullable=False)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

# Routes
@app.route('/')
def home():
    items = Item.query.all()  # Fetch all items
    return render_template('home.html', items=items)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
        else:
            user = User(username=username, password=password)
            db.session.add(user)
            db.session.commit()
            flash('Signup successful!', 'success')
            return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session['user_id'] = user.id
            session['username'] = user.username  # Store username in session
            session['is_admin'] = user.is_admin  # Store admin status in session
            return redirect(url_for('items'))
        else:
            flash('Invalid credentials', 'danger')
    return render_template('login.html')

@app.route('/items', methods=['GET', 'POST'])
def items():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    items = Item.query.all()
    return render_template('items.html', items=items, is_admin=session.get('is_admin', False))

@app.route('/delete_item/<int:item_id>', methods=['POST'])
def delete_item(item_id):
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Unauthorized access', 'danger')
        return redirect(url_for('items'))  # Redirect to items page instead of login
    item = Item.query.get_or_404(item_id)
    try:
        db.session.delete(item)
        db.session.commit()
        flash('Item deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting item: {str(e)}', 'danger')
    return redirect(url_for('items'))

@app.route('/add_item', methods=['GET', 'POST'])
def add_item():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Unauthorized access', 'danger')
        return redirect(url_for('items'))  # Redirect to items page instead of login
    if request.method == 'POST':
        name = request.form['name']
        price = request.form['price']
        new_item = Item(name=name, price=float(price))
        db.session.add(new_item)
        db.session.commit()
        flash('Item added successfully!', 'success')
        return redirect(url_for('items'))
    return render_template('add_item.html')

@app.route('/order_now/<int:item_id>', methods=['POST'])
def order_now(item_id):
    if 'user_id' not in session:
        flash('Please log in to place an order.', 'warning')
        return redirect(url_for('login'))

    # Retrieve the item being ordered
    item = Item.query.get_or_404(item_id)
    
    # Get the quantity from the form
    quantity = request.form.get('quantity')
    
    # Validate that the quantity is provided and is a positive integer
    try:
        quantity = int(quantity)
        if quantity < 1:
            raise ValueError("Quantity must be greater than 0.")
    except (ValueError, TypeError):
        flash("Invalid quantity. Please enter a valid number greater than 0.", 'danger')
        return redirect(url_for('items'))  # Redirect back to items page in case of invalid input

    # Create a new order entry in the database
    order = Order(user_id=session['user_id'], item_id=item.id, quantity=quantity)
    db.session.add(order)
    db.session.commit()

    # Notify the user of successful order placement
    flash(f'Order for {item.name} (Quantity: {quantity}) placed successfully!', 'success')
    return redirect(url_for('home'))

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Ensures tables are created before starting the app

        # Ensure an admin user exists (for simplicity, hardcoding admin credentials here)
        if not User.query.filter_by(username='admin').first():
            admin_user = User(username='admin', password='admin', is_admin=True)
            db.session.add(admin_user)
            db.session.commit()

    app.run(host='0.0.0.0', port=5000)
