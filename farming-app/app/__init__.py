from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = '411da25ae27244e55cc891e44e656dc3'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///farming.db'

    db.init_app(app)
    login_manager.init_app(app)

    # Register blueprint
    from .routes import main
    app.register_blueprint(main)

    # User loader function for Flask-Login
    from .models import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    return app
