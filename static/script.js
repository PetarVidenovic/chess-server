// ==================== GLOBALNE PROMENLJIVE ====================
let token = null;
let currentUser = null;
let ws = null;
let currentGameId = null;
let myColor = null; // "white" ili "black"
let game = null;

let onlineUsers = [];
let pendingChallenges = [];

let lastSentChallengeTo = null;
let lastReceivedChallengeFrom = null;

// SAT (90 minuta = 5400 sekundi)
let whiteTime = 5400;   // sekunde
let blackTime = 5400;
let clockInterval = null;
let currentTurnTimeStart = null;

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
        if (clockInterval) clearInterval(clockInterval);
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
        lastReceivedChallengeFrom = data.from_id;
        pendingChallenges.push({
            challenge_id: data.challenge_id,
            from_username: data.from_username,
            from_id: data.from_id
        });
        renderChallenges();
    }
    else if (type === "challenge_accepted" || type === "match_found") {
        currentGameId = data.game_id;
        // Odredi boju lokalno ili sa servera
        const opponentId = data.opponent_id;
        if (lastSentChallengeTo === opponentId) myColor = 'white';
        else if (lastReceivedChallengeFrom === opponentId) myColor = 'black';
        else myColor = data.my_color || data.color;
        lastSentChallengeTo = null;
        lastReceivedChallengeFrom = null;
        startGame(data.opponent);
    }
    else if (type === "move" || type === "game_state") {
        if (data.game_id === currentGameId && data.fen) {
            // Zaustavi trenutni sat
            if (clockInterval) clearInterval(clockInterval);
            // Ažuriraj tablu
            game = new Chess(data.fen);
            drawBoard();
            updateGameStatus();
            // Promeni sat: switch turn
            const turn = game.turn();
            if (turn === 'w') {
                if (clockInterval) startClock('white');
            } else {
                if (clockInterval) startClock('black');
            }
            updateClockDisplay();
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
            if (clockInterval) clearInterval(clockInterval);
            currentGameId = null;
        }
    }
}

// Sat
function startClock(color) {
    if (clockInterval) clearInterval(clockInterval);
    const startTime = Date.now();
    clockInterval = setInterval(() => {
        const elapsed = (Date.now() - startTime) / 1000;
        if (color === 'white') {
            whiteTime = Math.max(0, whiteTime - elapsed);
            if (whiteTime <= 0) { whiteTime = 0; clearInterval(clockInterval); gameOverByTime('white'); }
        } else {
            blackTime = Math.max(0, blackTime - elapsed);
            if (blackTime <= 0) { blackTime = 0; clearInterval(clockInterval); gameOverByTime('black'); }
        }
        updateClockDisplay();
    }, 100);
}
function updateClockDisplay() {
    const format = (sec) => {
        const mins = Math.floor(sec / 60);
        const remainSec = sec % 60;
        return `${mins}:${remainSec < 10 ? '0'+remainSec : remainSec}`;
    };
    document.getElementById('white-time').innerText = format(whiteTime);
    document.getElementById('black-time').innerText = format(blackTime);
}
function gameOverByTime(color) {
    // color je koji je ostao bez vremena
    if (!currentGameId) return;
    const winner = (color === 'white') ? 'black' : 'white';
    const result = (winner === myColor) ? "Pobeda (vreme)!" : "Poraz (vreme)";
    showResultModal(result, "Protivnik je ostao bez vremena.");
    // Pošalji resign poruku serveru?
    ws.send(JSON.stringify({ type: "resign", game_id: currentGameId }));
    currentGameId = null;
}

// ==================== LOBBY ====================
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
                alert("WebSocket nije povezan.");
                return;
            }
            const opponentId = parseInt(btn.getAttribute('data-id'));
            lastSentChallengeTo = opponentId;
            ws.send(JSON.stringify({ type: "challenge", opponent_id: opponentId }));
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
            const fromId = parseInt(btn.getAttribute('data-from'));
            if (!lastReceivedChallengeFrom) lastReceivedChallengeFrom = fromId;
            ws.send(JSON.stringify({
                type: "accept_challenge",
                challenge_id: challengeId,
                from_id: fromId
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

// ==================== TURNIRI ====================
async function loadTournaments() {
    try {
        const tournaments = await apiRequest('GET', '/tournaments/');
        const container = document.getElementById('tournament-list');
        container.innerHTML = '';
        for (let t of tournaments) {
            const card = document.createElement('div');
            card.className = 'tournament-card';
            card.innerHTML = `
                <h3>${t.name}</h3>
                <p>Status: ${t.status}</p>
                <p>Broj igrača: ${t.players_count}</p>
                <button class="join-tournament" data-id="${t.id}">Prijavi se</button>
                <button class="view-tournament" data-id="${t.id}" style="margin-left:8px;">Detalji</button>
            `;
            container.appendChild(card);
        }
        document.querySelectorAll('.join-tournament').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const tourId = btn.getAttribute('data-id');
                await apiRequest('POST', `/tournaments/${tourId}/join`, {});
                alert('Prijavljeni ste na turnir');
                loadTournaments();
            });
        });
        document.querySelectorAll('.view-tournament').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const tourId = btn.getAttribute('data-id');
                await showTournamentDetails(tourId);
            });
        });
    } catch (err) { console.error(err); }
}

