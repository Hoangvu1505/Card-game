# handlers/tienlen.py
import asyncio
from server_config import sio, manager, sid_to_room, broadcast_room_list
from games.tienlen import TienLenGame

# --- HELPER FUNCTIONS ---
async def broadcast_tlmn_state(game):
    winner = None
    for seat in game.seats:
        if seat and len(seat['hand']) == 0:
            winner = seat['name']
            break
            
    if winner and game.state != "FINISHED":
        game.state = "FINISHED"
        await sio.emit('tlmn_end', {'winner': winner}, room=game.room_id)

    for i in range(4):
        p = game.seats[i]
        if p and p['type'] == 'human':
            client_seats = []
            for offset in range(4):
                seat_idx = (i + offset) % 4
                seat_data = game.seats[seat_idx]
                info = None
                if seat_data:
                    hand_data = seat_data['hand'] if seat_idx == i else len(seat_data['hand'])
                    info = {
                        'sid': seat_data['sid'], 'name': seat_data['name'],
                        'hand': hand_data,
                        'is_turn': (game.turn_index == seat_idx and game.state == "PLAYING"),
                        'is_winner': (seat_data['name'] == winner and game.state == "FINISHED")
                    }
                client_seats.append(info)

            await sio.emit('tlmn_update', {
                'seats': client_seats,
                'last_move': game.last_move['cards'],
                'state': game.state,
                'is_host': (game.host_sid == p['sid'])
            }, room=p['sid'])

async def handle_bot_turns(game):
    while game.state == 'PLAYING':
        curr_p = game.seats[game.turn_index]
        if not curr_p or curr_p['type'] != 'bot': break 
        await asyncio.sleep(1.0)
        move = curr_p['obj'].choose_move(game.last_move)
        if move: game.play_cards(curr_p['sid'], move)
        else: game.pass_turn(curr_p['sid'])
        await broadcast_tlmn_state(game)

# --- EVENTS ---
@sio.event
async def create_tlmn(sid, data):
    mode = data.get('mode') 
    name = data.get('name', 'Player')
    is_bot = (mode == 'bot')
    room_id, err = manager.create_room('tienlen', sid, is_bot, host_name=name)
    if err: return await sio.emit('error', {'msg': err}, room=sid)
    
    sid_to_room[sid] = room_id
    await sio.enter_room(sid, room_id)
    await sio.emit('room_joined', {'room_id': room_id, 'game_type': 'tienlen'}, room=sid)
    
    if not is_bot: await broadcast_room_list()
    await broadcast_tlmn_state(manager.rooms[room_id])

@sio.event
async def join_tlmn(sid, data):
    room_id = data.get('code')
    name = data.get('name', 'Guest')
    success, msg = manager.join_room(room_id, sid, name)
    if success:
        sid_to_room[sid] = room_id
        await sio.enter_room(sid, room_id)
        await sio.emit('room_joined', {'room_id': room_id, 'game_type': 'tienlen'}, room=sid)
        await broadcast_tlmn_state(manager.rooms[room_id])
        await broadcast_room_list()
    else:
        await sio.emit('error', {'msg': msg}, room=sid)

@sio.event
async def tlmn_start_game(sid):
    room_id = sid_to_room.get(sid)
    game = manager.rooms.get(room_id)
    if game and game.host_sid == sid:
        if game.start_game():
            game.state = 'PLAYING' 
            await broadcast_tlmn_state(game)
            if game.is_bot_mode: await handle_bot_turns(game)
        else:
            await sio.emit('error', {'msg': 'Cần ít nhất 2 người chơi!'}, room=sid)

@sio.event
async def tlmn_action(sid, data):
    room_id = sid_to_room.get(sid)
    game = manager.rooms.get(room_id)
    if not game: return

    act = data.get('act')
    if act == 'play':
        success, msg = game.play_cards(sid, data.get('cards'))
        if not success: return await sio.emit('error', {'msg': msg}, room=sid)
    elif act == 'pass':
        game.pass_turn(sid)
    elif act == 'leave':
        from handlers.general import disconnect
        await disconnect(sid)
        await sio.emit('left_room', {}, room=sid)
        return

    await broadcast_tlmn_state(game)
    if game.is_bot_mode and game.state == 'PLAYING':
        await handle_bot_turns(game)