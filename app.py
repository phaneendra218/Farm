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

class Basket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

    user = db.relationship('User', backref='baskets')
    item = db.relationship('Item', backref='baskets')

# Routes
@app.route('/')
def home():
    items = Item.query.all()  # Fetch all items from the database
    if 'user_id' in session:
        user_id = session['user_id']
        basket_count = db.session.query(Basket).filter_by(user_id=user_id).count()
        session['basket_count'] = basket_count
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

            # Update the basket count in the session
            basket_count = db.session.query(Basket).filter_by(user_id=user.id).count()
            session['basket_count'] = basket_count
            return redirect(url_for('items'))
        else:
            flash('Invalid credentials', 'danger')
    return render_template('login.html')

@app.route('/items', methods=['GET', 'POST'])
def items():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    items = Item.query.all()
    user_id = session['user_id']
    basket_count = db.session.query(Basket).filter_by(user_id=user_id).count()
    session['basket_count'] = basket_count
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

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/order_item/<int:item_id>', methods=['POST'])
def order_item(item_id):
    if 'user_id' not in session:
        flash('Please login to order items', 'danger')
        return redirect(url_for('login'))
    
    # Get the item and create an order (assuming quantity is 1 for simplicity)
    item = Item.query.get_or_404(item_id)
    order = Order(user_id=session['user_id'], item_id=item.id, quantity=1)
    db.session.add(order)
    db.session.commit()
    
    flash('Item ordered successfully!', 'success')
    return redirect(url_for('items'))  # Redirect to the items page

@app.route('/add_to_basket/<int:item_id>', methods=['POST'])
def add_to_basket(item_id):
    if 'user_id' not in session:
        flash('Please login to add items to your basket', 'danger')
        return redirect(url_for('login'))

    user_id = session['user_id']
    quantity = int(request.form.get('quantity', 1))

    # Check if the item already exists in the basket
    basket_item = Basket.query.filter_by(user_id=user_id, item_id=item_id).first()
    if basket_item:
        basket_item.quantity += quantity  # Update quantity if item already exists
    else:
        basket_item = Basket(user_id=user_id, item_id=item_id, quantity=quantity)
        db.session.add(basket_item)

    db.session.commit()

    # Update the basket count in session
    basket_count = db.session.query(Basket).filter_by(user_id=user_id).count()
    session['basket_count'] = basket_count

    flash('Item added to basket successfully!', 'success')
    return redirect(url_for('items'))

@app.route('/basket')
def basket():
    if 'user_id' not in session:
        flash('Please login to view your basket', 'danger')
        return redirect(url_for('login'))

    user_id = session['user_id']
    basket_items = db.session.query(Basket, Item).join(Item).filter(Basket.user_id == user_id).all()

    # Calculate the total price
    total_price = sum(item.price * basket_item.quantity for basket_item, item in basket_items)

    # Update the basket count
    basket_count = len(basket_items)
    session['basket_count'] = basket_count

    return render_template('basket.html', basket_items=basket_items, total_price=total_price)

@app.route('/remove_from_basket/<int:item_id>', methods=['POST'])
def remove_from_basket(item_id):
    if 'user_id' not in session:
        flash('Please login to remove items from your basket', 'danger')
        return redirect(url_for('login'))

    user_id = session['user_id']
    basket_item = Basket.query.filter_by(user_id=user_id, item_id=item_id).first()

    if basket_item:
        db.session.delete(basket_item)
        db.session.commit()

        # Update the basket count
        basket_count = db.session.query(Basket).filter_by(user_id=user_id).count()
        session['basket_count'] = basket_count

        flash('Item removed from basket', 'info')

    return redirect(url_for('basket'))

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    # Handle checkout logic here
    return render_template('checkout.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Ensures tables are created before starting the app

        # Ensure an admin user exists (for simplicity, hardcoding admin credentials here)
        if not User.query.filter_by(username='admin').first():
            admin_user = User(username='admin', password='admin', is_admin=True)
            db.session.add(admin_user)
            db.session.commit()

    app.run(host='0.0.0.0', port=5000)
