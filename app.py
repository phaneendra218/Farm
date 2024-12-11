from flask import Flask, render_template, request, redirect, session, url_for, flash
from flask_sqlalchemy import SQLAlchemy
import os
import random
import string
from models import db, User  # Import db and User model from models.py

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://farmpsql_user:ilFpRrHEzsedKGwtrOtweM0ToOV6YmIW@dpg-ctc8ap5ds78s73flqmpg-a.oregon-postgres.render.com/farmpsql'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Function to create a random password
def generate_random_password():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=12))

# Create a default admin user if it doesn't exist
def create_default_admin():
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(username='admin', password=generate_random_password(), reset_required=True)
        db.session.add(admin)
        db.session.commit()

@app.before_first_request
def before_first_request():
    db.create_all()  # Create database tables
    create_default_admin()  # Ensure the default admin user is created

# Models (adjusted)
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)  # Track if the user is an admin
    reset_required = db.Column(db.Boolean, default=False)  # New field to indicate if password needs reset

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
    return render_template('base.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
        else:
            is_admin = User.query.count() == 0  # First user will be admin
            user = User(username=username, password=password, is_admin=is_admin)
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
            if user.reset_required:
                flash('Please reset your password on first login.', 'info')
                return redirect(url_for('reset_password', user_id=user.id))  # Redirect to reset page
            return redirect(url_for('items'))
        else:
            flash('Invalid credentials', 'danger')
    return render_template('login.html')

@app.route('/reset_password/<int:user_id>', methods=['GET', 'POST'])
def reset_password(user_id):
    user = User.query.get_or_404(user_id)
    if request.method == 'POST':
        new_password = request.form['new_password']
        user.password = new_password
        user.reset_required = False  # Set reset_required to False after password reset
        db.session.commit()
        flash('Password has been reset successfully.', 'success')
        return redirect(url_for('login'))  # Redirect to login page after password reset
    return render_template('reset_password.html', user=user)

@app.route('/items', methods=['GET', 'POST'])
def items():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    items = Item.query.all()
    if request.method == 'POST':
        item_id = request.form['item_id']
        quantity = int(request.form['quantity'])
        order = Order(user_id=session['user_id'], item_id=item_id, quantity=quantity)
        db.session.add(order)
        db.session.commit()
        flash('Order placed successfully!', 'success')
    return render_template('items.html', items=items)

@app.route('/add_item', methods=['GET', 'POST'])
def add_item():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # Check if the user is an admin
    user = User.query.get(session['user_id'])
    if not user.is_admin:
        flash('You are not authorized to access this page.', 'danger')
        return redirect(url_for('items'))  # Redirect to items page if not admin

    if request.method == 'POST':
        name = request.form['name']
        price = request.form['price']
        
        # Create a new Item object
        new_item = Item(name=name, price=float(price))
        
        # Add the new item to the session and commit to the database
        db.session.add(new_item)
        db.session.commit()
        
        flash('Item added successfully!', 'success')
        return redirect(url_for('items'))  # Redirect to the items page after adding

    return render_template('add_item.html')  # Display the form when GET request

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
    app.run(host='0.0.0.0', port=5000)
