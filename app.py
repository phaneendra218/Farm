from flask import Flask, render_template, request, redirect, session, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
import os
from werkzeug.utils import secure_filename
from sqlalchemy import Integer, String, Boolean, Float
from sqlalchemy.orm import sessionmaker, Session, joinedload
from sqlalchemy.types import Numeric
from decimal import Decimal
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Database Configuration (External Database URL)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://farmpsql_user:ilFpRrHEzsedKGwtrOtweM0ToOV6YmIW@dpg-ctc8ap5ds78s73flqmpg-a.oregon-postgres.render.com/farmpsql'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Set the upload folder and allowed file extensions
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024  # 100 KB
# Ensure the upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

db = SQLAlchemy(app)

# Models
class Address(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)  # Ensure cascading delete
    address = db.Column(db.String(255), nullable=False)
    address_type = db.Column(db.String(50), nullable=False)  # Required field for address type
    is_default = db.Column(db.Boolean, default=False)
    user = db.relationship('User', back_populates='addresses')

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, server_default='false')  # Default for admin flag
    phone_number = db.Column(db.String(15), nullable=False)
    addresses = db.relationship('Address', back_populates='user', cascade='all, delete-orphan')

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    price = db.Column(db.Float, nullable=False)
    image_path = db.Column(db.String(255), nullable=True)
    unit = db.Column(db.String(50), nullable=False, default="Kg")  # New column
    is_hidden = db.Column(db.Boolean, default=False)  # New column to track visibility

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    quantity = db.Column(Numeric(10, 2), nullable=False)
    address_id = db.Column(db.Integer, db.ForeignKey('address.id'), nullable=True)
    total_price = db.Column(db.Numeric(10, 2), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    delivery_address = db.Column(db.String(255), nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)

    
class Basket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    quantity = db.Column(Numeric(10, 2), nullable=False)

    user = db.relationship('User', backref='baskets')
    item = db.relationship('Item', backref='baskets')
    item = db.relationship('Item', backref='orders')
    Order.item = db.relationship('Item', backref='order_items')
    

# Routes
@app.route('/')
def home():
    items = Item.query.all()  # Fetch all items from the database, including image_path for each item
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
        phone_number = request.form['phone_number']

        # Check if the username already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
        elif User.query.filter_by(phone_number=phone_number).first():
            flash('Phone number is already taken', 'danger')
        else:
            # Create a new user with the phone number
            user = User(username=username, password=password, phone_number=phone_number)
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

@app.route('/forget_password', methods=['GET', 'POST'])
def forget_password():
    if request.method == 'POST':
        username = request.form['username']
        phone_number = request.form['phone_number']
        user = User.query.filter_by(username=username, phone_number=phone_number).first()

        if user:
            session['reset_user_id'] = user.id
            flash('Validation successful. Please update your password.', 'success')
            return redirect(url_for('update_password'))
        else:
            flash('Username and phone number do not match. Please try again.', 'danger')

    return render_template('forget_password.html')

@app.route('/update_password', methods=['GET', 'POST'])
def update_password():
    if 'reset_user_id' not in session:
        flash('Unauthorized access. Please start the reset process again.', 'danger')
        return redirect(url_for('forget_password'))

    if request.method == 'POST':
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        if new_password != confirm_password:
            flash('Passwords do not match. Please try again.', 'danger')
        else:
            # Directly update the plaintext password
            user = User.query.get(session['reset_user_id'])
            user.password = new_password  # Plaintext storage
            db.session.commit()
            session.pop('reset_user_id')  # Remove reset_user_id from session
            flash('Password updated successfully. You can now login.', 'success')
            return redirect(url_for('login'))

    return render_template('update_password.html')

@app.route('/forget_user', methods=['GET', 'POST'])
def forget_user():
    username = None
    if request.method == 'POST':
        phone_number = request.form['phone_number']
        user = User.query.filter_by(phone_number=phone_number).first()

        if user:
            username = user.username  # Pass username to the template for the popup
        else:
            flash('Phone number not found. Please try again.', 'danger')

    return render_template('forget_user.html', username=username)

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/items', methods=['GET', 'POST'])
def items():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    items = Item.query.all()
    
    user_id = session['user_id']
    basket_count = db.session.query(Basket).filter_by(user_id=user_id).count()
    session['basket_count'] = basket_count

    return render_template('items.html', 
                           items=items, 
                           is_admin=session.get('is_admin', False))

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

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/add_item', methods=['GET', 'POST'])
def add_item():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Unauthorized access', 'danger')
        return redirect(url_for('items'))  # Redirect to items page instead of login
    
    if request.method == 'POST':
        # Get item details from the form
        name = request.form['name']
        price = request.form['price']
        unit = request.form['unit']
        
        # Handle the image file
        if 'image' not in request.files:
            flash('No image file selected', 'warning')
            return redirect(request.url)

        image = request.files['image']
        if image and allowed_file(image.filename):
            # Check the file size first
            image.seek(0, os.SEEK_END)
            file_size = image.tell()

            if file_size > 100 * 1024:  # 100 KB limit
                flash('File is too large. The image must be less than 100 KB.', 'danger')
                return redirect(request.url)

            # Save the image
            filename = secure_filename(image.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image.seek(0)  # Reset the file pointer to save the file
            image.save(image_path)

            # Save item to database with image path
            new_item = Item(name=name, price=float(price), unit=unit, image_path=image_path)
            db.session.add(new_item)
            db.session.commit()

            flash(f'Item "{name}" added successfully!', 'success')
            return redirect(url_for('items'))  # Redirect to the list of items page

    return render_template('add_item.html')

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

from decimal import Decimal

@app.route('/add_to_basket/<int:item_id>', methods=['POST'])
def add_to_basket(item_id):
    if 'user_id' not in session:
        flash('Please login to add items to your basket', 'danger')
        return redirect(url_for('login'))

    user_id = session['user_id']
    quantity = request.form.get('quantity')

    # Handle custom quantity
    if quantity == 'custom':
        try:
            custom_quantity = request.form.get('custom_quantity', '1')
            quantity = Decimal(custom_quantity)
        except Exception:
            flash('Invalid custom quantity entered.', 'danger')
            return redirect(url_for('items'))
    else:
        try:
            quantity = Decimal(quantity)
        except Exception:
            flash('Invalid quantity entered.', 'danger')
            return redirect(url_for('items'))
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

@app.route('/update_basket_quantity/<int:item_id>', methods=['POST'])
def update_basket_quantity(item_id):
    if 'user_id' not in session:
        flash('Please login to update items in your basket.', 'danger')
        return redirect(url_for('login'))

    user_id = session['user_id']
    try:
        # Get the new quantity from the form
        new_quantity = request.form.get('quantity', '1')

        # Convert to Decimal for precision
        new_quantity = Decimal(new_quantity)

        # Validate the maximum quantity
        if new_quantity > 50:
            flash('Please enter upto 50. Contact support for bulk orders.', 'danger')
            return redirect(url_for('basket'))

        # Fetch the basket item for the user and item
        basket_item = Basket.query.filter_by(user_id=user_id, item_id=item_id).first()

        if basket_item:
            # Update the quantity
            basket_item.quantity = new_quantity
            db.session.commit()
            flash('Basket updated successfully!', 'success')
        else:
            flash('Item not found in your basket.', 'danger')

    except Exception:
        flash('Invalid quantity entered.', 'danger')

    return redirect(url_for('basket'))

@app.route('/basket')
def basket():
    if 'user_id' not in session:
        flash('Please login to view your basket', 'danger')
        return redirect(url_for('login'))

    user_id = session['user_id']
    basket_items = db.session.query(Basket, Item).join(Item).filter(Basket.user_id == user_id).all()
    # Calculate the total price (convert Decimal to float)
    total_price = sum(float(item.price) * float(basket_item.quantity) for basket_item, item in basket_items)
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
    if 'user_id' not in session:
        flash('You must be logged in to complete the checkout process', 'danger')
        return redirect(url_for('login'))    
    user = User.query.get(session['user_id'])
    if request.method == 'POST':
        address_id = request.form.get('address_id')
        # payment_option = request.form.get('payment_option')
        payment_method = request.form.get('payment_method')
        # Check if an address was selected
        if not address_id:
            flash('Please select a delivery address', 'danger')
            return redirect(url_for('checkout'))
        address = Address.query.get(address_id)
        # Ensure the address exists and belongs to the current user
        if not address or address.user_id != user.id:
            flash('Invalid address selected', 'danger')
            return redirect(url_for('checkout'))
        # Process the order, create order entries for items in the basket, etc.
        basket_items = Basket.query.filter_by(user_id=user.id).all()
        total_price = sum(float(item.price) * float(basket_item.quantity) for basket_item, item in basket_items)
        # Example of creating an order from the basket
        for basket_item in basket_items:
            order = Order(
                user_id=user.id,
                item_id=basket_item.item_id,
                quantity=basket_item.quantity
            )
            db.session.add(order)
        db.session.query(Basket).filter_by(user_id=user.id).delete()
        # Commit the transaction
        db.session.commit()
        flash('Order placed successfully!', 'success')
        return redirect(url_for('profile'))
    # Handle GET request to display checkout form
    addresses = Address.query.filter_by(user_id=user.id).all()
    # Clear flash messages on GET request
    if request.method == 'GET':
        session.pop('_flashes', None)
    if not addresses:
        flash('Please add a delivery address before proceeding.', 'warning')
        return redirect(url_for('profile'))
    return render_template('checkout.html', addresses=addresses)

@app.route('/get_basket_items')
def get_basket_items():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'User not logged in'}), 400    
    user = User.query.get(session['user_id'])
    basket_items = Basket.query.filter_by(user_id=user.id).all()
    items = []
    total_price = 0.0    
    for basket_item in basket_items:
        # Convert both price and quantity to float before calculating total
        item_price = float(basket_item.item.price)  # Convert price to float
        item_quantity = float(basket_item.quantity)  # Convert quantity to float        
        item_data = {
            'name': basket_item.item.name,
            'price': item_price,
            'quantity': item_quantity,
            'unit': basket_item.item.unit
        }
        items.append(item_data)
        total_price = Decimal(total_price)
        total_price += Decimal(basket_item.item.price) * basket_item.quantity  # Perform multiplication after conversion    
    return jsonify({'success': True, 'items': items, 'total_price': total_price})

