import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from webApp import create_app

@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.secret_key = 'test_secret_key' # Needed for session
    return app

@pytest.fixture
def client(app):
    return app.test_client()

class TestCartModule:
    """Test suite for cart module."""
    
    def test_add_to_cart_new_product(self, client):
        data = {'id': 1, 'name': 'Product 1', 'price': 100.0, 'image_url': 'url1'}
        response = client.post('/cart/add', json=data)
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data['success'] is True
        assert json_data['new_quantity'] == 1

        with client.session_transaction() as sess:
            assert len(sess['cart']) == 1
            assert sess['cart'][0]['id'] == 1

    def test_add_to_cart_existing_product(self, client):
        # First add
        client.post('/cart/add', json={'id': 1, 'name': 'Product 1', 'price': 100.0})
        # Second add
        response = client.post('/cart/add', json={'id': 1, 'name': 'Product 1', 'price': 100.0})
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data['success'] is True
        assert json_data['new_quantity'] == 2

        with client.session_transaction() as sess:
            assert len(sess['cart']) == 1
            assert sess['cart'][0]['quantity'] == 2

    def test_add_to_cart_invalid_data(self, client):
        response = client.post('/cart/add', json={})
        assert response.status_code == 400
        
        response = client.post('/cart/add', json={'id': 1}) # missing name
        assert response.status_code == 400

    def test_remove_from_cart(self, client):
        client.post('/cart/add', json={'id': 1, 'name': 'Product 1', 'price': 100.0})
        response = client.post('/cart/remove/1')
        assert response.status_code == 200
        
        with client.session_transaction() as sess:
            assert len(sess.get('cart', [])) == 0

    def test_increase_quantity_success(self, client):
        client.post('/cart/add', json={'id': 1, 'name': 'Product 1', 'price': 100.0})
        response = client.post('/cart/increase/1')
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data['success'] is True
        assert json_data['new_quantity'] == 2

    def test_increase_quantity_not_found(self, client):
        response = client.post('/cart/increase/999')
        assert response.status_code == 404

    def test_decrease_quantity_success(self, client):
        client.post('/cart/add', json={'id': 1, 'name': 'Product 1', 'price': 100.0})
        client.post('/cart/increase/1')
        response = client.post('/cart/decrease/1')
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data['success'] is True
        assert json_data['new_quantity'] == 1

    def test_decrease_quantity_remove(self, client):
        client.post('/cart/add', json={'id': 1, 'name': 'Product 1', 'price': 100.0})
        response = client.post('/cart/decrease/1')
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data['success'] is True
        assert json_data['new_quantity'] == 1

        with client.session_transaction() as sess:
            assert len(sess.get('cart', [])) == 0

    def test_decrease_quantity_not_found(self, client):
        response = client.post('/cart/decrease/999')
        assert response.status_code == 404
