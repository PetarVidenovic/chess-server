// ==================== GLOBALNE PROMENLJIVE ====================
let token = null;
let currentUser = null;
let ws = null;
let currentGameId = null;
let myColor = null; // "white" ili "black"
let game = null;

let onlineUsers = [];
let pendingChallenges = [];

// ==================== POMOĆNE FUNKCIJE ====================
function showView(viewId) {
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.getElementById(viewId).classList.add('active');
}

function showResultModal(title, message) {
    const modal = document.getElementById('result-modal');
    document.getElementById('result-title').innerText = title;
    document.getElementById('result-message').innerText = message;
    modal.style.display = 'flex';
    document.getElementById('result-ok').onclick = () => {
        modal.style.display = 'none';
        currentGameId = null;
        showView('lobby-view');
    };
}

function apiRequest(method, endpoint, data = null) {
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    return fetch(endpoint, {
        method,
        headers,
        body: data ? JSON.stringify(data) : undefined
    }).then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
    });
}

function connectWebSocket() {
    if (ws) ws.close();
    const wsUrl = `wss://${window.location.host}/ws?token=${token}`;
    ws = new WebSocket(wsUrl);
    ws.onopen = () => console.log("WebSocket connected");
    ws.onmessage = (event) => handleWebSocketMessage(JSON.parse(event.data));
    ws.onerror = (err) => console.error("WebSocket error", err);
    ws.onclose = () => {
        console.log("WebSocket closed, reconnecting in 3s...");
        setTimeout(() => { if (token) connectWebSocket(); }, 3000);
    };
}

function handleWebSocketMessage(data) {
    console.log("WS:", data);
    const type = data.type;
    if (type === "online_users") {
        onlineUsers = data.users.filter(u => u.id !== currentUser?.id);
        renderOnlineUsers();
    }
    else if (type === "challenge_received") {
        pendingChallenges.push({
            challenge_id: data.challenge_id,
            from_username: data.from_username,
            from_id: data.from_id
        });
        renderChallenges();
    }
    else if (type === "challenge_accepted" || type === "match_found") {
        currentGameId = data.game_id;
        // ISPRAVKA: koristi my_color (ili color kao fallback)
        myColor = data.my_color || data.color;
        console.log("Postavljen myColor:", myColor);
        // Osveži debug info
        updateDebugInfo();
        startGame(data.opponent);
    }
    else if (type === "move" || type === "game_state") {
        if (data.game_id === currentGameId && data.fen) {
            game = new Chess(data.fen);
            drawBoard();
            updateGameStatus();
            updateDebugInfo();
        }
    }
    else if (type === "game_chat") {
        appendGameChatMessage(data.from_username, data.content);
    }
    else if (type === "game_over" || data.result) {
        if (data.game_id === currentGameId) {
            let resultTitle = "", resultMsg = "";
            const winner = data.winner;
            if (winner === myColor) {
                resultTitle = "🏆 POBEDA!";
                resultMsg = "Čestitamo, pobedili ste!";
            } else if (winner && winner !== myColor) {
                resultTitle = "💔 PORAZ";
                resultMsg = "Nažalost, izgubili ste.";
            } else {
                resultTitle = "🤝 REMI";
                resultMsg = "Partija je završena remijem.";
            }
            if (data.result_text) resultMsg = data.result_text;
            showResultModal(resultTitle, resultMsg);
            currentGameId = null;
        }
    }
}

function updateDebugInfo() {
    const debugDiv = document.getElementById('debug-info');
    if (debugDiv && game) {
        const turnText = game.turn() === 'w' ? 'Beli' : 'Crni';
        debugDiv.innerHTML = `myColor: ${myColor} | game.turn: ${turnText} (${game.turn()}) | na potezu: ${turnText}`;
    }
}

// ==================== LOBBY UI ====================
function renderOnlineUsers() {
    const container = document.getElementById('users-list');
    container.innerHTML = '';
    onlineUsers.forEach(user => {
        const li = document.createElement('li');
        li.innerHTML = `${user.username} <button class="challenge-btn" data-id="${user.id}">Izazovi</button>`;
        container.appendChild(li);
    });
    container.querySelectorAll('.challenge-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            if (!ws || ws.readyState !== WebSocket.OPEN) {
                alert("WebSocket nije povezan. Pokušajte ponovo.");
                return;
            }
            const userId = parseInt(btn.getAttribute('data-id'));
            console.log("Šaljem izazov ID:", userId);
            ws.send(JSON.stringify({ type: "challenge", opponent_id: userId }));
        });
    });
}

