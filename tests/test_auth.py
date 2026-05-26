import pytest
import sys
import os
import json
from unittest.mock import patch
import grpc

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from webApp import create_app

@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    return app

@pytest.fixture
def client(app):
    return app.test_client()

class TestAuthModule:
    """Test suite for authentication module."""
    
    @patch('webApp.auth.services.login')
    def test_login_success(self, mock_login, client):
        mock_login.return_value = "Success"
        response = client.post('/login', json={'username': 'user1', 'password': '123'})
        assert response.status_code == 200
        json_data = response.get_json()
        assert "thành công" in json_data['message']

    @patch('webApp.auth.services.login')
    def test_login_failure(self, mock_login, client):
        mock_login.return_value = "Failed: Invalid"
        response = client.post('/login', json={'username': 'user1', 'password': 'wrong'})
        assert response.status_code == 401
        json_data = response.get_json()
        assert "không chính xác" in json_data['message']

    def test_login_missing_data(self, client):
        response = client.post('/login', json={'username': 'user1'})
        assert response.status_code == 409
        json_data = response.get_json()
        assert "Vui lòng" in json_data['message']

    @patch('webApp.auth.services.login')
    def test_login_grpc_error(self, mock_login, client):
        # Create a mock gRPC error
        class MockRpcError(grpc.RpcError):
            def details(self):
                return "Mock connection error"
        
        mock_login.side_effect = MockRpcError()
        response = client.post('/login', json={'username': 'user1', 'password': '123'})
        assert response.status_code == 500
        json_data = response.get_json()
        assert "Mock connection error" in json_data['message']

    @patch('webApp.auth.services.register')
    def test_register_success(self, mock_register, client):
        mock_register.return_value = "Success"
        response = client.post('/register', json={'username': 'user2', 'password': '123'})
        assert response.status_code == 201

    @patch('webApp.auth.services.register')
    def test_register_exist(self, mock_register, client):
        mock_register.return_value = "Exist"
        response = client.post('/register', json={'username': 'user1', 'password': '123'})
        assert response.status_code == 409

    @patch('webApp.auth.services.register')
    def test_register_failure(self, mock_register, client):
        mock_register.return_value = "Failed: Error"
        response = client.post('/register', json={'username': 'user2', 'password': '123'})
        assert response.status_code == 500

    def test_register_missing_data(self, client):
        response = client.post('/register', json={'username': 'user2'})
        assert response.status_code == 400

    @patch('webApp.auth.services.register')
    def test_register_grpc_error(self, mock_register, client):
        class MockRpcError(grpc.RpcError):
            def details(self):
                return "Mock connection error"
        
        mock_register.side_effect = MockRpcError()
        response = client.post('/register', json={'username': 'user2', 'password': '123'})
        assert response.status_code == 500

    @patch('webApp.auth.services.delete')
    def test_delete_user_success(self, mock_delete, client):
        mock_delete.return_value = "Success"
        response = client.delete('/deleteUser', json={'username': 'user1'})
        assert response.status_code == 200

    @patch('webApp.auth.services.delete')
    def test_delete_user_failure(self, mock_delete, client):
        mock_delete.return_value = "Failed: Not found"
        response = client.delete('/deleteUser', json={'username': 'user1'})
        assert response.status_code == 500

    def test_delete_user_missing_data(self, client):
        response = client.delete('/deleteUser', json={})
        assert response.status_code == 400

    @patch('webApp.auth.services.delete')
    def test_delete_user_grpc_error(self, mock_delete, client):
        class MockRpcError(grpc.RpcError):
            def details(self):
                return "Mock connection error"
        
        mock_delete.side_effect = MockRpcError()
        response = client.delete('/deleteUser', json={'username': 'user1'})
        assert response.status_code == 500

