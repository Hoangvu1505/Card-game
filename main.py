import socketio
import uvicorn
import asyncio 
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from room_manager import RoomManager

# Import các class Game
from games.tienlen import TienLenGame
from games.blackjack import BlackjackGame
from games.caro import CaroGame #mới

sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
app = FastAPI()
sio_app = socketio.ASGIApp(sio, app)

manager = RoomManager()
sid_to_room = {}

@app.get("/")
async def get():
    with open("templates/index.html", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

async def broadcast_room_list():
    # Tự quét danh sách phòng thay vì dùng manager.get_public_rooms()
    # để kiểm soát dữ liệu chính xác cho cả Caro và Tiến Lên
    rooms = []
    
    for r_id, game in manager.rooms.items():
        # 1. Chỉ hiện phòng đang CHỜ (WAITING)
        if getattr(game, 'state', '') != 'WAITING': continue
        
        # 2. Không hiện phòng chơi với BOT
        if getattr(game, 'is_bot_mode', False): continue
            
        # KHAI BÁO BIẾN TẠM
        count = 0
        max_p = 0
        host_name = "Ẩn danh"

        # --- TRƯỜNG HỢP 1: GAME TIẾN LÊN (Dùng seats) ---
        if hasattr(game, 'seats'): 
            # Đếm số ghế có người ngồi
            count = len([s for s in game.seats if s])
            max_p = 4
            
            # Tìm tên chủ phòng (dựa vào host_sid)
            if hasattr(game, 'host_sid'):
                for seat in game.seats:
                    if seat and seat['sid'] == game.host_sid:
                        host_name = seat['name']
                        break
        
        # --- TRƯỜNG HỢP 2: GAME CARO (Dùng players) ---
        elif hasattr(game, 'players'):
            count = len(game.players)
            max_p = 2
            # Caro lưu trực tiếp host_name (do mình gán lúc tạo)
            host_name = getattr(game, 'host_name', 'Player')

        # 3. Đóng gói dữ liệu
        rooms.append({
            'id': r_id,
            'players': f"{count}/{max_p}", # Ví dụ: "1/4" hoặc "1/2"
            'host': host_name
        })

    # Gửi danh sách về Client
    print(f"📡 Danh sách phòng: {rooms}") 
    await sio.emit('room_list_update', rooms)

async def handle_game_end(game, winner_name):
    # Đánh dấu game đã kết thúc
    game.state = "FINISHED"
    print(f"Game {game.room_id} ENDED. Winner: {winner_name}")
    
    # Quan trọng: Gửi sự kiện thắng
    await sio.emit('tlmn_end', {'winner': winner_name}, room=game.room_id)

# --- SỰ KIỆN KẾT NỐI ---
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
                if isinstance(game, TienLenGame): await broadcast_tlmn_state(game)
            await broadcast_room_list()
        del sid_to_room[sid]

# --- BLACKJACK ---
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

# --- TIEN LEN ---
@sio.event
async def create_tlmn(sid, data):
    mode = data.get('mode') 
    name = data.get('name', 'Player')
    is_bot = (mode == 'bot')
    
    room_id, err = manager.create_room('tienlen', sid, is_bot, host_name=name)
    if err: return await sio.emit('error', {'msg': err}, room=sid)
    
    sid_to_room[sid] = room_id
    #fix here
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
        #fix here
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
            # --- FIX LỖI: Cưỡng chế chuyển trạng thái sang ĐANG CHƠI ---
            game.state = 'PLAYING' 
            # (Nếu thiếu dòng này, game có thể vẫn lưu trạng thái FINISHED của ván trước
            # khiến nút Chơi lại không chịu biến mất)
            # -----------------------------------------------------------

            # 1. Cập nhật giao diện bàn cờ cho người chơi
            await broadcast_tlmn_state(game)

            # 2. Nếu là chế độ chơi với Bot, kích hoạt Bot
            if game.is_bot_mode:
                await handle_bot_turns(game)
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
        if not success: 
            await sio.emit('error', {'msg': msg}, room=sid)
            return
        
        # --- FIX: Xóa đoạn tự set state = FINISHED ở đây để tránh xung đột logic ---
        
    elif act == 'pass':
        game.pass_turn(sid)
    elif act == 'leave':
        await disconnect(sid)
        await sio.emit('left_room', {}, room=sid)
        return

    # Cập nhật bàn cờ -> Kiểm tra thắng thua sẽ nằm trong hàm broadcast này
    await broadcast_tlmn_state(game)

    # Bot đánh
    if game.is_bot_mode and game.state == 'PLAYING':
        await handle_bot_turns(game)
@sio.event
async def send_chat(sid, data):
    room_id = sid_to_room.get(sid)
    if room_id:
        # Gửi tin nhắn kèm theo ID người gửi (sid) để client biết ai đang nói
        await sio.emit('chat_received', {
            'sender_sid': sid, 
            'content': data.get('content'), 
            'type': data.get('type') # 'text' hoặc 'image'
        }, room=room_id)
    else:
        print("   ❌ LỖI: Không tìm thấy phòng của người này (Server mất trí nhớ hoặc chưa join)")

async def handle_bot_turns(game):
    while game.state == 'PLAYING':
        curr_p = game.seats[game.turn_index]
        if not curr_p or curr_p['type'] != 'bot': break 
        
        await asyncio.sleep(1.0)
        move = curr_p['obj'].choose_move(game.last_move)
        
        if move: game.play_cards(curr_p['sid'], move)
        else: game.pass_turn(curr_p['sid'])
            
        await broadcast_tlmn_state(game)

# --- CORE LOGIC: Cập nhật và Check Thắng ---
async def broadcast_tlmn_state(game):
    # 1. KIỂM TRA THẮNG THUA TỰ ĐỘNG
    winner = None
    for seat in game.seats:
        if seat and len(seat['hand']) == 0:
            winner = seat['name']
            break
            
    # --- FIX QUAN TRỌNG: 
    # Nếu tìm thấy winner thì gọi hàm kết thúc game NGAY LẬP TỨC
    # Dù game đang là PLAYING hay FINISHED cũng đều gửi để Client nhận được
    if winner:
        # Nếu game chưa finish thì finish nó và gửi sự kiện
        if game.state != "FINISHED":
            await handle_game_end(game, winner)
        
        # Nếu game đã finish rồi nhưng Client có thể chưa nhận được (do mạng lag), 
        # ta vẫn có thể gửi lại tlmn_end nếu cần thiết, nhưng tốt nhất là gửi 1 lần ở trên.

    # 2. Gửi thông tin bàn
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
                        'sid': seat_data['sid'],
                        'name': seat_data['name'],
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

# --- CARO (CỜ CARO) ---
@sio.event
async def create_caro(sid, data):
    print(f"--- ĐANG TẠO PHÒNG CARO CHO {sid} ---") # In log debug
    
    mode = data.get('mode') 
    name = data.get('name', 'Player')
    is_bot = (mode == 'bot')
    
    # 1. Tạo ID bắt đầu bằng "C-"
    room_id = f"C-{sid[:4]}".upper()
    
    # 2. Khởi tạo Game
    game = CaroGame(room_id, host_sid=sid)
    game.is_bot_mode = is_bot
    
    # --- QUAN TRỌNG: BẮT BUỘC PHẢI CÓ DÒNG NÀY ---
    # Nếu thiếu host_name, RoomManager sẽ không hiển thị phòng ra danh sách
    game.host_name = name 
    # ---------------------------------------------
    
    game.add_player(sid, name)
    
    if is_bot:
        game.players['BOT'] = {'name': 'Máy Siêu Cấp', 'symbol': 'O'}
    
    # 3. Lưu vào Manager
    manager.rooms[room_id] = game 
    sid_to_room[sid] = room_id
    
    print(f"-> Đã lưu phòng {room_id} vào Manager. Host: {game.host_name}") # In log debug

    # 4. Vào phòng socket
    await sio.enter_room(sid, room_id)
    await sio.emit('room_joined', {'room_id': room_id, 'game_type': 'caro'}, room=sid)
    
    # 5. Cập nhật danh sách (Chỉ khi chơi Online)
    if not is_bot: 
        print("-> Đang gửi danh sách phòng cập nhật...") # In log debug
        await broadcast_room_list()
    else:
        print("-> Chế độ Bot: Không hiện lên danh sách.")

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
        await broadcast_room_list() # Cập nhật danh sách để ẩn phòng full
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
        
        # Nếu chơi với Bot và game chưa kết thúc -> Bot đánh
        if game.is_bot_mode and game.state == 'PLAYING' and game.turn == 'O':
            await asyncio.sleep(0.5) # Giả vờ suy nghĩ
            move = game.bot_move()
            if move:
                game.make_move('BOT', move[0], move[1])
                await broadcast_caro_state(game)
    else:
        pass # Có thể gửi lỗi nếu muốn

async def broadcast_caro_state(game):
    # 1. Tạo danh sách tên map theo phe X và O (Dùng để hiển thị tên nhanh)
    player_names = {'X': 'Đang chờ...', 'O': 'Đang chờ...'}
    for p_data in game.players.values():
        player_names[p_data['symbol']] = p_data['name']

    # 2. Gửi thông tin về Client
    info = {
        'board': list(game.board.items()),
        'turn': game.turn,
        'winner': game.winner,
        'names': player_names,
        
        # --- SỬA DÒNG NÀY ---
        # Gửi nguyên cục data (gồm name và symbol) để Client biết ai là X, ai là O mà gán ID chat
        'players': {k: v for k, v in game.players.items() if k != 'BOT' or True},
        'last_move': game.last_move
        # --------------------
    }
    await sio.emit('caro_update', info, room=game.room_id)

@sio.event
async def caro_restart(sid):
    room_id = sid_to_room.get(sid)
    game = manager.rooms.get(room_id)
    
    # Chỉ chủ phòng hoặc cả 2 đều có quyền reset (ở đây cho phép cả 2 cho tiện)
    if game and isinstance(game, CaroGame):
        game.reset_game()
        await broadcast_caro_state(game) # Gửi bàn cờ trắng về cho mọi người

@sio.event
async def caro_leave(sid):
    room_id = sid_to_room.get(sid)
    if room_id:
        # Tận dụng hàm disconnect để xóa player và dọn phòng nếu trống
        await disconnect(sid) 
        # Gửi xác nhận về client (để client yên tâm là đã thoát)
        await sio.emit('left_room', {}, room=sid)
#--- CHẠY SERVER ---
if __name__ == "__main__":
    import os
    # Lấy PORT từ biến môi trường của Render (mặc định là 10000 nếu chạy local)
    port = int(os.environ.get("PORT", 8000)) 
    
    # Quan trọng: host phải là "0.0.0.0" (không được để 127.0.0.1 hay localhost)
    uvicorn.run("main:sio_app", host="0.0.0.0", port=port, reload=False)