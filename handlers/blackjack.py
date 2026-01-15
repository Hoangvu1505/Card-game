# handlers/blackjack.py
from server_config import sio, manager, sid_to_room
from games.blackjack import BlackjackGame
from games.tienlen import TienLenGame

async def handle_blackjack_end(sid, game):
    bot_hand, bot_score = game.bot_play()
    p_score = game.players[sid]['score']
    p_status = game.players[sid]['status']
    res = "Hòa"
    if p_status == 'bust': res = "Thua (Bạn Quắc)"
    elif p_status == 'ngu_linh': res = "Thắng (Ngũ Linh)"
    elif bot_score > 21: res = "Thắng (Máy Quắc)"
    elif p_score > bot_score: res = "Thắng"
    elif p_score < bot_score: res = "Thua"
    
    await sio.emit('game_over', {'dealer_hand': bot_hand, 'dealer_score': bot_score, 'result': res, 'is_host_view': True}, room=sid)

@sio.event
async def start_blackjack_pvc(sid):
    room_id = f"PVC_{sid}"
    if room_id not in manager.rooms:
        game = BlackjackGame(room_id, host_sid=None)
        game.add_player(sid, "Bạn") 
        manager.rooms[room_id] = game
    
    game = manager.rooms[room_id]
    sid_to_room[sid] = room_id 
    if game.start_round():
        p = game.players[sid]
        await sio.emit('deal_cards', {
            'hand': p['hand'], 'score': p['score'],
            'dealer_view': [game.bot_dealer_hand[0], "??"] if game.is_pvc else ["??", "??"],
            'is_dealer': False, 'is_host_view': True 
        }, room=sid)

@sio.event
async def action(sid, data):
    room_id = sid_to_room.get(sid)
    if not room_id: return
    game = manager.rooms.get(room_id)
    if isinstance(game, TienLenGame): return 

    act = data.get('act')
    if act == 'hit':
        p_data = game.hit(sid)
        await sio.emit('update_hand', {'hand': p_data['hand'], 'score': p_data['score']}, room=sid)
        if p_data['status'] in ['bust', 'ngu_linh']: await handle_blackjack_end(sid, game)
    elif act == 'stand':
        game.stand(sid)
        await handle_blackjack_end(sid, game)