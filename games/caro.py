import random
import time

class CaroGame:
    def __init__(self, room_id, host_sid=None):
        self.room_id = room_id
        self.host_sid = host_sid
        self.host_name = "Chủ phòng"
        self.players = {}
        self.board = {} 
        self.turn = 'X' 
        self.state = 'WAITING'
        self.winner = None
        self.is_bot_mode = False
        self.last_move = None

        # Giữ Depth = 3 để đảm bảo tốc độ, nhưng sẽ tăng độ thông minh bằng Heuristic xịn
        self.search_depth = 3

    def add_player(self, sid, name):
        if len(self.players) >= 2: return False
        symbol = 'X' if len(self.players) == 0 else 'O'
        self.players[sid] = {'name': name, 'symbol': symbol}
        if len(self.players) == 2 or self.is_bot_mode:
            self.state = 'PLAYING'
        return True

    def make_move(self, sid, row, col):
        if self.state != 'PLAYING' or self.winner: return False, "Game đã dừng"
        if sid != 'BOT' and sid not in self.players: return False, "Lỗi xác thực"
        
        symbol = self.players[sid]['symbol'] if sid != 'BOT' else 'O'
        if symbol != self.turn: return False, "Chưa đến lượt"

        if (row, col) in self.board: return False, "Ô đã đánh"

        self.board[(row, col)] = symbol
        self.last_move = (row, col)
        
        if self.check_win(row, col, symbol):
            self.winner = symbol
            self.state = 'FINISHED'
        else:
            self.turn = 'O' if self.turn == 'X' else 'X'
            
        return True, "OK"

    def check_win(self, r, c, symbol):
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
        for dr, dc in directions:
            count = 1
            for i in range(1, 5):
                if self.board.get((r + dr*i, c + dc*i)) == symbol: count += 1
                else: break
            for i in range(1, 5):
                if self.board.get((r - dr*i, c - dc*i)) == symbol: count += 1
                else: break
            if count >= 5: return True
        return False

    def reset_game(self):
        """Đưa game về trạng thái chờ, xóa bàn cờ"""
        self.state = "WAITING"
        self.board = {}      # Xóa bàn cờ
        self.turn = 'X'      # Reset lượt về X
        self.winner = None
        self.last_move = None

    # ----------------------------------------------------------------
    # --- BOT LOGIC: DEFENSIVE & AGGRESSIVE ---
    # ----------------------------------------------------------------
    
    def bot_move(self):
        if not self.board: return 7, 7

        possible_moves = self.get_neighbor_cells()
        if not possible_moves: return 7, 7

        # 1. BƯỚC THỦ KHẨN CẤP (QUAN TRỌNG NHẤT)
        # Kiểm tra xem có cần chặn ngay lập tức không (trước khi tính Minimax)
        urgent_move = self.check_urgent_defense()
        if urgent_move: 
            print(f"🛡️ Bot chặn nguy hiểm tại: {urgent_move}")
            return urgent_move

        # 2. MINIMAX (Tính toán nước đi tốt nhất)
        best_score = -float('inf')
        best_move = None
        alpha = -float('inf')
        beta = float('inf')

        # Sắp xếp nước đi để cắt nhánh nhanh hơn
        ranked_moves = self.rank_moves(possible_moves, 'O')

        for (r, c) in ranked_moves:
            self.board[(r, c)] = 'O'
            
            # Bot tìm nước đi max, đối thủ (người) sẽ tìm nước min
            score = self.minimax(self.search_depth - 1, False, alpha, beta)
            
            self.board.pop((r, c))

            if score > best_score:
                best_score = score
                best_move = (r, c)
            
            alpha = max(alpha, score)
            if beta <= alpha: break

        return best_move if best_move else random.choice(possible_moves)

    def minimax(self, depth, is_bot_turn, alpha, beta):
        if depth == 0: return self.evaluate_board()
        
        moves = self.get_neighbor_cells()
        if not moves: return self.evaluate_board()

        # Lấy Top 10 nước đi để tính cho nhanh
        # moves = self.rank_moves(moves, 'O' if is_bot_turn else 'X')[:10]

        if is_bot_turn: # Lượt Bot (O) -> Muốn điểm cao nhất
            max_eval = -float('inf')
            for (r, c) in moves:
                self.board[(r, c)] = 'O'
                if self.check_win_simulation(r, c, 'O'):
                    self.board.pop((r, c))
                    return 10000000 # Thắng là ưu tiên số 1
                
                eval_score = self.minimax(depth - 1, False, alpha, beta)
                self.board.pop((r, c))
                
                max_eval = max(max_eval, eval_score)
                alpha = max(alpha, eval_score)
                if beta <= alpha: break 
            return max_eval

        else: # Lượt Người (X) -> Bot giả định người sẽ đánh nước tệ nhất cho Bot (điểm thấp nhất)
            min_eval = float('inf')
            for (r, c) in moves:
                self.board[(r, c)] = 'X'
                if self.check_win_simulation(r, c, 'X'):
                    self.board.pop((r, c))
                    return -10000000 # Người thắng là thảm họa
                
                eval_score = self.minimax(depth - 1, True, alpha, beta)
                self.board.pop((r, c))
                
                min_eval = min(min_eval, eval_score)
                beta = min(beta, eval_score)
                if beta <= alpha: break
            return min_eval

    def get_neighbor_cells(self):
        candidates = set()
        for (r, c) in self.board:
            for dr in range(-1, 2):
                for dc in range(-1, 2):
                    if dr == 0 and dc == 0: continue
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < 15 and 0 <= nc < 15 and (nr, nc) not in self.board:
                        candidates.add((nr, nc))
        return list(candidates)

    def rank_moves(self, moves, player_symbol):
        scores = []
        for (r, c) in moves:
            # Điểm = Tấn công + Phòng thủ (Ưu tiên phòng thủ hơn một chút)
            score = self.evaluate_point(r, c, player_symbol) * 1.0 
            score += self.evaluate_point(r, c, 'X' if player_symbol == 'O' else 'O') * 1.2
            scores.append(((r, c), score))
        scores.sort(key=lambda x: x[1], reverse=True)
        return [x[0] for x in scores[:15]] # Lấy top 15 nước ngon nhất

    def check_urgent_defense(self):
        # Hàm này chạy riêng để bắt các trường hợp nguy hiểm KHÔNG THỂ BỎ QUA
        candidates = self.get_neighbor_cells()
        
        # 1. Ưu tiên thắng (nếu Bot có 4 con)
        for (r, c) in candidates:
            if self.evaluate_point(r, c, 'O') >= 50000: return (r, c)
            
        # 2. Chặn thua (nếu Người có 3 thoáng hoặc 4 bị chặn)
        # Điểm nguy hiểm > 2000 nghĩa là: 3 thoáng (3000) hoặc 4 chặn (2500)
        for (r, c) in candidates:
            if self.evaluate_point(r, c, 'X') >= 2000: return (r, c)
            
        return None

    def evaluate_board(self):
        score_o = 0
        score_x = 0
        for (r,c), val in self.board.items():
            if val == 'O': score_o += self.evaluate_point_static(r, c, 'O')
            else: score_x += self.evaluate_point_static(r, c, 'X')
        return score_o - score_x

    def evaluate_point(self, r, c, symbol):
        return self.check_sequences(r, c, symbol)

    def evaluate_point_static(self, r, c, symbol):
        return self.check_sequences(r, c, symbol, is_static=True)

    def check_sequences(self, r, c, symbol, is_static=False):
        total = 0
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
        
        for dr, dc in directions:
            consecutive = 0
            if is_static: consecutive = 1
            blocks = 0
            
            # Check hướng dương
            for i in range(1, 5):
                pos = (r + dr*i, c + dc*i)
                val = self.board.get(pos)
                if val == symbol: consecutive += 1
                elif val is None: break
                else: 
                    blocks += 1
                    break
            # Check hướng âm
            for i in range(1, 5):
                pos = (r - dr*i, c - dc*i)
                val = self.board.get(pos)
                if val == symbol: consecutive += 1
                elif val is None: break
                else: 
                    blocks += 1
                    break
            
            # --- BẢNG ĐIỂM HEURISTIC (ĐÃ NÂNG CẤP) ---
            # 5 con -> Thắng tuyệt đối
            if consecutive >= 5: total += 10000000 
            
            # 4 con
            elif consecutive == 4:
                if blocks == 0: total += 100000 # 4 thoáng -> Thắng ngay
                else: total += 2500 # 4 bị chặn -> Nguy hiểm cấp cao
            
            # 3 con
            elif consecutive == 3:
                if blocks == 0: total += 3000 # 3 thoáng -> Nguy hiểm (Bot phải chặn ngay)
                else: total += 150 # 3 bị chặn -> Bình thường
            
            # 2 con
            elif consecutive == 2:
                if blocks == 0: total += 50
                else: total += 10
                
        return total

    def check_win_simulation(self, r, c, symbol):
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
        for dr, dc in directions:
            count = 1
            for i in range(1, 5):
                if self.board.get((r + dr*i, c + dc*i)) == symbol: count += 1
                else: break
            for i in range(1, 5):
                if self.board.get((r - dr*i, c - dc*i)) == symbol: count += 1
                else: break
            if count >= 5: return True
        return False