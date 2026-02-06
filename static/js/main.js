const socket = io();
let currentScreen = 'home';
let currentUser = null; // Biến lưu người dùng hiện tại

// --- CÁC HÀM CHUNG ---
function showScreen(id) {
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
    document.getElementById(id).classList.add('active');
    currentScreen = id;
    // 2. THÊM ĐOẠN NÀY: Xử lý ẩn/hiện nút Đăng nhập
    const authBtns = document.getElementById('auth-buttons');
    if (authBtns) {
        if (id === 'home-screen') {
            // Chỉ hiện lại nút khi về Sảnh VÀ chưa đăng nhập (currentUser là null)
            if (!currentUser) {
                authBtns.style.display = 'flex'; 
            }
        } else {
            // Vào bất kỳ màn hình game/lobby nào thì ẨN luôn cho thoáng
            authBtns.style.display = 'none';
        }
    }
}
function goHome() { showScreen('home-screen'); }

function renderCard(c) {
    if(!c || c == "??") return `<div class="card hidden-card"></div>`;
    let rank = c.slice(0, -1);
    let suit = c.slice(-1);
    const isRed = (suit === '♥' || suit === '♦');
    return `<div class="card ${isRed ? 'red' : ''}">${rank}<small>${suit}</small></div>`;
}

function leaveRoom(type) {
    if(type === 'tlmn') {
        socket.emit('tlmn_action', {act: 'leave'});
        document.getElementById('game-controls').style.display = 'none';
        const startBtn = document.getElementById('btn-start');
        if(startBtn) startBtn.style.display = 'none';
        document.getElementById('table-center').innerHTML = '';
    } 
    else if (type === 'caro') socket.emit('caro_leave'); 
    else if (type === 'blackjack') socket.emit('action', {act: 'leave'});
    goHome();
}

function closeWinnerPopup() {
    document.getElementById('winner-overlay').style.display = 'none';
}

function joinByCode() {
    const code = document.getElementById('room-code-input').value.toUpperCase();
    const name = document.getElementById('username').value;
    socket.emit('join_tlmn', {code: code, name: name});
}
function joinRoom(id) {
    const name = document.getElementById('username').value;
    socket.emit('join_tlmn', {code: id, name: name});
}

// --- LOGIC KIỂM TRA TRƯỚC KHI CHƠI ---
function checkLoginAndPlay(gameType) {
    const nameInput = document.getElementById('username');
    const name = nameInput.value.trim();

    // 1. Nếu chưa nhập tên -> Bắt nhập
    if (!name) {
        alert("Vui lòng nhập tên (Khách) hoặc Đăng nhập để chơi!");
        nameInput.focus();
        nameInput.style.border = "2px solid red";
        setTimeout(() => nameInput.style.border = "none", 2000);
        return;
    }

    // 2. Chuyển màn hình
    if(gameType === 'tienlen') showTLMNMenu();
    else if(gameType === 'caro') showCaroMenu();
    else if(gameType === 'blackjack') startBlackjack();
}

// --- HỆ THỐNG AUTHENTICATION ---
function openAuthModal(type) {
    document.getElementById('auth-overlay').style.display = 'flex';
    const title = document.getElementById('auth-title');
    const btn = document.getElementById('btn-auth-action');
    document.getElementById('auth-msg').innerText = "";
    
    if (type === 'login') {
        title.innerText = "ĐĂNG NHẬP";
        btn.innerText = "ĐĂNG NHẬP";
        btn.onclick = () => doAuth('auth_login');
    } else {
        title.innerText = "ĐĂNG KÝ";
        btn.innerText = "ĐĂNG KÝ";
        btn.onclick = () => doAuth('auth_register');
    }
}

function closeAuthModal() {
    document.getElementById('auth-overlay').style.display = 'none';
}

