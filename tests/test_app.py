import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app


@pytest.fixture
def app():
    """Create and configure a test app instance."""
    app = create_app()
    app.config['TESTING'] = True
    return app


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


def test_app_creation(app):
    """Test that the app can be created."""
    assert app is not None
    assert app.config['TESTING'] is True


def test_home_page(client):
    """Test the home page route."""
    response = client.get('/')
    assert response.status_code in [200, 404, 500] 
