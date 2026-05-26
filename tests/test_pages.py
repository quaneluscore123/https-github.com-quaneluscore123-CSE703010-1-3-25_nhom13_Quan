import pytest
from unittest.mock import patch
from webApp.pages.controller import page
from flask import Flask

@pytest.fixture
def app():
    app = Flask(__name__)
    # Register blueprint with app
    app.register_blueprint(page)
    # Cấu hình đường dẫn templates folder
    # Mock render_template vì chúng ta không thực sự cần file HTML để test routing logic.
    app.template_folder = 'templates'
    return app

@pytest.fixture
def client(app):
    return app.test_client()

def test_home_page(client, mocker):
    mocker.patch('webApp.pages.services.render_template', return_value="Home Page Rendered")
    response = client.get('/')
    assert response.status_code == 200
    assert b"Home Page Rendered" in response.data

    response_index = client.get('/index')
    assert response_index.status_code == 200
    assert b"Home Page Rendered" in response_index.data

def test_contact_page(client, mocker):
    mocker.patch('webApp.pages.services.render_template', return_value="Contact Page")
    response = client.get('/contact')
    assert response.status_code == 200
    assert b"Contact Page" in response.data

def test_introduce_page(client, mocker):
    mocker.patch('webApp.pages.services.render_template', return_value="Introduce Page")
    response = client.get('/introduce')
    assert response.status_code == 200
    assert b"Introduce Page" in response.data

def test_products_page(client, mocker):
    mocker.patch('webApp.pages.services.render_template', return_value="Products Page")
    response = client.get('/products')
    assert response.status_code == 200
    assert b"Products Page" in response.data

def test_payment_page(client, mocker):
    # Mock _get_cart to return some fake data
    mock_cart = [{'id': 1, 'quantity': 2, 'price': 100}]
    mocker.patch('webApp.pages.services._get_cart', return_value=mock_cart)
    mocker.patch('webApp.pages.services.render_template', return_value="Payment Page")
    
    response = client.get('/payment')
    assert response.status_code == 200
    assert b"Payment Page" in response.data

def test_cart_page(client, mocker):
    # Mock _get_cart
    mock_cart = [{'id': 2, 'quantity': 1, 'price': 50}]
    mocker.patch('webApp.pages.services._get_cart', return_value=mock_cart)
    mocker.patch('webApp.pages.services.render_template', return_value="Cart Page")
    
    response = client.get('/cart')
    assert response.status_code == 200
    assert b"Cart Page" in response.data