async function showTournamentDetails(tourId) {
    try {
        const data = await apiRequest('GET', `/tournaments/${tourId}/details`);
        document.getElementById('tournament-name').innerText = data.name;
        let matchesHtml = '<h4>Mečevi</h4><ul>';
        for (let m of data.matches) {
            matchesHtml += `<li>${m.player1} vs ${m.player2} - Rezultat: ${m.result || 'nije odigran'}</li>`;
        }
        matchesHtml += '</ul>';
        document.getElementById('tournament-matches').innerHTML = matchesHtml;
        let standingsHtml = '<h4>Tabela</h4><table class="standings-table"><tr><th>Igrač</th><th>Pobede</th><th>Porazi</th><th>Remiji</th><th>Bodovi</th></tr>';
        for (let p of data.standings) {
            standingsHtml += `<tr><td>${p.username}</td><td>${p.wins}</td><td>${p.losses}</td><td>${p.draws}</td><td>${p.points}</td></tr>`;
        }
        standingsHtml += '</table>';
        document.getElementById('tournament-standings').innerHTML = standingsHtml;
        document.getElementById('tournament-detail').style.display = 'block';
    } catch (err) { alert('Ne mogu učitati detalje turnira'); }
}

// ==================== PROFIL ====================
async function loadProfile() {
    try {
        const user = await apiRequest('GET', '/users/me');
        document.getElementById('profile-username').innerText = user.username;
        document.getElementById('profile-rating').innerText = user.rating || 1200;
        document.getElementById('profile-wins').innerText = user.wins || 0;
        document.getElementById('profile-losses').innerText = user.losses || 0;
        document.getElementById('profile-draws').innerText = user.draws || 0;
        const total = (user.wins || 0) + (user.losses || 0) + (user.draws || 0);
        document.getElementById('profile-total').innerText = total;
        if (user.profile_picture) {
            document.getElementById('profile-pic').src = user.profile_picture;
        }
    } catch (err) { console.error(err); }
}

// ==================== ŠAHOVSKA TABLA (SVG figure) ====================
function startGame(opponentName) {
    game = new Chess();
    whiteTime = 5400;
    blackTime = 5400;
    updateClockDisplay();
    if (clockInterval) clearInterval(clockInterval);
    // Ko prvi igra? Ako je myColor = white, startuj beli sat
    if (myColor === 'white') startClock('white');
    else startClock('black');
    showView('game-view');
    document.getElementById('game-opponent').innerText = `Protivnik: ${opponentName}`;
    setTimeout(() => {
        drawBoard();
        updateGameStatus();
    }, 50);
}

function getPieceCodeSVG(type, color) {
    const map = {
        'k': color === 'w' ? 'wK' : 'bK',
        'q': color === 'w' ? 'wQ' : 'bQ',
        'r': color === 'w' ? 'wR' : 'bR',
        'b': color === 'w' ? 'wB' : 'bB',
        'n': color === 'w' ? 'wN' : 'bN',
        'p': color === 'w' ? 'wP' : 'bP'
    };
    return map[type];
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
            if (piece) {
                const img = document.createElement('img');
                const code = getPieceCodeSVG(piece.type, piece.color);
                img.src = `https://lichess1.org/assets/piece/cburnett/${code}.svg`;
                img.style.width = '100%';
                img.style.height = '100%';
                img.style.objectFit = 'contain';
                square.appendChild(img);
            }
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
    const turn = game.turn();
    let myTurn = (myColor === 'white' && turn === 'w') || (myColor === 'black' && turn === 'b');
    if (!myTurn) { alert("Niste na potezu!"); return; }
    const row = parseInt(squareDiv.dataset.row);
    const col = parseInt(squareDiv.dataset.col);
    const file = String.fromCharCode(97 + col);
    const rank = 8 - row;
    const square = file + rank;
    if (selectedSquare === null) {
        const piece = game.get(square);
        if (piece && ((myColor === 'white' && piece.color === 'w') || (myColor === 'black' && piece.color === 'b'))) {
            selectedSquare = square;
            highlightSelectedSquare(row, col);
        } else alert("To nije vaša figura!");
    } else {
        const move = game.move({ from: selectedSquare, to: square, promotion: 'q' });
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
            // Sat se menja na drugu stranu (automatski preko handleWebSocketMessage)
        } else alert("Nelegalan potez");
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

// ==================== AUTH I INICIJALIZACIJA ====================
async function login(email, password) {
    try {
        const data = await apiRequest('POST', '/auth/login', { email, password });
        token = data.access_token;
        const userData = await apiRequest('GET', '/users/me');
        currentUser = userData;
        connectWebSocket();
        document.getElementById('main-interface').style.display = 'block';
        showView('lobby-view');
        document.getElementById('lobby-error').innerText = '';
        loadProfile();
        loadTournaments();
        // Navigacija
        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const viewId = btn.getAttribute('data-view');
                showView(viewId);
                if (viewId === 'tournament-view') loadTournaments();
                if (viewId === 'profile-view') loadProfile();
            });
        });
        document.getElementById('close-tournament').addEventListener('click', () => {
            document.getElementById('tournament-detail').style.display = 'none';
        });
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
    document.getElementById('main-interface').style.display = 'none';
    showView('auth-view');
});
document.getElementById('exit-game-btn').addEventListener('click', () => {
    currentGameId = null;
    if (clockInterval) clearInterval(clockInterval);
    showView('lobby-view');
});
// Chat
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
// Profile picture upload
document.getElementById('upload-pic-btn').addEventListener('click', () => {
    document.getElementById('profile-pic-input').click();
});
document.getElementById('profile-pic-input').addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const formData = new FormData();
    formData.append('profile_picture', file);
    try {
        const response = await fetch('/users/me/profile_picture', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` },
            body: formData
        });
        if (response.ok) {
            alert('Slika postavljena');
            loadProfile();
        } else alert('Greška pri upload-u');
    } catch (err) { alert('Greška: ' + err); }
});

showView('auth-view');