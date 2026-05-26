import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from webApp import create_app

@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.secret_key = 'test_secret_key'
    return app

@pytest.fixture
def client(app):
    return app.test_client()

class TestPaymentModule:
    """Test suite for payment module."""
    
    def test_submit_payment_success(self, client):
        data = {
            'name': 'John Doe',
            'phone': '0123456789',
            'address': '123 Test St',
            'payment_method': 'cod',
            'cart': [
                {'id': 1, 'name': 'Product 1', 'price': 100.0, 'quantity': 2},
                {'id': 2, 'name': 'Product 2', 'price': 50.0, 'quantity': 1}
            ]
        }
        
        with client.session_transaction() as sess:
            sess['cart'] = data['cart']
            
        response = client.post('/payment/submit', json=data)
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data['success'] is True
        assert json_data['total_price'] == '250.0 VND'
        
        with client.session_transaction() as sess:
            assert len(sess.get('cart', [])) == 0

    def test_submit_payment_missing_data(self, client):
        data = {
            'name': 'John Doe',
            'phone': '0123456789',
            'cart': []
        }
        response = client.post('/payment/submit', json=data)
        assert response.status_code == 400
        json_data = response.get_json()
        assert json_data['success'] is False

    def test_submit_payment_invalid_phone(self, client):
        data = {
            'name': 'John Doe',
            'phone': '123', # invalid length
            'address': '123 Test St',
            'payment_method': 'cod',
            'cart': [{'id': 1, 'quantity': 1}]
        }
        response = client.post('/payment/submit', json=data)
        assert response.status_code == 400
        json_data = response.get_json()
        assert "Số điện thoại không hợp lệ" in json_data['message']

    def test_submit_payment_invalid_method(self, client):
        data = {
            'name': 'John Doe',
            'phone': '0123456789',
            'address': '123 Test St',
            'payment_method': 'invalid_method',
            'cart': [{'id': 1, 'quantity': 1}]
        }
        response = client.post('/payment/submit', json=data)
        assert response.status_code == 400
        json_data = response.get_json()
        assert json_data['success'] is False
        assert "Phương thức thanh toán không hợp lệ" in json_data['message']

