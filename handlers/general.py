# handlers/general.py
import random
from server_config import sio, manager, sid_to_room, broadcast_room_list, user_manager
from games.tienlen import TienLenGame

# Cấu hình giải thưởng
PRIZES = [
    {"label": "100 $",   "value": 100,   "weight": 30},
    {"label": "500 $",   "value": 500,   "weight": 25},
    {"label": "1.000 $", "value": 1000,  "weight": 20},
    {"label": "Mất lượt", "value": 0,    "weight": 10},
    {"label": "2.000 $", "value": 2000,  "weight": 10},
    {"label": "5.000 $", "value": 5000,  "weight": 4},
    {"label": "10.000 $", "value": 10000, "weight": 1}
]

# --- XỬ LÝ ĐĂNG KÝ / ĐĂNG NHẬP ---
@sio.event
async def auth_register(sid, data):
    username = data.get('username')
    password = data.get('password')
    
    success, msg = user_manager.register(username, password)
    if success:
        await sio.emit('auth_response', {'success': True, 'msg': msg, 'username': username}, room=sid)
    else:
        await sio.emit('auth_response', {'success': False, 'msg': msg}, room=sid)

@sio.event
async def auth_login(sid, data):
    username = data.get('username')
    password = data.get('password')
    
    success, msg = user_manager.login(username, password)
    if success:
        # Lưu thông tin user vào session hoặc biến map nếu cần thiết (ở đây ta gửi về client tự lưu)
        await sio.emit('auth_response', {'success': True, 'msg': msg, 'username': username}, room=sid)
    else:
        await sio.emit('auth_response', {'success': False, 'msg': msg}, room=sid)

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
                if isinstance(game, TienLenGame):
                    from handlers.tienlen import broadcast_tlmn_state
                    await broadcast_tlmn_state(game)
            await broadcast_room_list()
        if sid in sid_to_room: del sid_to_room[sid]

@sio.event
async def send_chat(sid, data):
    room_id = sid_to_room.get(sid)
    if room_id:
        await sio.emit('chat_received', {
            'sender_sid': sid, 'content': data.get('content'), 'type': data.get('type')
        }, room=room_id)

# --- LOGIC TIỀN & BXH & VÒNG QUAY ---
@sio.event
async def get_my_money(sid, data):
    name = data.get('name')
    if name:
        user_data = user_manager.get_user_data(name)
        await sio.emit('money_update', {'money': user_data['money'], 'spins': user_data['spins']}, room=sid)

@sio.event
async def get_leaderboard(sid):
    top_users = user_manager.get_top_users()
    await sio.emit('leaderboard_data', top_users, room=sid)

@sio.event
async def spin_wheel(sid, data):
    name = data.get('name')
    can_spin, remaining = user_manager.use_spin(name)
    if not can_spin:
        await sio.emit('error', {'msg': 'Hết lượt quay hôm nay!'}, room=sid)
        return

    items = [p for p in PRIZES]
    weights = [p['weight'] for p in PRIZES]
    result_prize = random.choices(items, weights=weights, k=1)[0]
    result_index = PRIZES.index(result_prize)
    new_money = user_manager.update_money(name, result_prize['value'])

    await sio.emit('spin_result', {
        'index': result_index, 'prize': result_prize,
        'new_money': new_money, 'remaining_spins': remaining
    }, room=sid)