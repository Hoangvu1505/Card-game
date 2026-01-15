# handlers/caro.py
import asyncio
from server_config import sio, manager, sid_to_room, broadcast_room_list
from games.caro import CaroGame

async def broadcast_caro_state(game):
    player_names = {'X': 'Đang chờ...', 'O': 'Đang chờ...'}
    for p_data in game.players.values():
        player_names[p_data['symbol']] = p_data['name']

    info = {
        'board': list(game.board.items()),
        'turn': game.turn,
        'winner': game.winner,
        'names': player_names,
        'players': {k: v for k, v in game.players.items() if k != 'BOT' or True},
        'last_move': game.last_move
    }
    await sio.emit('caro_update', info, room=game.room_id)

@sio.event
async def create_caro(sid, data):
    mode = data.get('mode') 
    name = data.get('name', 'Player')
    is_bot = (mode == 'bot')
    room_id = f"C-{sid[:4]}".upper()
    
    game = CaroGame(room_id, host_sid=sid)
    game.is_bot_mode = is_bot
    game.host_name = name 
    
    game.add_player(sid, name)
    if is_bot:
        game.players['BOT'] = {'name': 'Máy Siêu Cấp', 'symbol': 'O'}
    
    manager.rooms[room_id] = game 
    sid_to_room[sid] = room_id
    
    await sio.enter_room(sid, room_id)
    await sio.emit('room_joined', {'room_id': room_id, 'game_type': 'caro'}, room=sid)
    
    if not is_bot: await broadcast_room_list()
    await broadcast_caro_state(game)

@sio.event
async def join_caro(sid, data):
    room_id = data.get('code')
    name = data.get('name', 'Guest')
    game = manager.rooms.get(room_id)
    
    if game and isinstance(game, CaroGame) and game.state == 'WAITING':
        game.add_player(sid, name)
        sid_to_room[sid] = room_id
        await sio.enter_room(sid, room_id)
        await sio.emit('room_joined', {'room_id': room_id, 'game_type': 'caro'}, room=sid)
        await broadcast_caro_state(game)
        await broadcast_room_list()
    else:
        await sio.emit('error', {'msg': 'Phòng không tồn tại hoặc đã đầy!'}, room=sid)

@sio.event
async def caro_move(sid, data):
    room_id = sid_to_room.get(sid)
    game = manager.rooms.get(room_id)
    if not game or not isinstance(game, CaroGame): return

    row, col = data.get('r'), data.get('c')
    success, msg = game.make_move(sid, row, col)
    
    if success:
        await broadcast_caro_state(game)
        if game.is_bot_mode and game.state == 'PLAYING' and game.turn == 'O':
            await asyncio.sleep(0.5)
            move = game.bot_move()
            if move:
                game.make_move('BOT', move[0], move[1])
                await broadcast_caro_state(game)

@sio.event
async def caro_restart(sid):
    room_id = sid_to_room.get(sid)
    game = manager.rooms.get(room_id)
    if game and isinstance(game, CaroGame):
        game.reset_game()
        await broadcast_caro_state(game)

@sio.event
async def caro_leave(sid):
    # Logic thoát đã được xử lý ở hàm disconnect bên general.py
    # Ở đây chỉ cần gọi disconnect thủ công và báo về client
    from handlers.general import disconnect
    await disconnect(sid) 
    await sio.emit('left_room', {}, room=sid)