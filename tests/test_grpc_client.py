import pytest
import sys
import os
from unittest.mock import patch, MagicMock
import grpc

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Prevent thread from starting when importing
with patch('threading.Thread'):
    import webApp.grpc_client as grpc_client
from grpc_services import greeter_pb2

class TestGrpcClient:
    
    @patch('webApp.grpc_client.grpc.insecure_channel')
    @patch('webApp.grpc_client.grpc.channel_ready_future')
    def test_check_server_success(self, mock_future, mock_channel):
        mock_future.return_value.result.return_value = None
        assert grpc_client.check_server("127.0.0.1:50051") is True

    @patch('webApp.grpc_client.grpc.insecure_channel')
    @patch('webApp.grpc_client.grpc.channel_ready_future')
    def test_check_server_timeout(self, mock_future, mock_channel):
        mock_future.return_value.result.side_effect = grpc.FutureTimeoutError()
        assert grpc_client.check_server("127.0.0.1:50051") is False

    @patch('webApp.grpc_client.ACTIVE_SERVERS', ['127.0.0.1:50051'])
    @patch('webApp.grpc_client.greeter_pb2_grpc.GreeterStub')
    @patch('webApp.grpc_client.grpc.insecure_channel')
    def test_get_stub_success(self, mock_channel, mock_stub):
        mock_stub_instance = MagicMock()
        mock_stub.return_value = mock_stub_instance
        
        stub = grpc_client.get_stub()
        assert stub == mock_stub_instance

    @patch('webApp.grpc_client.ACTIVE_SERVERS', [])
    def test_get_stub_empty(self):
        with pytest.raises(Exception, match="Không có server nào khả dụng"):
            grpc_client.get_stub()

    @patch('webApp.grpc_client.get_stub')
    def test_login_success(self, mock_get_stub):
        mock_stub = MagicMock()
        mock_stub.Authenticate.return_value = greeter_pb2.AuthResponse(success=True)
        mock_get_stub.return_value = mock_stub
        
        result = grpc_client.login('user', 'pass')
        assert result == "Success"

    @patch('webApp.grpc_client.get_stub')
    def test_login_failure(self, mock_get_stub):
        mock_stub = MagicMock()
        mock_stub.Authenticate.return_value = greeter_pb2.AuthResponse(success=False, status="Failure")
        mock_get_stub.return_value = mock_stub
        
        result = grpc_client.login('user', 'pass')
        assert "Failed:" in result

    @patch('webApp.grpc_client.get_stub')
    def test_login_grpc_error(self, mock_get_stub):
        mock_stub = MagicMock()
        class MockRpcError(grpc.RpcError):
            def code(self): return "UNAVAILABLE"
            def details(self): return "Server down"
        
        mock_stub.Authenticate.side_effect = MockRpcError()
        mock_get_stub.return_value = mock_stub
        
        result = grpc_client.login('user', 'pass')
        assert "gRPC Error: UNAVAILABLE - Server down" in result

    @patch('webApp.grpc_client.get_stub')
    def test_register_success(self, mock_get_stub):
        mock_stub = MagicMock()
        mock_stub.Register.return_value = greeter_pb2.RegisterResponse(success=True)
        mock_get_stub.return_value = mock_stub
        
        result = grpc_client.register('user', 'pass')
        assert result == "Success"

    @patch('webApp.grpc_client.get_stub')
    def test_delete_success(self, mock_get_stub):
        mock_stub = MagicMock()
        mock_stub.DeleteUser.return_value = greeter_pb2.DeleteUserResponse(success=True)
        mock_get_stub.return_value = mock_stub
        
        result = grpc_client.delete('user')
        assert result == "Success"