@app.route('/complete_order', methods=['POST'])
def complete_order():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'User not logged in'}), 401
    
    # Get user using Session.get()
    # user_id = session['user_id'] Working
    # user = db.session.get(User, user_id) Working
    user = db.session.get(User, session['user_id'])
    if not user:
        return jsonify({'success': False, 'message': 'User not found.'}), 404

    data = request.get_json()
    address_id = data.get('address_id')
    # payment_option = data.get('payment_option')
    payment_method = data.get('payment_method')
    # delivery_address = data.get('delivery_address')
    # delivery_address = data.get('address_id')
    # address_id = data.get('address_id')
    # delivery_address = Address.query.get(address_id) working
    delivery_address = db.session.get(Address, address_id)
    # Validate Address
    address = Address.query.filter_by(id=address_id, user_id=user.id).first()
    if not address:
        return jsonify({'success': False, 'message': 'Invalid address selected.'}), 400

    # Fetch Basket Items
    basket_items = Basket.query.filter_by(user_id=user.id).all()
    if not basket_items:
        return jsonify({'success': False, 'message': 'No items in the basket.'}), 400

    # Calculate Total Price and Create Orders
    total_price = Decimal(0.0)
    for basket_item in basket_items:
        item = basket_item.item  # Access the related Item object via the relationship
        if not item:
            return jsonify({'success': False, 'message': f'Item not found for basket item ID {basket_item.id}.'}), 400

        item_total = Decimal(item.price) * Decimal(basket_item.quantity)
        total_price += item_total

        # Create and add an Order
        order = Order(
            user_id=user.id,
            item_id=basket_item.item_id,
            quantity=basket_item.quantity,
            address_id=address.id,
            delivery_address=delivery_address.address,
            total_price=item_total,
            payment_method=payment_method
        )
        db.session.add(order)

    # Clear Basket
    Basket.query.filter_by(user_id=user.id).delete()

    # Commit Changes
    db.session.commit()

    return jsonify({'success': True, 'message': 'Order placed successfully!', 'total_price': str(total_price)})

