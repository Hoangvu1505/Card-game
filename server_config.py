# server_config.py
import socketio
from room_manager import RoomManager
from user_manager import UserManager

# 1. Khởi tạo Server Socket.IO
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
manager = RoomManager()
user_manager = UserManager() # <--- Khởi tạo biến dùng chung
sid_to_room = {} # Map: sid -> room_id

# 2. Hàm dùng chung: Gửi danh sách phòng
async def broadcast_room_list():
    rooms = []
    for r_id, game in manager.rooms.items():
        if getattr(game, 'state', '') != 'WAITING': continue
        if getattr(game, 'is_bot_mode', False): continue
            
        count = 0
        max_p = 0
        host_name = "Ẩn danh"

        # Game Tiến Lên
        if hasattr(game, 'seats'): 
            count = len([s for s in game.seats if s])
            max_p = 4
            if hasattr(game, 'host_sid'):
                for seat in game.seats:
                    if seat and seat['sid'] == game.host_sid:
                        host_name = seat['name']
                        break
        
        # Game Caro
        elif hasattr(game, 'players'):
            count = len(game.players)
            max_p = 2
            host_name = getattr(game, 'host_name', 'Player')

        rooms.append({
            'id': r_id,
            'players': f"{count}/{max_p}",
            'host': host_name
        })

    print(f"📡 Danh sách phòng: {rooms}") 
    await sio.emit('room_list_update', rooms)