const socket = io();
let currentScreen = 'home';

function showScreen(id) {
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
    document.getElementById(id).classList.add('active');
    currentScreen = id;
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
        startBtn.style.display = 'none';
        startBtn.innerText = "BẮT ĐẦU"; 
        document.getElementById('table-center').innerHTML = '';
    } 
    else if (type === 'caro') {
        socket.emit('caro_leave'); 
    }
    else if (type === 'blackjack') {
        socket.emit('action', {act: 'leave'}); // Nếu có
    }
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

// --- 1. XỬ LÝ DANH SÁCH PHÒNG ---
socket.on('room_list_update', (rooms) => {
    // Danh sách Tiến Lên
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
    // Danh sách Caro
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

// --- ĐIỀU HƯỚNG PHÒNG ---
socket.on('room_joined', (data) => {
    if(data.game_type === 'tienlen') {
        showScreen('tlmn-game');
        document.getElementById('rid-display').innerText = "Phòng: " + data.room_id;
        const startBtn = document.getElementById('btn-start');
        startBtn.style.display = 'none'; 
        startBtn.innerText = 'BẮT ĐẦU';
    } else if (data.game_type === 'caro') {
        showScreen('caro-game');
        document.getElementById('caro-rid').innerText = data.room_id;
        initCaroBoard(); 
    }
});

// --- CHAT SYSTEM CHUNG ---
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

// --- BLACKJACK LOGIC ---
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
socket.on('error', (data) => alert(data.msg));