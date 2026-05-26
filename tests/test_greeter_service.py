import pytest
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock sys.argv before importing greeter_service to prevent sys.exit(1)
with patch.object(sys, 'argv', ['server.py', '50051']):
    from grpc_services.greeter_service import GreeterService
from grpc_services import greeter_pb2

class TestGreeterService:
    
    @pytest.fixture
    def service(self):
        with patch('grpc_services.greeter_service.GreeterService._broadcast_registration'), \
             patch('grpc_services.greeter_service.GreeterService._backup_data'):
            yield GreeterService()

    @pytest.fixture
    def mock_context(self):
        return MagicMock()

    @patch('grpc_services.greeter_service.UserLocal', [{'username': 'testuser', 'password': 'testpassword'}])
    def test_authenticate_success(self, service, mock_context):
        request = greeter_pb2.UserRequest(username='testuser', password='testpassword')
        response = service.Authenticate(request, mock_context)
        assert response.success is True

    @patch('grpc_services.greeter_service.UserLocal', [{'username': 'testuser', 'password': 'testpassword'}])
    def test_authenticate_failure(self, service, mock_context):
        request = greeter_pb2.UserRequest(username='testuser', password='wrongpassword')
        response = service.Authenticate(request, mock_context)
        assert response.success is False

    @patch('grpc_services.greeter_service.UserLocal', [])
    def test_register_success(self, service, mock_context):
        request = greeter_pb2.UserRequest(username='newuser', password='newpassword')
        with patch('grpc_services.greeter_service.GreeterService._broadcast_registration') as mock_broadcast, \
             patch('grpc_services.greeter_service.GreeterService._backup_data') as mock_backup:
            response = service.Register(request, mock_context)
            assert response.success is True
            assert response.status == "Success"
            mock_broadcast.assert_called_once()
            mock_backup.assert_called_once()

    @patch('grpc_services.greeter_service.UserLocal', [{'username': 'existinguser', 'password': 'password'}])
    def test_register_exist(self, service, mock_context):
        request = greeter_pb2.UserRequest(username='existinguser', password='password')
        response = service.Register(request, mock_context)
        assert response.success is False
        assert response.status == "Exist"

    @patch('grpc_services.greeter_service.UserLocal', [{'username': 'deleteuser', 'password': 'password'}])
    def test_delete_user_success(self, service, mock_context):
        request = greeter_pb2.UserRequest(username='deleteuser')
        with patch('grpc_services.greeter_service.GreeterService._backup_data') as mock_backup:
            response = service.DeleteUser(request, mock_context)
            assert response.success is True
            mock_backup.assert_called_once()

    @patch('grpc_services.greeter_service.UserLocal', [{'username': 'otheruser', 'password': 'password'}])
    def test_delete_user_not_found(self, service, mock_context):
        request = greeter_pb2.UserRequest(username='deleteuser')
        response = service.DeleteUser(request, mock_context)
        assert response.success is False

    def test_check_heartbeat(self, service, mock_context):
        request = greeter_pb2.Empty()
        response = service.CheckHeartbeat(request, mock_context)
        assert response.alive is True

    @patch('grpc_services.greeter_service.UserLocal', [])
    def test_backup_data_success(self, service, mock_context):
        request = MagicMock()
        request.json_data = '[{"username": "backup_user", "password": "123"}]'
        response = service.BackupData(request, mock_context)
        assert response.success is True
        from grpc_services.greeter_service import UserLocal
        assert len(UserLocal) == 1
        assert UserLocal[0]['username'] == "backup_user"

    def test_backup_data_invalid(self, service, mock_context):
        request = MagicMock()
        request.json_data = '{"username": "not_a_list"}'
        response = service.BackupData(request, mock_context)
        assert response.success is False

    def test_backup_data_exception(self, service, mock_context):
        request = MagicMock()
        request.json_data = 'invalid json'
        response = service.BackupData(request, mock_context)
        assert response.success is False

    @patch('grpc_services.greeter_service.UserLocal', [{'username': 'test', 'password': '123'}])
    def test_request_backup_success(self, service, mock_context):
        request = greeter_pb2.Empty()
        response = service.RequestBackup(request, mock_context)
        assert response.success is True
        assert 'test' in response.message

    @patch('grpc_services.greeter_service.json.dumps', side_effect=Exception("mocked error"))
    def test_request_backup_exception(self, mock_json_dumps, service, mock_context):
        request = greeter_pb2.Empty()
        response = service.RequestBackup(request, mock_context)
        assert response.success is False

    @patch('grpc_services.greeter_service.open')
    @patch('grpc_services.greeter_service.GreeterService._send_backup_to_servers')
    def test__backup_data(self, mock_send, mock_open):
        from grpc_services.greeter_service import GreeterService
        svc = GreeterService()
        svc._backup_data()
        mock_open.assert_called_once()
        mock_send.assert_called_once()

    @patch('grpc_services.greeter_service.grpc.insecure_channel')
    @patch('grpc_services.greeter_service.greeter_pb2_grpc.GreeterStub')
    def test__is_server_alive_true(self, mock_stub_class, mock_channel, service):
        mock_stub = MagicMock()
        mock_stub_class.return_value = mock_stub
        mock_stub.CheckHeartbeat.return_value.alive = True
        assert service._is_server_alive(50052) is True

    @patch('grpc_services.greeter_service.grpc.insecure_channel')
    @patch('grpc_services.greeter_service.greeter_pb2_grpc.GreeterStub')
    def test__is_server_alive_false(self, mock_stub_class, mock_channel, service):
        import grpc
        mock_stub = MagicMock()
        mock_stub_class.return_value = mock_stub
        mock_stub.CheckHeartbeat.side_effect = grpc.RpcError("error")
        assert service._is_server_alive(50052) is False

    @patch('grpc_services.greeter_service.time.sleep', side_effect=InterruptedError)
    @patch('grpc_services.greeter_service.GreeterService._is_server_alive')
    def test__schedule_heartbeat(self, mock_is_alive, mock_sleep, service):
        mock_is_alive.side_effect = [True, False, True, False] 
        import grpc_services.greeter_service as gs
        gs.dead_server = [50052]
        try:
            service._schedule_heartbeat()
        except InterruptedError:
            pass
        assert mock_is_alive.call_count >= 2

    @patch('grpc_services.greeter_service.grpc.insecure_channel')
    @patch('grpc_services.greeter_service.greeter_pb2_grpc.GreeterStub')
    def test__send_registration_to_server(self, mock_stub_class, mock_channel, service):
        mock_stub = MagicMock()
        mock_stub_class.return_value = mock_stub
        mock_stub.Register.return_value.success = True
        service._send_registration_to_server(50052, "u", "p")
        mock_stub.Register.assert_called_once()
        
    @patch('grpc_services.greeter_service.threading.Thread')
    def test__broadcast_registration(self, mock_thread_class):
        from grpc_services.greeter_service import GreeterService
        svc = GreeterService()
        mock_thread = MagicMock()
        mock_thread_class.return_value = mock_thread
        import grpc_services.greeter_service as gs
        gs.dead_server = [50053]
        gs.port = 50051
        svc._broadcast_registration("u", "p")
        mock_thread_class.assert_called_once()
        mock_thread.start.assert_called_once()
        mock_thread.join.assert_called_once()

    @patch('grpc_services.greeter_service.grpc.insecure_channel')
    @patch('grpc_services.greeter_service.greeter_pb2_grpc.GreeterStub')
    def test__send_backup_to_servers(self, mock_stub_class, mock_channel, service):
        mock_stub = MagicMock()
        mock_stub_class.return_value = mock_stub
        mock_stub.BackupData.return_value.success = True
        import grpc_services.greeter_service as gs
        gs.dead_server = []
        gs.port = 50051
        service._send_backup_to_servers("[]")
        assert mock_stub.BackupData.call_count == 2

    @patch('grpc_services.greeter_service.grpc.insecure_channel')
    @patch('grpc_services.greeter_service.greeter_pb2_grpc.GreeterStub')
    def test__request_backup_from_server(self, mock_stub_class, mock_channel, service):
        mock_stub = MagicMock()
        mock_stub_class.return_value = mock_stub
        mock_stub.RequestBackup.return_value.success = True
        mock_stub.RequestBackup.return_value.message = '[{"username":"bk","password":"12"}]'
        service._request_backup_from_server(50052)
        from grpc_services.greeter_service import UserLocal
        assert len(UserLocal) > 0
        assert UserLocal[0]['username'] == 'bk'

    @patch('grpc_services.greeter_service.time.sleep')
    @patch('grpc_services.greeter_service.GreeterService._backup_data', side_effect=InterruptedError)
    def test__schedule_backup(self, mock_backup, mock_sleep, service):
        try:
            service._schedule_backup()
        except InterruptedError:
            pass
        mock_backup.assert_called_once()

    @patch('grpc_services.greeter_service.time.sleep')
    @patch('grpc_services.greeter_service.GreeterService._broadcast_registration', side_effect=InterruptedError)
    def test__broadcast_periodically(self, mock_broadcast, mock_sleep, service):
        from grpc_services.greeter_service import UserLocal
        UserLocal.clear()
        UserLocal.append({'username': 'u1', 'password': 'p1'})
        try:
            service._broadcast_periodically()
        except InterruptedError:
            pass
        mock_broadcast.assert_called_once()

    @patch('grpc_services.greeter_service.time.sleep', side_effect=InterruptedError)
    @patch('grpc_services.greeter_service.grpc.insecure_channel')
    @patch('grpc_services.greeter_service.greeter_pb2_grpc.GreeterStub')
    def test__check_server_status(self, mock_stub_class, mock_channel, mock_sleep, service):
        mock_stub = MagicMock()
        mock_stub_class.return_value = mock_stub
        mock_stub.CheckHeartbeat.return_value.alive = True
        import grpc_services.greeter_service as gs
        gs.dead_server = [50052, 50053]
        try:
            service._check_server_status()
        except InterruptedError:
            pass
        assert len(gs.dead_server) == 0

@patch('sys.argv', ['server.py', '50051'])
@patch('grpc_services.greeter_service.grpc.server')
@patch('grpc_services.greeter_service.GreeterService._request_backup_from_server')
@patch('grpc_services.greeter_service.GreeterService._is_server_alive', return_value=True)
def test_start_services(mock_is_alive, mock_req_backup, mock_grpc_server):
    from grpc_services.greeter_service import start_services
    mock_server_instance = MagicMock()
    mock_grpc_server.return_value = mock_server_instance
    start_services()
    mock_grpc_server.assert_called_once()
    mock_server_instance.start.assert_called_once()
    mock_server_instance.wait_for_termination.assert_called_once()
