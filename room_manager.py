import random
import string

class RoomManager:
    def __init__(self):
        self.rooms = {}

    def get_public_rooms(self):
        rooms = []
        for r_id, game in self.rooms.items():
            count = 0
            max_p = 0
            host_name = getattr(game, 'host_name', 'Ẩn danh')
            
            if hasattr(game, 'seats'): # Tiến Lên
                count = len([s for s in game.seats if s])
                max_p = 4
            elif hasattr(game, 'players'): # Caro
                count = len(game.players)
                max_p = 2
            
            status_text = "Chờ"
            game_state = getattr(game, 'state', 'WAITING')
            
            if count >= max_p: status_text = "Full"
            elif game_state == 'PLAYING': status_text = "Đang chơi"
            
            display_str = f"{count}/{max_p} ({status_text})"

            rooms.append({
                'id': r_id, 
                'players': display_str, 
                'host': host_name,
                'game_type': 'caro' if r_id.startswith('C-') else 'tienlen'
            })
        return rooms

    def remove_player(self, sid, room_id):
        leaver_name = "Khách"
        
        if room_id in self.rooms:
            game = self.rooms[room_id]
            is_host = False
            found = False
            
            # 1. Xác định chủ phòng
            if hasattr(game, 'host_sid') and game.host_sid == sid:
                is_host = True
            
            # 2. Xóa người chơi & Lấy tên
            if hasattr(game, 'players') and isinstance(game.players, dict): # Caro
                if sid in game.players: 
                    leaver_name = game.players[sid].get('name', 'Khách')
                    del game.players[sid]
                    found = True
            elif hasattr(game, 'seats'): # Tiến Lên
                for i in range(len(game.seats)):
                    if game.seats[i] and game.seats[i]['sid'] == sid:
                        leaver_name = game.seats[i]['name']
                        game.seats[i] = None
                        found = True
                        break
            
            # Nếu không tìm thấy người chơi thì báo lỗi
            if not found: return "NOT_FOUND", None

            # 3. QUYẾT ĐỊNH SỐ PHẬN PHÒNG (GỘP GỌN)
            count = 0
            if hasattr(game, 'players'): count = len(game.players)
            elif hasattr(game, 'seats'): count = len([s for s in game.seats if s])

            # Nếu là Chủ phòng thoát HOẶC Phòng trống -> XÓA LUÔN
            if is_host or count == 0:
                del self.rooms[room_id]
                return "DESTROYED", leaver_name

            # Nếu là Khách thoát -> RESET GAME
            else:
                # Cách 1: Gọi hàm reset_game (Tiến lên dùng cái này)
                if hasattr(game, 'reset_game'):
                    game.reset_game()
                
                # Cách 2: Reset thủ công (Caro dùng cái này nếu chưa có hàm reset_game)
                elif hasattr(game, 'board'):
                    game.state = 'WAITING'
                    game.board = {}      # Xóa bàn cờ
                    game.turn = 'X'      # Reset lượt
                    game.winner = None
                    game.last_move = None
                
                return "LEFT", leaver_name
            
        return "NOT_FOUND", None