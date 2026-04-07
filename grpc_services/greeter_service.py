import grpc
import json
import threading
import time
from grpc_services import greeter_pb2_grpc, greeter_pb2
from webApp import config
from webApp.model import UserLocal
import sys
from concurrent import futures

SECRET_KEY = config.SECRET_KEY
SERVER_PORTS = [50051, 50052, 50053]

dead_server = []

def portIsValid():
    """Kiểm tra và trả về cổng hợp lệ từ đối số dòng lệnh."""
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 50051
    if port not in SERVER_PORTS:
        print("❌ Cổng không hợp lệ. Vui lòng chọn từ 50051 đến 50053.")
        sys.exit(1)
    return port

port = portIsValid()

BACKUP_FILE_PATH = f'user_data_backup_{port}.json'

class GreeterService(greeter_pb2_grpc.GreeterServicer):
    # -------------- Chức năng chính --------------
    def Authenticate(self, request, context):
        """Xác thực người dùng."""
        username = request.username
        password = request.password

        for user in UserLocal:
            if user['username'] == username and user['password'] == password:
                print(f"Đăng nhập thành công: {username}")
                return greeter_pb2.AuthResponse(success=True)
        return greeter_pb2.AuthResponse(status="Failure", success=False)

    def Register(self, request, context):
        """Đăng ký người dùng mới."""
        username = request.username
        password = request.password

        for user in UserLocal:
            if user['username'] == username:
                return greeter_pb2.RegisterResponse(success=False, message="Tài khoản đã tồn tại.", status="Exist")
        
        print(f"Đăng ký tài khoản mới: {username}")
        UserLocal.append({'username': username, 'password': password})
        self._broadcast_registration(username, password)
        self._backup_data()
        print(UserLocal)
        return greeter_pb2.RegisterResponse(success=True, message="Đăng ký thành công.", status="Success")

    def DeleteUser(self, request, context):
        """Xóa người dùng khỏi danh sách."""
        username = request.username
        new_user_list = [user for user in UserLocal if user['username'] != username]
        
        if len(new_user_list) == len(UserLocal):
            return greeter_pb2.DeleteUserResponse(success=False, message="Không tìm thấy tài khoản.")

        UserLocal.clear()
        UserLocal.extend(new_user_list)
        self._backup_data()
        print(UserLocal)
        return greeter_pb2.DeleteUserResponse(success=True, message="Xóa tài khoản thành công.")

    def CheckHeartbeat(self, request, context):
        """Trả về trạng thái sống của server."""
        return greeter_pb2.HeartbeatResponse(alive=True)


    # -------------- Sao lưu dữ liệu --------------
    def _backup_data(self):
        """Lưu dữ liệu vào JSON và gửi sao lưu đến server khác."""
        backup_json = json.dumps(UserLocal, indent=4)
        with open(BACKUP_FILE_PATH, 'w') as f:
            f.write(backup_json)
        print(f"💾 Dữ liệu đã được sao lưu vào {BACKUP_FILE_PATH}")
        self._send_backup_to_servers(backup_json)

    def BackupData(self, request, context):
        """Nhận dữ liệu sao lưu từ server khác."""
        try:
            data = json.loads(request.json_data)
            if not isinstance(data, list):
                return greeter_pb2.BackupResponse(success=False, message="Dữ liệu sao lưu không hợp lệ.")
            UserLocal.clear()
            UserLocal.extend(data)
            print("🔄 Đã nhận và cập nhật dữ liệu sao lưu.")
            return greeter_pb2.BackupResponse(success=True, message="Dữ liệu sao lưu đã được cập nhật.")
        except Exception as e:
            return greeter_pb2.BackupResponse(success=False, message=f"Lỗi khi cập nhật dữ liệu: {str(e)}")

    def RequestBackup(self, request, context):
        """Gửi dữ liệu sao lưu đến server khác theo yêu cầu."""
        try:
            print("📤 Nhận yêu cầu sao lưu từ server khác. Đang gửi dữ liệu...")
            backup_json = json.dumps(UserLocal, indent=4)
            return greeter_pb2.BackupResponse(success=True, message=backup_json)
        except Exception as e:
            return greeter_pb2.BackupResponse(success=False, message=f"Lỗi sao lưu: {str(e)}")


    # -------------- Quản lý heartbeat --------------
    def _is_server_alive(self, server):
        """Kiểm tra server có đang hoạt động không."""
        try:
            with grpc.insecure_channel(f'localhost:{server}') as channel:
                stub = greeter_pb2_grpc.GreeterStub(channel)
                response = stub.CheckHeartbeat(greeter_pb2.Empty())
                return response.alive
        except grpc.RpcError:
            return False

    def _schedule_heartbeat(self):
        """Gửi heartbeat định kỳ mỗi 15 giây."""
        while True:
            for server in SERVER_PORTS:
                if server == port:
                    continue
                if self._is_server_alive(server):
                    if server in dead_server:
                        dead_server.remove(server)
                    print(f"✅ Server {server} đang hoạt động.")
                else:
                    if server not in dead_server:
                        dead_server.append(server)
                    print(f"❌ Server {server} không phản hồi.")
            time.sleep(15)

    # -------------- Xử lý đăng ký người dùng --------------
    def _send_registration_to_server(self, server, username, password):
        """Gửi thông tin đăng ký đến một server cụ thể."""
        try:
            print(f"Gửi thông tin đăng ký tới server: {server}")
            with grpc.insecure_channel(f'localhost:{server}') as channel:
                stub = greeter_pb2_grpc.GreeterStub(channel)
                response = stub.Register(greeter_pb2.UserRequest(username=username, password=password))
                if response.success:
                    print(f"Đã gửi thông tin đăng ký thành công đến {server}")
                else:
                    print(f"Không thể gửi thông tin đăng ký đến {server}: {response.message}")
        except grpc.RpcError as e:
            print(f"Lỗi khi gửi thông tin đến server {server}: {e.details()}")

    def _broadcast_registration(self, username, password):
        """Gửi thông tin đăng ký đến tất cả server khác, tránh gửi đến chính mình."""
        threads = []  # Danh sách các luồng

        for server in SERVER_PORTS:
            if server == port:
                continue  # Bỏ qua chính server hiện tại
            if server in dead_server:
                print(f"⚠️ Bỏ qua server {server} (Không phản hồi)")
                continue
            
            # Tạo và chạy luồng gửi thông tin đăng ký
            thread = threading.Thread(target=self._send_registration_to_server, args=(server, username, password))
            thread.start()
            threads.append(thread)

        # Đợi tất cả luồng hoàn thành trước khi tiếp tục
        for thread in threads:
            thread.join()

    # -------------- Quản lý sao lưu dữ liệu --------------
    def _send_backup_to_servers(self, backup_json):
        """Gửi sao lưu đến các server còn sống."""
        for server in SERVER_PORTS:
            if server == port:
                continue  # Không gửi đến chính mình

            if server in dead_server:
                print(f"⚠️ Bỏ qua server {server} (Không phản hồi)")
                continue

            try:
                with grpc.insecure_channel(f'localhost:{server}') as channel:
                    stub = greeter_pb2_grpc.GreeterStub(channel)
                    response = stub.BackupData(greeter_pb2.BackupRequest(json_data=backup_json))
                    if response.success:
                        print(f"✅ Gửi sao lưu thành công đến {server}")
                        print(UserLocal)
                    else:
                        print(f"⚠️ Gửi sao lưu đến {server} thất bại: {response.message}")
            except grpc.RpcError as e:
                print(f"❌ Lỗi khi gửi sao lưu đến {server}: {e.details()}")

    def _request_backup_from_server(self, server):
        """Yêu cầu server khác gửi dữ liệu sao lưu."""
        try:
            with grpc.insecure_channel(f'localhost:{server}') as channel:
                stub = greeter_pb2_grpc.GreeterStub(channel)
                response = stub.RequestBackup(greeter_pb2.Empty())

                if response.success:
                    backup_data = json.loads(response.message)
                    if isinstance(backup_data, list):
                        UserLocal.clear()
                        UserLocal.extend(backup_data)
                        print(f"✅ Đã nhận và cập nhật dữ liệu sao lưu từ server {server}.")
                    else:
                        print(f"⚠️ Dữ liệu sao lưu từ server {server} không hợp lệ.")
                else:
                    print(f"❌ Yêu cầu sao lưu từ server {server} thất bại: {response.message}")
        except grpc.RpcError as e:
            print(f"❌ Lỗi khi yêu cầu sao lưu từ server {server}: {e.details()}")

    def _schedule_backup(self):
        """Chạy sao lưu định kỳ mỗi 60 giây và gửi đến server khác."""
        while True:
            time.sleep(60)  # Chờ 60 giây
            self._backup_data()  # Thực hiện sao lưu và gửi đến server khác
            print(UserLocal)
    # -------------- Quản lý heartbeat --------------
    def CheckHeartbeat(self, request, context):
        """Server phản hồi trạng thái sống (heartbeat)."""
        return greeter_pb2.HeartbeatResponse(alive=True)

    def _check_server_status(self):
        """Kiểm tra trạng thái của các server khác bằng heartbeat."""
        while True:
            for server in SERVER_PORTS:
                if server == port:
                    continue  # Bỏ qua chính mình

                try:
                    with grpc.insecure_channel(f'localhost:{server}') as channel:
                        stub = greeter_pb2_grpc.GreeterStub(channel)
                        response = stub.CheckHeartbeat(greeter_pb2.Empty())

                        if response.alive:
                            if server in dead_server:
                                dead_server.remove(server)  # Server đã sống lại
                                print(f"✅ Server {server} đã hoạt động trở lại.")
                        else:
                            if server not in dead_server:
                                dead_server.add(server)  # Đánh dấu server chết
                                print(f"❌ Server {server} không phản hồi.")
                except grpc.RpcError:
                    if server not in dead_server:
                        dead_server.add(server)
                        print(f"❌ Không thể kết nối đến server {server}. Có thể đã chết.")

            time.sleep(30)  # Kiểm tra trạng thái mỗi 30 giây

    # -------------- Gửi thông tin định kỳ --------------
    def _broadcast_periodically(self):
        """Chạy định kỳ để gửi thông tin đăng ký mới đến các server khác mỗi 60 giây."""
        last_sent_users = set()  # Giữ danh sách user đã gửi

        while True:
            time.sleep(60)  # Chờ 60 giây trước khi gửi lại

            for user in UserLocal:
                user_tuple = (user['username'], user['password'])
                if user_tuple not in last_sent_users:  # Chỉ gửi nếu là user mới
                    self._broadcast_registration(user['username'], user['password'])
                    last_sent_users.add(user_tuple)


# ----------------- Khởi động Services -----------------
def start_services():
    greeter_service = GreeterService()
    print(f"🔴 Danh sách server không phản hồi: {dead_server}")
    
    for server in SERVER_PORTS:
        if server == port:
            continue
        if greeter_service._is_server_alive(server):
            dead_server.remove(server) if server in dead_server else None
            greeter_service._request_backup_from_server(server)
        else:
            dead_server.append(server) if server not in dead_server else None

    backup_thread = threading.Thread(target=greeter_service._schedule_backup, daemon=True)
    backup_thread.start()
    
    heartbeat_thread = threading.Thread(target=greeter_service._schedule_heartbeat, daemon=True)
    heartbeat_thread.start()

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    greeter_pb2_grpc.add_GreeterServicer_to_server(greeter_service, server)
    server.add_insecure_port(f'[::]:{port}')
    server.start()
    print(f"✅ Server started on port {port}")
    server.wait_for_termination()

start_services()