function doAuth(event) {
    const u = document.getElementById('auth-user').value.trim();
    const p = document.getElementById('auth-pass').value.trim();
    if(!u || !p) {
        document.getElementById('auth-msg').innerText = "Vui lòng nhập đủ thông tin!";
        return;
    }
    socket.emit(event, {username: u, password: p});
}

function logout() {
    currentUser = null;
    document.getElementById('auth-buttons').style.display = 'block';
    
    // --- SỬA ĐOẠN NÀY ---
    // Thay vì ẩn đi (display = 'none'), ta đưa nó về vị trí cũ và reset số
    const infoBar = document.getElementById('user-info-bar');
    infoBar.style.right = '240px'; // Dịch sang trái để nhường chỗ cho nút Đăng nhập
    
    document.getElementById('display-username').innerText = "Player";
    document.getElementById('user-money').innerText = "10,000";
    document.getElementById('spin-count').innerText = "3";
    
    document.getElementById('btn-logout').style.display = 'none'; // Ẩn nút thoát
    // --------------------

    document.getElementById('lucky-wheel-btn').style.display = 'none';
    alert("Đã đăng xuất!");
    goHome();
}

// NHẬN KẾT QUẢ AUTH TỪ SERVER
socket.on('auth_response', (data) => {
    if (data.success) {
        closeAuthModal();
        currentUser = data.username;
        
        // 1. Ẩn nút đăng nhập, Hiện thanh thông tin
        document.getElementById('auth-buttons').style.display = 'none';
        document.getElementById('user-info-bar').style.display = 'flex';
        
        // 2. Cập nhật tên lên thanh thông tin
        const displayUser = document.getElementById('display-username');
        if(displayUser) displayUser.innerText = currentUser;
        
        // 3. ĐIỀN TÊN VÀO Ô GIỮA MÀN HÌNH VÀ KHÓA LẠI (FIX LỖI CỦA BẠN TẠI ĐÂY)
        const nameInput = document.getElementById('username');
        if (nameInput) {
            nameInput.value = currentUser;
            nameInput.readOnly = true; // Khóa không cho sửa
            nameInput.style.background = "#ddd"; // Màu xám
        }
        
        // 4. Lấy tiền ngay lập tức
        socket.emit('get_my_money', {name: currentUser});

    } else {
        document.getElementById('auth-msg').innerText = data.msg;
    }
});

// --- TIỀN & BXH ---
// Tự động cập nhật tiền khi nhập tên (cho khách)
const nameInput = document.getElementById('username');
if(nameInput) {
    nameInput.addEventListener('change', () => {
        if(nameInput.value.trim()) {
            socket.emit('get_my_money', {name: nameInput.value});
        }
    });
}

// Nhận dữ liệu tiền từ server về
socket.on('money_update', (data) => {
    // Tìm thẻ hiển thị tiền
    const moneyEl = document.getElementById('user-money');
    const spinEl = document.getElementById('spin-count');

    // Cập nhật text và format số (ví dụ: 10000 -> 10,000)
    if(data.money !== undefined && moneyEl) {
        moneyEl.innerText = data.money.toLocaleString();
    }
    if(data.spins !== undefined && spinEl) {
        spinEl.innerText = data.spins;
    }
    if(currentScreen === 'tlmn-game' || currentScreen === 'caro-game') {
        showNotify(`💰 Số dư mới: ${data.money.toLocaleString()}$`, 'money');
    }
});

// --- CÁC LOGIC KHÁC (ROOM, CHAT, GAME) GIỮ NGUYÊN ---

