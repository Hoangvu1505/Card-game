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

    def reset_game(self):
        
        self.board = {}      # Xóa bàn cờ
        self.winner = None   # Xóa người thắng
        self.turn = 'X'      # X đi trước
        self.state = 'PLAYING'
        return True
    
    # ----------------------------------------------------------------
    # --- PHẦN TRÍ TUỆ NHÂN TẠO (AI) MỚI ---
    # ----------------------------------------------------------------
    
    def bot_move(self):
        # Nếu bàn cờ trống, đánh luôn vào giữa cho "ngầu"
        if not self.board:
            return 7, 7

        # Ký hiệu của Bot và Người
        bot_sym = 'O'
        human_sym = 'X'
        
        best_score = -1
        best_moves = []

        # Chỉ quét những ô trống nằm gần các ô đã đánh (tối ưu hiệu suất)
        # Thay vì quét cả 225 ô, ta chỉ quét ô trống có hàng xóm
        possible_moves = self.get_neighbor_cells()
        
        if not possible_moves: 
            return 7, 7 # Phòng hờ

        for (r, c) in possible_moves:
            # Tính điểm tấn công (Bot đánh vào đây lợi thế nào?)
            attack_score = self.evaluate_point(r, c, bot_sym)
            
            # Tính điểm phòng thủ (Nếu Bot không đánh, Người đánh vào đây nguy hiểm thế nào?)
            defense_score = self.evaluate_point(r, c, human_sym)
            
            # Tổng điểm = Tấn công + Phòng thủ
            # (Thường phòng thủ quan trọng hơn xíu để không thua nhảm)
            current_score = attack_score + defense_score

            if current_score > best_score:
                best_score = current_score
                best_moves = [(r, c)]
            elif current_score == best_score:
                best_moves.append((r, c))
        
        # Chọn ngẫu nhiên trong các nước đi tốt nhất (để bot đỡ máy móc)
        if best_moves:
            return random.choice(best_moves)
        
        return random.choice(list(possible_moves))

    def get_neighbor_cells(self):
        # Lấy tất cả ô trống có ít nhất 1 quân cờ nằm cạnh (trong phạm vi 2 ô)
        candidates = set()
        for (r, c) in self.board:
            for dr in range(-2, 3):
                for dc in range(-2, 3):
                    if dr == 0 and dc == 0: continue
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < 15 and 0 <= nc < 15 and (nr, nc) not in self.board:
                        candidates.add((nr, nc))
        return candidates

    def evaluate_point(self, r, c, symbol):
        # Hàm tính điểm cho 1 ô dựa trên 4 hướng
        total_score = 0
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
        
        for dr, dc in directions:
            consecutive = 0   # Số quân liên tiếp
            open_ends = 0     # Số đầu thoáng (không bị chặn)
            
            # Duyệt hướng dương
            for i in range(1, 5):
                pos = (r + dr*i, c + dc*i)
                val = self.board.get(pos)
                if val == symbol: consecutive += 1
                elif val is None: # Gặp ô trống
                    if 0 <= pos[0] < 15 and 0 <= pos[1] < 15: open_ends += 1
                    break
                else: break # Gặp quân địch -> bị chặn

            # Duyệt hướng âm
            for i in range(1, 5):
                pos = (r - dr*i, c - dc*i)
                val = self.board.get(pos)
                if val == symbol: consecutive += 1
                elif val is None: 
                    if 0 <= pos[0] < 15 and 0 <= pos[1] < 15: open_ends += 1
                    break
                else: break

            # Bảng điểm (Heuristic Score)
            if consecutive >= 4: total_score += 1000000 # 5 quân -> Thắng chắc
            elif consecutive == 3:
                if open_ends == 2: total_score += 50000 # 4 quân thoáng 2 đầu -> Sắp thắng
                elif open_ends == 1: total_score += 1000 # 4 quân bị chặn 1 đầu
            elif consecutive == 2:
                if open_ends == 2: total_score += 500 # 3 quân thoáng
                elif open_ends == 1: total_score += 100 
            elif consecutive == 1:
                if open_ends == 2: total_score += 10

        return total_score