@app.route('/hide_item/<int:item_id>', methods=['POST'])
def hide_item(item_id):
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Unauthorized access', 'danger')
        return redirect(url_for('items'))

    item = Item.query.get_or_404(item_id)
    item.is_hidden = True
    db.session.commit()
    flash('Item hidden successfully!', 'success')
    return redirect(url_for('items'))


@app.route('/unhide_item/<int:item_id>', methods=['POST'])
def unhide_item(item_id):
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Unauthorized access', 'danger')
        return redirect(url_for('items'))

    item = Item.query.get_or_404(item_id)
    item.is_hidden = False
    db.session.commit()
    flash('Item unhidden successfully!', 'success')
    return redirect(url_for('items'))

@app.route('/update_item/<int:item_id>', methods=['GET', 'POST'])
def update_item(item_id):
    # Check if the user is logged in and is an admin
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Unauthorized access', 'danger')
        return redirect(url_for('items'))  # Redirect to items page if not authorized

    # Get the item from the database
    item = Item.query.get_or_404(item_id)

    if request.method == 'POST':
        # Get the updated details from the form
        name = request.form['name']
        price = request.form['price']
        unit = request.form['unit']        
        # Handle the image file
        image = request.files.get('image')
        if image and allowed_file(image.filename):
            # Check the file size first
            image.seek(0, os.SEEK_END)
            file_size = image.tell()
            if file_size > 100 * 1024:  # 100 KB limit
                flash('File is too large. The image must be less than 100 KB.', 'danger')
                return redirect(request.url)
            # Save the image
            filename = secure_filename(image.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image.seek(0)  # Reset the file pointer to save the file
            image.save(image_path)
            item.image_path = image_path  # Update the image path in the item
        # Update the item details
        item.name = name
        item.price = float(price)
        item.unit = unit    
        db.session.commit()
        flash(f'Item "{name}" updated successfully!', 'success')
        return redirect(url_for('items'))  # Redirect to the list of items page
    # If GET request, render the update form with item details
    return render_template('update_item.html', item=item)

from werkzeug.security import generate_password_hash

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        flash('Please login to view your profile', 'danger')
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        action = request.form.get('action')
        # Handle updating the password
        if action == 'update_password':
            new_password = request.form.get('password')
            if not new_password or len(new_password) < 4:
                return jsonify({'success': False, 'message': 'Password must be at least 4 characters long.'}), 400
            
            user.password = new_password  # Directly saving plain-text password
            db.session.commit()
            return jsonify({'success': True, 'message': 'Password updated successfully!'}), 200
        # Handle making an address default
        elif action == 'make_default':
            address_id = request.form.get('address_id')
            address = Address.query.get(address_id)
            if address and address.user_id == user.id:
                for addr in user.addresses:
                    addr.is_default = False
                address.is_default = True
                db.session.commit()
                flash('Address set as default successfully!', 'success')
        # Handle updating phone number
        elif action == 'update_phone_number':
            phone_number = request.form.get('phone_number')
            if not phone_number or not phone_number.isdigit() or len(phone_number) != 10:
                return jsonify({'message': 'Invalid phone number. Please enter a valid 10-digit number.', 'success': False}), 400            
            # Check if the phone number already exists in the database
            existing_user = User.query.filter(User.phone_number == phone_number, User.id != user.id).first()
            if existing_user:
                return jsonify({'message': 'This phone number is already in use. Please choose a different number.', 'success': False}), 400            
            user.phone_number = phone_number
            db.session.commit()
            return jsonify({'message': 'Phone number updated successfully!', 'success': True}), 200        
        # Handle updating an address
        elif action == 'update_address':
            address_id = request.form.get('address_id')
            address_type = request.form.get('address_type')
            address_text = request.form.get('address')

            address = Address.query.get(address_id)
            if address and address.user_id == user.id:
                address.address_type = address_type
                address.address = address_text
                db.session.commit()
                return jsonify({'message': 'Address updated successfully!', 'success': True}), 200
            return jsonify({'message': 'Failed to update the address.', 'success': False}), 400
        # Handle adding a new address
        elif action == 'add_new_address':
            address_text = request.form.get('address')
            address_type = request.form.get('address_type')
            is_default = request.form.get('is_default') == 'on'

            if address_text and address_type:
                new_address = Address(
                    user_id=user.id,
                    address=address_text,
                    address_type=address_type,
                    is_default=is_default
                )
                db.session.add(new_address)
                # Ensure only one default address
                if is_default:
                    for address in user.addresses:
                        if address.id != new_address.id:
                            address.is_default = False

                db.session.commit()
                return jsonify({'success': True, 'message': 'Address added successfully!'})
            else:
                return jsonify({'success': False, 'message': 'Please provide valid address details.'}), 400
        # Handle deleting an address
        elif action == 'delete_address':
            address_id = request.form.get('address_id')
            address = Address.query.get(address_id)

            if address and address.user_id == user.id:
                db.session.delete(address)
                db.session.commit()
                return jsonify({'success': True, 'message': 'Address deleted successfully!'}), 200

            return jsonify({'success': False, 'message': 'Failed to delete the address.'}), 400

    return render_template('profile.html', user=user)

@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'user_id' not in session:
        flash('Please login to edit your profile', 'danger')
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        # Retrieve the new phone number
        new_phone_number = request.form.get('phone_number')

        # Validate the phone number is unique
        if new_phone_number != user.phone_number:
            existing_user = User.query.filter_by(phone_number=new_phone_number).first()
            if existing_user:
                flash('This phone number is already in use. Please choose a different number.', 'danger')
                return redirect(url_for('edit_profile'))

        # Update phone number if unique
        user.phone_number = new_phone_number

        # Update password if provided
        if request.form['password']:
            user.password = request.form['password']

        # Update addresses
        for i in range(5):
            address_id = request.form.get(f'address_id_{i}')
            address_text = request.form.get(f'address_{i}')
            address_type = request.form.get(f'address_type_{i}')
            is_default = request.form.get(f'is_default_{i}') == 'on'

            if address_id:
                # Update existing address
                address = Address.query.get(address_id)
                if address and address.user_id == user.id:  # Ensure address belongs to the user
                    address.address = address_text
                    address.address_type = address_type
                    address.is_default = is_default
            elif address_text:
                # Create new address if the text is provided and no existing address
                new_address = Address(
                    user_id=user.id,
                    address=address_text,
                    address_type=address_type,
                    is_default=is_default
                )
                db.session.add(new_address)

        # Ensure only one default address
        default_addresses = [a for a in user.addresses if a.is_default]
        if len(default_addresses) > 1:
            for address in default_addresses[1:]:
                address.is_default = False

        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))

    # Pass 'enumerate' explicitly to the template context
    return render_template('edit_profile.html', user=user, enumerate=enumerate)