socket.on('room_list_update', (rooms) => {
    const tlmnList = document.getElementById('room-list');
    if (tlmnList) {
        const tlmnRooms = rooms.filter(r => !r.id.startsWith('C-'));
        if (tlmnRooms.length === 0) tlmnList.innerHTML = "<p>Chưa có phòng.</p>";
        else tlmnList.innerHTML = tlmnRooms.map(r => `
            <div class="room-item" onclick="joinRoom('${r.id}')">
                <span><b>${r.id}</b></span>
                <span>${r.players} - ${r.host}</span>
            </div>`).join('');
    }
    const caroList = document.getElementById('caro-room-list');
    if (caroList) {
        const caroRooms = rooms.filter(r => r.id.startsWith('C-'));
        if (caroRooms.length === 0) caroList.innerHTML = "<p>Chưa có phòng.</p>";
        else caroList.innerHTML = caroRooms.map(r => `
            <div class="room-item" onclick="joinCaroRoom('${r.id}')">
                <span><b>${r.id}</b></span>
                <span>${r.players} - ${r.host}</span>
            </div>`).join('');
    }
});

socket.on('room_joined', (data) => {
    if(data.game_type === 'tienlen') {
        showScreen('tlmn-game');
        document.getElementById('rid-display').innerText = "Phòng: " + data.room_id;
        const startBtn = document.getElementById('btn-start');
        if(startBtn) startBtn.style.display = 'none'; 
    } else if (data.game_type === 'caro') {
        showScreen('caro-game');
        document.getElementById('caro-rid').innerText = data.room_id;
        initCaroBoard(); 
    }
});

function toggleChatPopup() {
    const popup = document.getElementById('chat-popup');
    popup.style.display = (popup.style.display === 'grid') ? 'none' : 'grid';
    if (popup.style.display === 'grid') document.getElementById('chat-msg').focus();
}
function sendText() {
    const input = document.getElementById('chat-msg');
    const text = input.value.trim();
    if (text) {
        sendChat('text', text);
        input.value = '';
    }
}
function checkEnter(e) { if (e.key === "Enter") sendText(); }
function sendChat(type, content) {
    socket.emit('send_chat', {type: type, content: content});
    toggleChatPopup(); 
}
socket.on('chat_received', (data) => {
    const bubbleId = `chat-bubble-${data.sender_sid}`;
    const bubble = document.getElementById(bubbleId);
    if (bubble) {
        if (data.type === 'text') bubble.innerText = data.content;
        else if (data.type === 'image') bubble.innerHTML = `<img src="${data.content}">`;
        bubble.style.display = 'block';
        if (bubble.hideTimeout) clearTimeout(bubble.hideTimeout);
        bubble.hideTimeout = setTimeout(() => { bubble.style.display = 'none'; }, 5000);
    }
});

function startBlackjack() {
    showScreen('blackjack-game');
    document.getElementById('bj-dealer-cards').innerHTML = "";
    document.getElementById('bj-my-cards').innerHTML = "";
    document.getElementById('bj-controls').style.display = 'none';
    document.getElementById('bj-btn-start').style.display = 'none';
    socket.emit('start_blackjack_pvc');
}
function bjAction(act) { socket.emit('action', {act: act}); }

socket.on('deal_cards', (data) => {
    document.getElementById('bj-btn-start').style.display = 'none';
    document.getElementById('bj-my-cards').innerHTML = data.hand.map(renderCard).join('');
    document.getElementById('bj-my-score').innerText = "Điểm: " + data.score;
    document.getElementById('bj-dealer-cards').innerHTML = data.dealer_view.map(renderCard).join('');
    document.getElementById('bj-controls').style.display = 'block';
});
socket.on('update_hand', (data) => {
    const current = document.getElementById('bj-my-cards').innerHTML;
    const newCard = data.hand[data.hand.length - 1];
    document.getElementById('bj-my-cards').innerHTML = current + renderCard(newCard);
    document.getElementById('bj-my-score').innerText = "Điểm: " + data.score;
    if(data.score > 21) document.getElementById('bj-controls').style.display = 'none';
});
socket.on('game_over', (data) => {
    document.getElementById('bj-dealer-cards').innerHTML = data.dealer_hand.map(renderCard).join('');
    document.getElementById('bj-dealer-score').innerText = "Điểm: " + data.dealer_score;
    document.getElementById('bj-controls').style.display = 'none';
    document.getElementById('bj-btn-start').style.display = 'inline-block';
    setTimeout(() => alert(`KẾT QUẢ: ${data.result}`), 200);
});
socket.on('force_leave', (data) => { alert(data.msg); goHome(); });
socket.on('error', (data) => {
    // Gọi hàm thông báo nổi thay vì alert
    showNotify(data.msg, 'error');
});

