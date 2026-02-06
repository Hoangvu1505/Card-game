import asyncio
import random
import string
from server_config import sio, manager, sid_to_room, broadcast_room_list, user_manager
from games.tienlen import TienLenGame

# --- CẤU HÌNH TIỀN CƯỢC ---
BET_AMOUNT = 1000 # Mức cược cơ bản

# --- HELPER FUNCTIONS ---
async def broadcast_tlmn_state(game):
    winner = None
    for seat in game.seats:
        if seat and len(seat['hand']) == 0:
            winner = seat['name']
            break
            
    if winner and game.state != "FINISHED":
        game.state = "FINISHED"
        
        # --- TÍNH TIỀN KẾT THÚC (LUẬT CHÁY BÀI) ---
        total_lost = 0
        for seat in game.seats:
            if not seat or seat['name'] == winner: continue
            
            # Người thua (Cháy bài) -> Mất gấp 3 lần cược
            # "Cháy bài sẽ mất gấp ba tiền cược cho người thắng"
            lost_amount = BET_AMOUNT * 3
            
            # Trừ tiền người thua
            if seat['type'] == 'human':
                new_money = user_manager.update_money(seat['name'], -lost_amount)
                await sio.emit('money_update', {'money': new_money}, room=seat['sid'])
            
            total_lost += lost_amount
        
        # Cộng tiền người thắng (Ăn tất cả)
        for seat in game.seats:
            if seat and seat['name'] == winner:
                if seat['type'] == 'human':
                    new_money = user_manager.update_money(seat['name'], total_lost)
                    await sio.emit('money_update', {'money': new_money}, room=seat['sid'])
                break

        await sio.emit('tlmn_end', {'winner': winner}, room=game.room_id)

    # Gửi update bàn chơi
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
        await asyncio.sleep(1.5)
        
        move = game.get_bot_move(game.turn_index)
        if move: 
            # Bot đánh bài cũng phải check chặt
            # Nhưng để đơn giản, ta gọi hàm xử lý chung ở dưới
             await process_move(game, game.turn_index, move)
        else:
            game.pass_turn(game.turn_index)
            
        await broadcast_tlmn_state(game)
        if game.state == 'FINISHED': break

# --- HÀM XỬ LÝ ĐÁNH BÀI (Dùng chung cho người và bot để tính tiền) ---
async def process_move(game, player_idx, cards):
    # Lưu lại người bị chặt (là người đánh last_move)
    victim_sid = game.last_move['sid']
    
    success, result = game.play_cards(player_idx, cards)
    
    if success and result not in ["OK", "WIN"]:
        # Có sự kiện Chặt -> Tính tiền ngay
        cutter = game.seats[player_idx]
        victim = None
        
        # Tìm thông tin người bị chặt
        for s in game.seats:
            if s and s['sid'] == victim_sid:
                victim = s
                break
        
        if cutter and victim:
            fine = 0
            msg = ""
            
            if result == "CHOP_PIG_BLACK":
                fine = BET_AMOUNT
                msg = "Chặt Heo Đen! (-1 cược)"
            elif result == "CHOP_PIG_RED":
                fine = BET_AMOUNT # User yêu cầu: heo đỏ = 3 đôi thông = tứ quý?
                # "heo đỏ bằng 3 đôi thông hay tứ quý" -> Logic hơi lạ, thường heo đỏ đắt hơn.
                # Nhưng user nói: "mất tiền cược... nếu bị chặt heo đen, heo đỏ bằng 3 đôi thông hay tứ quý"
                # Có thể hiểu là: Bị chặt [Heo Đen/Đỏ] BỞI [3 đôi thông/Tứ quý].
                # Thôi ta làm theo luật phổ biến + yêu cầu user:
                # Heo đỏ = 2 lần cược (Gấp đôi heo đen)
                fine = BET_AMOUNT * 2
                msg = "Chặt Heo Đỏ! (-2 cược)"
            elif result == "CHOP_PAIR_PIG":
                # "Gấp đôi cho đôi heo" (tức là gấp đôi tiền phạt heo thường? hay gấp đôi cược?)
                # Thường đôi heo = Heo đen + Heo đỏ.
                # User: "gấp đôi cho đôi heo (bị chặt bởi tứ quý và bốn đôi thông)"
                fine = BET_AMOUNT * 4 # Phạt nặng
                msg = "Chặt Đôi Heo! (-4 cược)"
            elif result == "CHOP_OVER":
                # "Chặt đè thì người bị chặt sẽ mất gấp bốn tiền cược"
                fine = BET_AMOUNT * 4
                msg = "Chặt chồng! (-4 cược)"
            
            # Thực hiện chuyển tiền
            # Trừ người bị chặt
            if victim['type'] == 'human':
                new_m = user_manager.update_money(victim['name'], -fine)
                await sio.emit('money_update', {'money': new_m}, room=victim['sid'])
                await sio.emit('error', {'msg': f"Bạn bị {msg}"}, room=victim['sid'])
                
            # Cộng người chặt
            if cutter['type'] == 'human':
                new_m = user_manager.update_money(cutter['name'], fine)
                await sio.emit('money_update', {'money': new_m}, room=cutter['sid'])
                await sio.emit('error', {'msg': f"Bạn {msg} (+{fine})"}, room=cutter['sid'])

    return success, result

