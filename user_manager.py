import json
import os
import hashlib
from datetime import datetime

DATA_FILE = "users.json"

class UserManager:
    def __init__(self):
        self.users = {}
        self.load_data()

    def load_data(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    self.users = json.load(f)
            except:
                self.users = {}
        else:
            self.users = {}

    def save_data(self):
        # --- ĐÂY LÀ ĐOẠN THAY ĐỔI QUAN TRỌNG ---
        # Chỉ lưu những user có trường 'password' (Đã đăng ký)
        # Khách (không có password) sẽ bị loại bỏ khỏi danh sách cần lưu
        data_to_save = {k: v for k, v in self.users.items() if 'password' in v}
        
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=4)

    def _hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    # --- LẤY USER (Tự tạo trong RAM nếu là Khách) ---
    def get_user_data(self, username):
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Nếu chưa có trong bộ nhớ -> Tạo mới tạm thời (Khách)
        if username not in self.users:
            self.users[username] = {
                'money': 10000, # 10k mặc định
                'spins': 3,     # 3 lượt
                'last_login': today
                # Không có 'password' -> save_data sẽ bỏ qua ông này
            }
            # Không cần gọi save_data() ở đây vì khách không cần lưu
        
        # Logic reset lượt quay
        user = self.users[username]
        if user.get('last_login') != today:
            user['spins'] = user.get('spins', 0) + 1 
            user['last_login'] = today
            # Chỉ lưu nếu là user thật
            if 'password' in user:
                self.save_data()
            
        return user

    # --- ĐĂNG KÝ (Biến Khách thành User thật) ---
    def register(self, username, password):
        if username in self.users and 'password' in self.users[username]:
            return False, "Tên này đã có chủ!"
        
        if len(username) < 3 or len(password) < 3:
            return False, "Tên/Mật khẩu quá ngắn!"

        today = datetime.now().strftime("%Y-%m-%d")
        
        # Lấy tiền hiện tại (nếu đang chơi thử) hoặc reset 10k
        current_money = 10000
        if username in self.users:
            current_money = self.users[username].get('money', 10000)

        # Cập nhật thông tin và THÊM PASSWORD
        self.users[username] = {
            'password': self._hash_password(password),
            'money': current_money,
            'spins': 3,
            'last_login': today
        }
        # Gọi save_data -> Lúc này user đã có pass nên sẽ được lưu vào file
        self.save_data()
        return True, "Đăng ký thành công!"

    # --- ĐĂNG NHẬP ---
    def login(self, username, password):
        if username not in self.users:
            # Thử load lại từ file xem có không (trường hợp mới khởi động lại server)
            self.load_data()
            if username not in self.users:
                return False, "Tài khoản không tồn tại!"
        
        user = self.users[username]
        if 'password' not in user:
             return False, "Tài khoản Khách không cần đăng nhập!"

        if user.get('password') == self._hash_password(password):
            today = datetime.now().strftime("%Y-%m-%d")
            if user.get('last_login') != today:
                user['spins'] = user.get('spins', 0) + 1
                user['last_login'] = today
                self.save_data()
            return True, "Đăng nhập thành công!"
        else:
            return False, "Sai mật khẩu!"

    # --- CẬP NHẬT TIỀN ---
    def update_money(self, username, amount):
        user = self.get_user_data(username)
        user['money'] += amount
        if user['money'] < 0: user['money'] = 1000
        
        # Chỉ lưu file nếu là user thật
        if 'password' in user:
            self.save_data()
            
        return user['money']

    # --- TRỪ LƯỢT QUAY ---
    def use_spin(self, username):
        user = self.get_user_data(username)
        if user['spins'] > 0:
            user['spins'] -= 1
            if 'password' in user:
                self.save_data()
            return True, user['spins']
        return False, 0

    def get_top_users(self, limit=5):
        # Lọc user có tiền để xếp hạng
        sorted_users = sorted(self.users.items(), key=lambda item: item[1].get('money', 0), reverse=True)
        return [(k, v.get('money', 0)) for k, v in sorted_users[:limit]]