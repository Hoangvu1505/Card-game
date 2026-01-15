function showCaroMenu() { showScreen('caro-lobby'); }

function createCaro(mode) {
    const name = document.getElementById('username').value;
    socket.emit('create_caro', {mode: mode, name: name});
}

function joinCaroByInput() {
    const code = document.getElementById('caro-code-input').value.toUpperCase();
    const name = document.getElementById('username').value;
    if(!code) return alert("Vui lòng nhập mã phòng!");
    socket.emit('join_caro', {code: code, name: name});
}

function joinCaroRoom(id) {
    const name = document.getElementById('username').value;
    socket.emit('join_caro', {code: id, name: name});
}

function initCaroBoard() {
    const boardDiv = document.getElementById('caro-board');
    boardDiv.innerHTML = '';
    for(let r=0; r<15; r++){
        for(let c=0; c<15; c++){
            const cell = document.createElement('div');
            cell.className = 'cell';
            cell.id = `c-${r}-${c}`;
            cell.onclick = () => socket.emit('caro_move', {r: r, c: c});
            boardDiv.appendChild(cell);
        }
    }
}

// UPDATE CARO
socket.on('caro_update', (data) => {
    document.querySelectorAll('.cell').forEach(c => {
        c.innerText = ''; c.className='cell'; 
    });
    
    data.board.forEach(item => {
        const [pos, val] = item; 
        const cell = document.getElementById(`c-${pos[0]}-${pos[1]}`);
        if(cell) {
            cell.innerText = val;
            cell.classList.add(val.toLowerCase());
        }
    });

    if (data.last_move) {
        const [r, c] = data.last_move;
        const lastCell = document.getElementById(`c-${r}-${c}`);
        if (lastCell) lastCell.classList.add('last-move');
    }

    if (data.names) {
        document.getElementById('player-x').innerText = 'X: ' + data.names.X;
        document.getElementById('player-o').innerText = 'O: ' + data.names.O;
    }

    if (data.players) {
        for (const [sid, p] of Object.entries(data.players)) {
            if (p.symbol === 'X') {
                const bubble = document.querySelector('#wrapper-x .chat-bubble');
                if(bubble) bubble.id = `chat-bubble-${sid}`;
            } else if (p.symbol === 'O') {
                const bubble = document.querySelector('#wrapper-o .chat-bubble');
                if(bubble) bubble.id = `chat-bubble-${sid}`;
            }
        }
    }

    const px = document.getElementById('player-x');
    const po = document.getElementById('player-o');
    if(data.turn === 'X') { 
        px.classList.add('active-turn-box'); po.classList.remove('active-turn-box'); 
    } else { 
        po.classList.add('active-turn-box'); px.classList.remove('active-turn-box'); 
    }

    const controls = document.getElementById('caro-controls');
    if(data.winner) {
        controls.style.display = 'block';
        const winnerName = data.names ? data.names[data.winner] : data.winner;
        setTimeout(() => alert(`🏆 CHÚC MỪNG! ${winnerName} (${data.winner}) ĐÃ CHIẾN THẮNG!`), 100);
    } else {
        controls.style.display = 'none';
    }
});

// CARO CHAT
function toggleCaroChat() {
    const popup = document.getElementById('caro-chat-popup');
    popup.style.display = (popup.style.display === 'grid') ? 'none' : 'grid';
    if (popup.style.display === 'grid') document.getElementById('caro-chat-msg').focus();
}
function sendCaroText() {
    const input = document.getElementById('caro-chat-msg');
    const text = input.value.trim();
    if (text) {
        sendCaroChat('text', text);
        input.value = '';
    }
}
function checkCaroEnter(e) { if (e.key === "Enter") sendCaroText(); }
function sendCaroChat(type, content) {
    socket.emit('send_chat', {type: type, content: content});
    toggleCaroChat(); 
}