function renderChallenges() {
    const container = document.getElementById('challenges-list');
    container.innerHTML = '';
    pendingChallenges.forEach(ch => {
        const li = document.createElement('li');
        li.innerHTML = `${ch.from_username} 
            <button class="accept-btn" data-id="${ch.challenge_id}" data-from="${ch.from_id}">Prihvati</button>
            <button class="decline-btn" data-id="${ch.challenge_id}">Odbij</button>`;
        container.appendChild(li);
    });
    container.querySelectorAll('.accept-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const challengeId = btn.getAttribute('data-id');
            const fromId = btn.getAttribute('data-from');
            ws.send(JSON.stringify({
                type: "accept_challenge",
                challenge_id: challengeId,
                from_id: parseInt(fromId)
            }));
            pendingChallenges = pendingChallenges.filter(c => c.challenge_id != challengeId);
            renderChallenges();
        });
    });
    container.querySelectorAll('.decline-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const challengeId = btn.getAttribute('data-id');
            ws.send(JSON.stringify({ type: "decline_challenge", challenge_id: challengeId }));
            pendingChallenges = pendingChallenges.filter(c => c.challenge_id != challengeId);
            renderChallenges();
        });
    });
}

// ==================== ŠAHOVSKA TABLA ====================
function startGame(opponentName) {
    game = new Chess();
    showView('game-view');
    document.getElementById('game-opponent').innerText = `Protivnik: ${opponentName}`;
    setTimeout(() => {
        drawBoard();
        updateGameStatus();
        updateDebugInfo();
    }, 50);
}

function getPieceSymbol(type, color) {
    const symbols = {
        'k': color === 'w' ? '♔' : '♚',
        'q': color === 'w' ? '♕' : '♛',
        'r': color === 'w' ? '♖' : '♜',
        'b': color === 'w' ? '♗' : '♝',
        'n': color === 'w' ? '♘' : '♞',
        'p': color === 'w' ? '♙' : '♟'
    };
    return symbols[type];
}

function drawBoard() {
    const boardDiv = document.getElementById('chessboard');
    if (!boardDiv) return;
    boardDiv.innerHTML = '';
    const board = game.board();
    for (let i = 0; i < 8; i++) {
        for (let j = 0; j < 8; j++) {
            const square = document.createElement('div');
            square.classList.add('square');
            square.classList.add((i + j) % 2 === 0 ? 'light' : 'dark');
            const piece = board[i][j];
            square.textContent = piece ? getPieceSymbol(piece.type, piece.color) : '';
            square.dataset.row = i;
            square.dataset.col = j;
            boardDiv.appendChild(square);
        }
    }
}

function updateGameStatus() {
    const statusDiv = document.getElementById('game-status');
    if (!statusDiv) return;
    if (game.game_over()) {
        if (game.in_checkmate()) {
            const winner = game.turn() === 'w' ? 'Crni' : 'Beli';
            statusDiv.innerText = `Mat! ${winner} je pobedio.`;
        } else if (game.in_stalemate()) statusDiv.innerText = 'Pat – remi.';
        else statusDiv.innerText = 'Partija završena.';
    } else {
        const turn = game.turn() === 'w' ? 'Beli' : 'Crni';
        statusDiv.innerText = `${turn} na potezu.`;
    }
}

let selectedSquare = null;

function highlightSelectedSquare(row, col) {
    clearHighlight();
    const boardDiv = document.getElementById('chessboard');
    const idx = row * 8 + col;
    if (boardDiv.children[idx]) boardDiv.children[idx].classList.add('selected');
}
function clearHighlight() {
    document.querySelectorAll('.square').forEach(sq => sq.classList.remove('selected'));
}

