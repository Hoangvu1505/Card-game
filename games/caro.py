import random

class CaroGame:
    def __init__(self, room_id, host_sid=None):
        self.room_id = room_id
        self.host_sid = host_sid
        self.players = {}  # {sid: 'X' hoặc 'O'}
        self.board = {}    # Key: (row, col), Value: 'X'/'O'
        self.turn = 'X'    # X đi trước
        self.state = 'WAITING'
        self.winner = None
        self.is_bot_mode = False

    def add_player(self, sid, name):
        if len(self.players) >= 2: return False
        symbol = 'X' if len(self.players) == 0 else 'O'
        self.players[sid] = {'name': name, 'symbol': symbol}
        if len(self.players) == 2 or self.is_bot_mode:
            self.state = 'PLAYING'
        return True

    def make_move(self, sid, row, col):
        if self.state != 'PLAYING' or self.winner: return False, "Chưa chơi được"
        
        # Nếu là Bot mode, sid của Bot là 'BOT'
        if sid != 'BOT' and sid not in self.players: return False, "Bạn không ở trong phòng"
        
        # Kiểm tra lượt
        symbol = self.players[sid]['symbol'] if sid != 'BOT' else 'O'
        if symbol != self.turn: return False, "Chưa đến lượt"

        # Kiểm tra ô trống
        if (row, col) in self.board: return False, "Ô này đánh rồi"

        # Đánh dấu
        self.board[(row, col)] = symbol
        
        # Check thắng
        if self.check_win(row, col, symbol):
            self.winner = symbol
            self.state = 'FINISHED'
        else:
            # Đổi lượt
            self.turn = 'O' if self.turn == 'X' else 'X'
            
        return True, "OK"

    def check_win(self, r, c, symbol):
        # Kiểm tra 4 hướng: Ngang, Dọc, Chéo chính, Chéo phụ
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
        for dr, dc in directions:
            count = 1
            # Duyệt về 2 phía
            for i in range(1, 5):
                if self.board.get((r + dr*i, c + dc*i)) == symbol: count += 1
                else: break
            for i in range(1, 5):
                if self.board.get((r - dr*i, c - dc*i)) == symbol: count += 1
                else: break
            if count >= 5: return True
        return False

    def bot_move(self):
        # Bot đơn giản: Tìm ô trống ngẫu nhiên quanh các ô đã đánh (để không đánh quá xa)
        # Nếu bàn trống trơn thì đánh giữa
        if not self.board: return 7, 7
        
        possible_moves = set()
        for (r, c) in self.board:
            for dr in [-1, 0, 1]:
                for dc in [-1, 0, 1]:
                    if dr == 0 and dc == 0: continue
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < 15 and 0 <= nc < 15 and (nr, nc) not in self.board:
                        possible_moves.add((nr, nc))
        
        if possible_moves:
            return random.choice(list(possible_moves))
        return None
    
    # ... (Các hàm cũ giữ nguyên)

    def reset_game(self):
        
        self.board = {}      # Xóa bàn cờ
        self.winner = None   # Xóa người thắng
        self.turn = 'X'      # X đi trước
        self.state = 'PLAYING'
        return True