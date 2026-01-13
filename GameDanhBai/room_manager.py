import random
import string
from games.tienlen import TienLenGame
from games.blackjack import BlackjackGame

class RoomManager:
    def __init__(self):
        self.rooms = {} 
        self.max_rooms = 10

    def get_public_rooms(self):
        data = []
        for rid, game in self.rooms.items():
            # Chỉ hiện phòng Multiplayer Tienlen
            if isinstance(game, TienLenGame) and not game.is_bot_mode:
                # Đếm số người hiện tại
                count = len([s for s in game.seats if s])
                host_name = game.seats[0]['name'] if game.seats[0] else "Unknown"
                data.append({'id': rid, 'players': f"{count}/4", 'host': host_name})
        return data

    def generate_room_id(self):
        while True:
            room_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
            if room_id not in self.rooms: return room_id

    # --- FIX: Thêm tham số host_name ---
    def create_room(self, game_type, host_sid, is_bot=False, host_name="Player"):
        if len(self.rooms) >= self.max_rooms and not is_bot:
            return None, "Server quá tải."
        
        room_id = self.generate_room_id()
        if is_bot: room_id = f"BOT_{host_sid}"

        if game_type == 'tienlen':
            # Truyền host_name vào đây
            self.rooms[room_id] = TienLenGame(room_id, host_sid, is_bot_mode=is_bot, host_name=host_name)
            if not is_bot:
                # Add chính chủ phòng vào ghế
                self.rooms[room_id].add_player(host_sid, host_name)
        
        return room_id, None

    def join_room(self, room_id, sid, name):
        if room_id not in self.rooms: return False, "Phòng không tồn tại"
        game = self.rooms[room_id]
        
        # Kiểm tra đúng loại game
        if isinstance(game, TienLenGame):
            return game.add_player(sid, name)
        
        return False, "Không thể tham gia"

    def remove_player(self, sid, room_id):
        if room_id in self.rooms:
            game = self.rooms[room_id]
            
            # Nếu là Blackjack PvC
            if isinstance(game, BlackjackGame):
                del self.rooms[room_id]
                return "LEFT"

            # Nếu là Tienlen
            if isinstance(game, TienLenGame):
                # Nếu chủ phòng online thoát -> Hủy phòng
                if not game.is_bot_mode and sid == game.host_sid:
                    del self.rooms[room_id]
                    return "DESTROYED"
                
                game.remove_player(sid)
                
                # Nếu phòng trống -> Xóa
                if not any(game.seats):
                    del self.rooms[room_id]
                    return "DESTROYED"
                    
            return "LEFT"
        return "ERROR"