function showLeaderboard() {
    socket.emit('get_leaderboard');
    document.getElementById('leaderboard-overlay').style.display = 'flex';
}

socket.on('leaderboard_data', (data) => {
    const list = document.getElementById('leaderboard-list');
    list.innerHTML = "";
    data.forEach((user, index) => {
        let icon = "👤";
        if (index === 0) icon = "🥇";
        if (index === 1) icon = "🥈";
        if (index === 2) icon = "🥉";
        list.innerHTML += `<div style="display: flex; justify-content: space-between; padding: 10px; border-bottom: 1px solid #555; font-size: 16px;"><span>${icon} <b>${user[0]}</b></span><span style="color: gold;">${user[1].toLocaleString()} $</span></div>`;
    });
});

function showWheel() {
    document.getElementById('wheel-overlay').style.display = 'flex';
    const wheel = document.getElementById('the-wheel');
    wheel.style.transition = 'none';
    wheel.style.transform = 'rotate(0deg)';
}

function spinNow() {
    const name = document.getElementById('username').value;
    // Kiểm tra xem đã đăng nhập chưa
    if (!name) {
        alert("Vui lòng đăng nhập để quay!");
        return;
    }
    
    const btn = document.getElementById('btn-spin-action');
    btn.disabled = true; 
    socket.emit('spin_wheel', {'name': name});
}

socket.on('spin_result', (data) => {
    const wheel = document.getElementById('the-wheel');
    const prizeIndex = data.index; 
    const segments = 7; 
    const segmentAngle = 360 / segments;
    const rotateAmount = (360 * 5) - (prizeIndex * segmentAngle) - (segmentAngle / 2);

    wheel.style.transition = 'transform 4s cubic-bezier(0.25, 0.1, 0.25, 1)';
    wheel.style.transform = `rotate(${rotateAmount}deg)`;

    setTimeout(() => {
        alert(`🎉 BẠN NHẬN ĐƯỢC: ${data.prize.label}`);
        document.getElementById('user-money').innerText = data.new_money.toLocaleString();
        document.getElementById('spin-count').innerText = data.remaining_spins;
        document.getElementById('btn-spin-action').disabled = false;
    }, 4000);
});
function reloadRooms() {
    socket.emit('get_room_list'); // Gửi yêu cầu lên server
    // Hiển thị hiệu ứng đang tải giả lập
    const list1 = document.getElementById('room-list');
    const list2 = document.getElementById('caro-room-list');
    if(list1) list1.innerHTML = '<div style="color: yellow;">Đang làm mới...</div>';
    if(list2) list2.innerHTML = '<div style="color: yellow;">Đang làm mới...</div>';
}
// --- HÀM HIỂN THỊ THÔNG BÁO BAY ---
function showNotify(msg, type = 'normal') {
    // 1. Tạo thẻ div
    const div = document.createElement('div');
    div.className = 'game-notify';
    
    // 2. Thêm class màu sắc tùy loại
    if (type === 'error' || msg.includes('lỗi') || msg.includes('bị')) {
        div.classList.add('notify-error');
    } else if (type === 'money' || msg.includes('+')) {
        div.classList.add('notify-money');
    }
    
    // 3. Gán nội dung
    div.innerHTML = msg;
    
    // 4. Gắn vào body
    document.body.appendChild(div);
    
    // 5. Tự động xóa sau 2.5 giây (khớp với animation css)
    setTimeout(() => {
        div.remove();
    }, 2500);
}