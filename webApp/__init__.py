import os
from dotenv import load_dotenv
from flask import Flask
from .pages.controller import page
from .auth.controller import auth
from .cart.controller import cart
from .payment.controller import payment

load_dotenv()


def create_app(config_file='config.py'):
    app = Flask(__name__, template_folder='../templates', static_folder='../static')

    app.config.from_pyfile(config_file)

    app.register_blueprint(page)
    app.register_blueprint(auth)
    app.register_blueprint(cart)
    app.register_blueprint(payment)

    return app