function handleSquareTap(e) {
    const squareDiv = e.target.closest('.square');
    if (!squareDiv) return;
    if (!currentGameId) return;
    if (game.game_over()) return;

    const turn = game.turn(); // 'w' ili 'b'
    let myTurn = false;
    if (myColor === 'white' && turn === 'w') myTurn = true;
    if (myColor === 'black' && turn === 'b') myTurn = true;

    // Ako nije tvoj potez, prikaži detaljnu poruku (umesto samo "Niste na potezu")
    if (!myTurn) {
        alert(`Niste na potezu! (myColor=${myColor}, game.turn=${turn})`);
        return;
    }

    const row = parseInt(squareDiv.dataset.row);
    const col = parseInt(squareDiv.dataset.col);
    const file = String.fromCharCode(97 + col);
    const rank = 8 - row;
    const square = file + rank;

    if (selectedSquare === null) {
        // Prvi klik: proveri da li je na toj figuri igrač
        const piece = game.get(square);
        if (piece && ((myColor === 'white' && piece.color === 'w') || (myColor === 'black' && piece.color === 'b'))) {
            selectedSquare = square;
            highlightSelectedSquare(row, col);
        } else {
            alert("To nije vaša figura!");
        }
    } else {
        // Drugi klik: pokušaj poteza
        const move = game.move({
            from: selectedSquare,
            to: square,
            promotion: 'q'
        });
        if (move) {
            ws.send(JSON.stringify({
                type: "move",
                game_id: currentGameId,
                fen: game.fen(),
                move: move.from + move.to,
                turn: game.turn() === 'w' ? 'w' : 'b'
            }));
            drawBoard();
            updateGameStatus();
            updateDebugInfo();
        } else {
            alert("Nelegalan potez");
        }
        selectedSquare = null;
        clearHighlight();
    }
}

const boardDivElement = document.getElementById('chessboard');
if (boardDivElement) {
    boardDivElement.addEventListener('click', handleSquareTap);
    boardDivElement.addEventListener('touchstart', (e) => {
        e.preventDefault();
        const touch = e.touches[0];
        const fakeEvent = { target: document.elementFromPoint(touch.clientX, touch.clientY) };
        handleSquareTap(fakeEvent);
    });
}

function appendGameChatMessage(sender, msg) {
    const chatDiv = document.getElementById('game-chat-messages');
    if (!chatDiv) return;
    const p = document.createElement('div');
    p.textContent = `${sender}: ${msg}`;
    chatDiv.appendChild(p);
    chatDiv.scrollTop = chatDiv.scrollHeight;
}

// ==================== AUTH ====================
async function login(email, password) {
    try {
        const data = await apiRequest('POST', '/auth/login', { email, password });
        token = data.access_token;
        const userData = await apiRequest('GET', '/users/me');
        currentUser = userData;
        connectWebSocket();
        showView('lobby-view');
        document.getElementById('lobby-error').innerText = '';
    } catch (err) {
        document.getElementById('auth-error').innerText = 'Pogrešan email ili lozinka';
    }
}

async function register(email, username, password) {
    try {
        await apiRequest('POST', '/auth/register', { email, username, password });
        document.getElementById('reg-error').innerText = '';
        showView('auth-view');
    } catch (err) {
        document.getElementById('reg-error').innerText = 'Registracija nije uspela';
    }
}

document.getElementById('login-btn').addEventListener('click', () => {
    login(document.getElementById('login-email').value, document.getElementById('login-password').value);
});
document.getElementById('show-register').addEventListener('click', () => showView('register-view'));
document.getElementById('show-login').addEventListener('click', () => showView('auth-view'));
document.getElementById('register-btn').addEventListener('click', () => {
    register(document.getElementById('reg-email').value, document.getElementById('reg-username').value, document.getElementById('reg-password').value);
});
document.getElementById('logout-btn').addEventListener('click', () => {
    token = null;
    currentUser = null;
    if (ws) ws.close();
    showView('auth-view');
});
document.getElementById('exit-game-btn').addEventListener('click', () => {
    currentGameId = null;
    showView('lobby-view');
});

document.getElementById('send-chat').addEventListener('click', () => {
    const input = document.getElementById('chat-input');
    if (input.value.trim() && ws) {
        ws.send(JSON.stringify({ type: "chat", content: input.value }));
        input.value = '';
    }
});
document.getElementById('send-game-chat').addEventListener('click', () => {
    const input = document.getElementById('game-chat-input');
    if (input.value.trim() && ws && currentGameId) {
        ws.send(JSON.stringify({ type: "game_chat", game_id: currentGameId, content: input.value }));
        input.value = '';
    }
});

showView('auth-view');