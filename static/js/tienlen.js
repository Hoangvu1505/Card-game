function showTLMNMenu() {
    showScreen('tlmn-lobby');
    reloadRooms();
 }

function createTLMN(mode) {
    const name = document.getElementById('username').value;
    socket.emit('create_tlmn', {mode: mode, name: name});
}

function tlmnAction(act) {
    if (act === 'pass') {
        socket.emit('tlmn_action', {act: 'pass'});
    } else {
        const checked = document.querySelectorAll('.card-checkbox:checked');
        const cards = Array.from(checked).map(c => c.value);
        if (cards.length === 0) return alert("Chọn bài đi!");
        socket.emit('tlmn_action', {act: 'play', cards: cards});
    }
}

// CẬP NHẬT GIAO DIỆN TIẾN LÊN
socket.on('tlmn_update', (data) => {
    data.seats.forEach((seat, index) => {
        const div = document.getElementById(`seat-${index}`);
        if (!seat) { div.innerHTML = `<div class="avatar" style="opacity:0.3">+</div>`; return; }
        
        let cardsHtml = '';
        if (index === 0) {
            cardsHtml = '<div style="display:flex; justify-content:center; width: 400px; flex-wrap:wrap;">' + 
                seat.hand.map(c => `<label><input type="checkbox" class="card-checkbox" value="${c}">${renderCard(c)}</label>`).join('') + '</div>';
        } else {
            if (seat.is_winner) cardsHtml = ''; 
            else cardsHtml = `<div class="card card-back">${seat.hand}</div>`; 
        }

        let chatBtnHtml = (index === 0) ? `<button class="chat-btn" onclick="toggleChatPopup()">💬</button>` : '';
        let bubbleHtml = `<div id="chat-bubble-${seat.sid}" class="chat-bubble"></div>`;
        let winnerHtml = seat.is_winner ? `<div class="winner-badge">👑 CHIẾN THẮNG 👑</div>` : '';
        
        if (seat.is_winner) div.classList.add('active-turn');
        else if (seat.is_turn) div.classList.add('active-turn');
        else div.classList.remove('active-turn');

        div.className = `seat seat-${index} ${seat.is_turn || seat.is_winner ? 'active-turn' : ''}`;
        div.innerHTML = `${winnerHtml}${bubbleHtml}${chatBtnHtml}<div class="avatar">${seat.name}</div>${cardsHtml}`;
    });

    const centerDiv = document.getElementById('table-center');
    centerDiv.innerHTML = (data.last_move && data.last_move.length > 0) ? data.last_move.map(renderCard).join('') : "";

    const startBtn = document.getElementById('btn-start');
    if (data.is_host && (data.state === 'WAITING' || data.state === 'FINISHED') && data.state !== 'PLAYING') {
        startBtn.style.display = 'block';
        startBtn.innerText = (data.state === 'FINISHED') ? "CHƠI LẠI" : "BẮT ĐẦU";
    } else {
        startBtn.style.display = 'none';
    }
    document.getElementById('game-controls').style.display = (data.seats[0] && data.seats[0].is_turn) ? 'block' : 'none';
});

socket.on('tlmn_end', (data) => {
    const winner = data.winner;
    const myName = document.getElementById('username').value;
    document.getElementById('winner-name-display').innerText = winner;
    if (winner === myName || winner === "Bạn") {
        document.getElementById('winner-message').innerText = "🎉 XUẤT SẮC! BẠN ĐÃ CHIẾN THẮNG 🎉";
        document.querySelector('.winner-box').style.background = "linear-gradient(135deg, #2ecc71, #27ae60)";
    } else {
        document.getElementById('winner-message').innerText = "😢 Chúc bạn may mắn lần sau...";
        document.querySelector('.winner-box').style.background = "linear-gradient(135deg, #e74c3c, #c0392b)";
    }
    document.getElementById('winner-overlay').style.display = 'flex';
});