# --- EVENTS ---
@sio.event
async def create_tlmn(sid, data):
    mode = data.get('mode') 
    name = data.get('name', 'Player')
    
    room_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    game = TienLenGame(room_id, host_sid=sid, is_bot_mode=(mode == 'bot'), host_name=name)
    
    if not game.is_bot_mode: game.add_player(sid, name)
    if game.is_bot_mode: 
        game.start_game()
        
    manager.rooms[room_id] = game
    sid_to_room[sid] = room_id
    await sio.enter_room(sid, room_id)
    await sio.emit('room_joined', {'room_id': room_id, 'game_type': 'tienlen'}, room=sid)
    
    if not game.is_bot_mode: await broadcast_room_list()
    await broadcast_tlmn_state(game)
    if game.is_bot_mode: asyncio.create_task(handle_bot_turns(game))

@sio.event
async def join_tlmn(sid, data):
    room_id = data.get('code')
    name = data.get('name', 'Guest')
    game = manager.rooms.get(room_id)
    
    if game and isinstance(game, TienLenGame):
        if game.state == 'WAITING':
            if game.add_player(sid, name):
                sid_to_room[sid] = room_id
                await sio.enter_room(sid, room_id)
                await sio.emit('room_joined', {'room_id': room_id, 'game_type': 'tienlen'}, room=sid)
                await broadcast_tlmn_state(game)
                await broadcast_room_list()
            else: await sio.emit('error', {'msg': 'Phòng Full!'}, room=sid)
        else: await sio.emit('error', {'msg': 'Đang chơi!'}, room=sid)
    else: await sio.emit('error', {'msg': 'Sai mã phòng!'}, room=sid)

@sio.event
async def tlmn_start_game(sid):
    room_id = sid_to_room.get(sid)
    game = manager.rooms.get(room_id)
    if game and game.host_sid == sid:
        if game.start_game(): 
            await broadcast_tlmn_state(game)
            await broadcast_room_list()
            if game.is_bot_mode: asyncio.create_task(handle_bot_turns(game))
        else: await sio.emit('error', {'msg': 'Thiếu người!'}, room=sid)

@sio.event
async def tlmn_action(sid, data):
    room_id = sid_to_room.get(sid)
    game = manager.rooms.get(room_id)
    if not game: return
    act = data.get('act')

    if act == 'leave':
        from handlers.general import disconnect
        await disconnect(sid)
        await sio.emit('left_room', {}, room=sid)
        return

    player_idx = -1
    for i in range(4):
        if game.seats[i] and game.seats[i]['sid'] == sid:
            player_idx = i
            break
            
    if player_idx == -1 or game.turn_index != player_idx:
        return await sio.emit('error', {'msg': 'Chưa đến lượt!'}, room=sid)

    
    if act == 'play':
        # Gọi hàm process_move thay vì game.play_cards trực tiếp để tính tiền
        success, msg = await process_move(game, player_idx, data.get('cards'))
        if not success: return await sio.emit('error', {'msg': msg}, room=sid)
        
    elif act == 'pass':
        game.pass_turn(player_idx)


    await broadcast_tlmn_state(game)
    if game.is_bot_mode and game.state == 'PLAYING':
        await handle_bot_turns(game)