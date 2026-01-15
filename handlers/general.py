# handlers/general.py
from server_config import sio, manager, sid_to_room, broadcast_room_list
from games.tienlen import TienLenGame

# Cần import broadcast_tlmn_state để cập nhật khi có người thoát
# (Để tránh import vòng tròn, ta sẽ import bên trong hàm nếu cần, hoặc cấu trúc lại kỹ hơn.
# Ở mức độ đơn giản, ta sẽ chấp nhận import cục bộ trong hàm disconnect)

@sio.event
async def connect(sid, environ):
    print(f"Client {sid} connected")
    await sio.emit('room_list_update', manager.get_public_rooms(), room=sid)

@sio.event
async def disconnect(sid):
    if sid in sid_to_room:
        room_id = sid_to_room[sid]
        status = manager.remove_player(sid, room_id)
        
        if status == "DESTROYED":
            await sio.emit('force_leave', {'msg': 'Phòng đã giải tán.'}, room=room_id)
            await broadcast_room_list()
        elif status == "LEFT":
            if room_id in manager.rooms:
                game = manager.rooms[room_id]
                # Nếu là game tiến lên, cập nhật lại bàn cho người ở lại
                if isinstance(game, TienLenGame):
                    from handlers.tienlen import broadcast_tlmn_state
                    await broadcast_tlmn_state(game)
            await broadcast_room_list()
        
        if sid in sid_to_room:
            del sid_to_room[sid]

@sio.event
async def send_chat(sid, data):
    room_id = sid_to_room.get(sid)
    if room_id:
        await sio.emit('chat_received', {
            'sender_sid': sid, 
            'content': data.get('content'), 
            'type': data.get('type')
        }, room=room_id)
    else:
        print(f"❌ Chat lỗi: {sid} chưa vào phòng nào.")