# @app.route('/delete_address/<int:address_id>', methods=['POST'])
# def delete_address(address_id):
#     address = Address.query.get(address_id)
#     if address and address.user_id == session['user_id']:
#         db.session.delete(address)
#         db.session.commit()
#         flash('Address deleted successfully!', 'success')
#     else:
#         flash('Address not found or unauthorized.', 'danger')
#     return redirect(url_for('edit_profile'))


@app.route('/delete_address', methods=['POST'])
def delete_address_by_id():
    if 'user_id' not in session:
        return jsonify({'message': 'Unauthorized access'}), 401

    address_id = request.form.get('address_id')
    address = Address.query.get(address_id)

    if address and address.user_id == session['user_id']:
        db.session.delete(address)
        db.session.commit()
        return jsonify({'message': 'Address deleted successfully!'}), 200

    return jsonify({'message': 'Address not found or unauthorized'}), 404

@app.route('/orders', methods=['GET'])
def orders():
    if 'user_id' not in session:
        flash('Please login to view your orders', 'danger')
        return redirect(url_for('login'))
    
    user = User.query.filter_by(id=session['user_id']).first()
    if not user:
        return {"error": "User not found"}, 404

    # Retrieve user orders with related item data and payment method
    user_orders = Order.query.options(joinedload(Order.item)).filter_by(user_id=user.id).all()

    if not user_orders:
        flash("No orders found.", "info")
    
    # Process orders for the response
    orders_list = [
        {
            "order_id": order.id,
            "item_name": order.item.name,  # Access item relationship
            "quantity": order.quantity,
            "price": order.item.price,    # Fetching price for better UI display
            "total_price": round(float(order.item.price) * float(order.quantity), 2),  # Calculating total dynamically
            "delivery_address": order.delivery_address,
            "payment_method": order.payment_method,  # Include payment method for better UX
            "created_at": order.created_at
        }
        for order in user_orders
    ]

    return render_template('orders.html', orders=orders_list)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Ensures tables are created before starting the app

        # # Ensure an admin user exists (for simplicity, hardcoding admin credentials here)
        # if not User.query.filter_by(username='admin').first():
        #     admin_user = User(username='admin', password='', is_admin=True)
        #     db.session.add(admin_user)
        #     db.session.commit()

    app.run(host='0.0.0.0', port=5000)