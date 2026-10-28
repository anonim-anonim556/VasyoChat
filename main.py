import sqlite3
from fastapi import FastAPI, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse
import shutil
import os

app = FastAPI()

DB_FILE = "vasyochat_v2.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            pin TEXT,
            bio TEXT DEFAULT 'VasyoChat kullanıcısı',
            avatar TEXT DEFAULT 'https://i.imgur.com/6VBx3io.png'
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT,
            receiver TEXT,
            content TEXT,
            msg_type TEXT DEFAULT 'text',
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT,
            receiver TEXT,
            status TEXT DEFAULT 'pending'
        )
    """)
    conn.commit()
    conn.close()

init_db()

@app.get("/", response_class=HTMLResponse)
def home():
    return """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <title>VasyoChat - Telegram Style</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
</head>
<body class="bg-[#0f172a] text-slate-100 h-screen flex overflow-hidden font-sans select-none">

    <!-- SOL KENAR ÇUBUĞU -->
    <div class="w-80 bg-[#1e293b] border-r border-slate-700 flex flex-col">
        <div class="p-4 bg-[#0f172a] flex items-center justify-between border-b border-slate-700">
            <div class="flex items-center space-x-3 cursor-pointer" onclick="openProfileModal()">
                <img id="my-avatar" src="https://i.imgur.com/6VBx3io.png" class="w-10 h-10 rounded-full object-cover border border-indigo-500">
                <div>
                    <h3 id="my-username-display" class="font-bold text-sm">Giriş Yapılmadı</h3>
                    <span class="text-xs text-emerald-400">Çevrimiçi</span>
                </div>
            </div>
            <div class="flex items-center space-x-3">
                <button onclick="openRequestsModal()" class="text-slate-400 hover:text-indigo-400 text-sm relative" title="İstekler">
                    <i class="fa-solid fa-user-plus"></i>
                    <span id="req-badge" class="absolute -top-1 -right-1 bg-red-500 text-white text-[9px] w-4 h-4 rounded-full flex items-center justify-center hidden">0</span>
                </button>
                <button onclick="logout()" class="text-slate-400 hover:text-red-400 text-sm" title="Çıkış Yap"><i class="fa-solid fa-power-off"></i></button>
            </div>
        </div>

        <!-- @ İLE KİŞİ ARAMA ÇUBUĞU -->
        <div class="p-3">
            <div class="relative">
                <i class="fa-solid fa-search absolute left-3 top-3 text-slate-400 text-sm"></i>
                <input type="text" id="search-box" oninput="searchUsers()" placeholder="@kullaniciadi ara..." class="w-full bg-[#0f172a] text-sm rounded-xl pl-9 pr-4 py-2.5 focus:outline-none focus:ring-1 focus:ring-indigo-500 text-slate-200 placeholder-slate-500">
            </div>
        </div>

        <!-- ARAMA SONUÇLARI VEYA ARKADAŞ LİSTESİ -->
        <div id="user-list" class="flex-1 overflow-y-auto divide-y divide-slate-800/50"></div>
    </div>

    <!-- SAĞ ANA SOHBET EKRANI -->
    <div class="flex-1 flex flex-col bg-[#0b1329]">
        <div id="chat-header" class="h-16 bg-[#1e293b] border-b border-slate-700 px-6 flex items-center justify-between hidden">
            <div class="flex items-center space-x-3">
                <img id="active-chat-avatar" src="" class="w-10 h-10 rounded-full object-cover">
                <div>
                    <h3 id="active-chat-name" class="font-bold text-sm"></h3>
                    <span class="text-xs text-slate-400" id="active-chat-bio"></span>
                </div>
            </div>
        </div>

        <div id="chat-messages" class="flex-1 overflow-y-auto p-6 space-y-4 flex flex-col">
            <div class="m-auto text-center text-slate-500">
                <i class="fa-regular fa-comments text-5xl mb-2"></i>
                <p>Sohbet etmek için soldan birini seçin veya @ ile arayıp ekleyin.</p>
            </div>
        </div>

        <div id="chat-input-bar" class="p-4 bg-[#1e293b] border-t border-slate-700 flex items-center space-x-3 hidden">
            <label class="text-slate-400 hover:text-indigo-400 text-xl cursor-pointer px-2" title="Fotoğraf Gönder">
                <i class="fa-solid fa-image"></i>
                <input type="file" id="media-file-input" accept="image/*" onchange="sendMediaFile()" class="hidden">
            </label>
            <input type="text" id="message-input" onkeypress="checkEnter(event)" placeholder="Mesaj yazın..." class="flex-1 bg-[#0f172a] text-sm rounded-xl px-4 py-3 focus:outline-none focus:ring-1 focus:ring-indigo-500 text-slate-200 placeholder-slate-500">
            <button onclick="sendMessage()" class="bg-indigo-600 hover:bg-indigo-500 text-white px-5 py-3 rounded-xl font-medium transition flex items-center space-x-2">
                <span>Gönder</span>
                <i class="fa-solid fa-paper-plane text-xs"></i>
            </button>
        </div>
    </div>

    <!-- İSTEKLER MODALI -->
    <div id="requests-modal" class="fixed inset-0 bg-black/70 hidden flex items-center justify-center z-50">
        <div class="bg-[#1e293b] p-6 rounded-2xl w-96 border border-slate-700 space-y-4 shadow-2xl">
            <div class="flex justify-between items-center">
                <h3 class="text-lg font-bold">Arkadaşlık İstekleri</h3>
                <button onclick="closeRequestsModal()" class="text-slate-400 hover:text-white"><i class="fa-solid fa-xmark"></i></button>
            </div>
            <div id="requests-list" class="space-y-2 max-h-60 overflow-y-auto">
                <p class="text-xs text-slate-500 text-center py-4">Yeni istek yok.</p>
            </div>
        </div>
    </div>

    <!-- PROFIL MODALI -->
    <div id="profile-modal" class="fixed inset-0 bg-black/70 hidden flex items-center justify-center z-50">
        <div class="bg-[#1e293b] p-6 rounded-2xl w-96 border border-slate-700 space-y-4 shadow-2xl">
            <h3 class="text-lg font-bold">Profilini Düzenle</h3>
            <div class="text-center">
                <img id="modal-avatar-preview" src="" class="w-20 h-20 rounded-full mx-auto object-cover border-2 border-indigo-500 mb-2">
                <input type="text" id="edit-avatar-url" placeholder="Avatar Resim URL'si" class="w-full bg-[#0f172a] text-xs p-2 rounded-lg border border-slate-700 text-slate-300">
            </div>
            <div>
                <label class="text-xs text-slate-400">Biyografi</label>
                <input type="text" id="edit-bio" class="w-full bg-[#0f172a] text-sm p-2.5 rounded-lg border border-slate-700 text-slate-200 mt-1">
            </div>
            <div class="flex justify-end space-x-2 pt-2">
                <button onclick="closeProfileModal()" class="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-sm">İptal</button>
                <button onclick="saveProfile()" class="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-sm font-medium">Kaydet</button>
            </div>
        </div>
    </div>

    <!-- GİRİŞ MODALI -->
    <div id="auth-modal" class="fixed inset-0 bg-[#0f172a] z-50 flex items-center justify-center">
        <div class="bg-[#1e293b] p-8 rounded-2xl w-96 border border-slate-700 space-y-6 shadow-2xl text-center">
            <div class="text-indigo-500 text-4xl mb-2"><i class="fa-brands fa-telegram"></i></div>
            <h2 class="text-xl font-bold">VasyoChat'e Hoş Geldin</h2>
            <input type="text" id="auth-username" placeholder="Kullanıcı Adı" class="w-full bg-[#0f172a] text-sm p-3 rounded-xl border border-slate-700 text-slate-200">
            <input type="password" id="auth-pin" placeholder="Şifre / PIN" class="w-full bg-[#0f172a] text-sm p-3 rounded-xl border border-slate-700 text-slate-200">
            <button onclick="loginUser()" class="w-full bg-indigo-600 hover:bg-indigo-500 py-3 rounded-xl font-bold transition">Giriş Yap / Kaydol</button>
        </div>
    </div>

    <script>
        let currentUser = localStorage.getItem("vasyo_user") || null;
        let currentTarget = null;

        window.onload = () => {
            if (!currentUser) {
                document.getElementById("auth-modal").classList.remove("hidden");
            } else {
                document.getElementById("auth-modal").classList.add("hidden");
                initApp();
            }
        };

        async function loginUser() {
            let u = document.getElementById("auth-username").value.trim();
            let p = document.getElementById("auth-pin").value.trim();
            if(!u || !p) return alert("Kullanıcı adı ve şifre gir!");
            
            let res = await fetch("/api/login", {
                method: "POST",
                headers: {"Content-Type": "application/x-www-form-urlencoded"},
                body: `username=${encodeURIComponent(u)}&pin=${encodeURIComponent(p)}`
            });
            let data = await res.json();
            if(data.status === "ok") {
                localStorage.setItem("vasyo_user", u);
                currentUser = u;
                document.getElementById("auth-modal").classList.add("hidden");
                initApp();
            } else {
                alert("Giriş başarısız!");
            }
        }

        function logout() {
            localStorage.removeItem("vasyo_user");
            location.reload();
        }

        async function initApp() {
            document.getElementById("my-username-display").innerText = currentUser;
            await loadFriends();
            await checkRequestsCount();
            setInterval(() => {
                loadFriends();
                checkRequestsCount();
                if(currentTarget) loadMessages();
            }, 4000);
        }

        async function loadFriends() {
            let res = await fetch(`/api/friends?username=${encodeURIComponent(currentUser)}`);
            let friends = await res.json();
            let list = document.getElementById("user-list");
            
            // Eğer arama çubuğu boşsa arkadaş listesini göster
            let query = document.getElementById("search-box").value.trim();
            if(!query.startsWith("@")) {
                list.innerHTML = "";
                friends.forEach(u => {
                    if(u.username === currentUser) {
                        document.getElementById("my-avatar").src = u.avatar;
                        return;
                    }
                    let div = document.createElement("div");
                    div.className = `flex items-center space-x-3 p-3 cursor-pointer hover:bg-slate-800/60 transition ${currentTarget === u.username ? 'bg-slate-800' : ''}`;
                    div.onclick = () => selectChat(u.username, u.avatar, u.bio);
                    div.innerHTML = `
                        <img src="${u.avatar}" class="w-11 h-11 rounded-full object-cover">
                        <div class="flex-1 min-w-0">
                            <h4 class="font-bold text-sm truncate">${u.username}</h4>
                            <p class="text-xs text-slate-400 truncate">${u.bio}</p>
                        </div>
                    `;
                    list.appendChild(div);
                });
            }
        }

        async function searchUsers() {
            let query = document.getElementById("search-box").value.trim();
            let list = document.getElementById("user-list");
            
            if(!query.startsWith("@") || query.length < 2) {
                if(query === "") loadFriends();
                return;
            }

            let searchterm = query.substring(1);
            let res = await fetch(`/api/search-user?query=${encodeURIComponent(searchterm)}¤t=${encodeURIComponent(currentUser)}`);
            let user = await res.json();

            list.innerHTML = "";
            if(user.error) {
                list.innerHTML = `<div class="p-4 text-xs text-slate-500 text-center">Kullanıcı bulunamadı.</div>`;
            } else {
                let div = document.createElement("div");
                div.className = "flex items-center justify-between p-3 bg-slate-800/40";
                div.innerHTML = `
                    <div class="flex items-center space-x-3">
                        <img src="${user.avatar}" class="w-10 h-10 rounded-full object-cover">
                        <div>
                            <h4 class="font-bold text-sm">${user.username}</h4>
                            <p class="text-xs text-slate-400">${user.bio}</p>
                        </div>
                    </div>
                    <button onclick="sendRequest('${user.username}')" class="bg-indigo-600 hover:bg-indigo-500 text-white text-xs px-3 py-1.5 rounded-lg font-medium">Ekle</button>
                `;
                list.appendChild(div);
            }
        }

        async function sendRequest(receiver) {
            let res = await fetch("/api/send-request", {
                method: "POST",
                headers: {"Content-Type": "application/x-www-form-urlencoded"},
                body: `sender=${encodeURIComponent(currentUser)}&receiver=${encodeURIComponent(receiver)}`
            });
            let data = await res.json();
            alert(data.message);
            document.getElementById("search-box").value = "";
            loadFriends();
        }

        async function checkRequestsCount() {
            let res = await fetch(`/api/get-requests?username=${encodeURIComponent(currentUser)}`);
            let reqs = await res.json();
            let badge = document.getElementById("req-badge");
            if(reqs.length > 0) {
                badge.innerText = reqs.length;
                badge.classList.remove("hidden");
            } else {
                badge.classList.add("hidden");
            }
        }

        async function openRequestsModal() {
            let res = await fetch(`/api/get-requests?username=${encodeURIComponent(currentUser)}`);
            let reqs = await res.json();
            let rList = document.getElementById("requests-list");
            rList.innerHTML = "";
            
            if(reqs.length === 0) {
                rList.innerHTML = `<p class="text-xs text-slate-500 text-center py-4">Yeni istek yok.</p>`;
            } else {
                reqs.forEach(r => {
                    let div = document.createElement("div");
                    div.className = "flex items-center justify-between bg-[#0f172a] p-3 rounded-xl border border-slate-700";
                    div.innerHTML = `
                        <div class="flex items-center space-x-3">
                            <img src="${r.avatar}" class="w-9 h-9 rounded-full object-cover">
                            <span class="text-sm font-bold">${r.sender}</span>
                        </div>
                        <div class="space-x-1">
                            <button onclick="respondRequest(${r.id}, 'accept')" class="bg-emerald-600 hover:bg-emerald-500 text-white text-xs px-3 py-1.5 rounded-lg">Kabul Et</button>
                            <button onclick="respondRequest(${r.id}, 'reject')" class="bg-red-600 hover:bg-red-500 text-white text-xs px-3 py-1.5 rounded-lg">Reddet</button>
                        </div>
                    `;
                    rList.appendChild(div);
                });
            }
            document.getElementById("requests-modal").classList.remove("hidden");
        }

        function closeRequestsModal() { document.getElementById("requests-modal").classList.add("hidden"); }

        async function respondRequest(id, action) {
            await fetch("/api/respond-request", {
                method: "POST",
                headers: {"Content-Type": "application/x-www-form-urlencoded"},
                body: `id=${id}&action=${action}`
            });
            openRequestsModal();
            loadFriends();
        }

        function selectChat(username, avatar, bio) {
            currentTarget = username;
            document.getElementById("chat-header").classList.remove("hidden");
            document.getElementById("chat-input-bar").classList.remove("hidden");
            document.getElementById("active-chat-name").innerText = username;
            document.getElementById("active-chat-avatar").src = avatar;
            document.getElementById("active-chat-bio").innerText = bio;
            loadMessages();
        }

        async function sendMessage() {
            let input = document.getElementById("message-input");
            let text = input.value.trim();
            if(!text || !currentTarget) return;

            await fetch("/api/send", {
                method: "POST",
                headers: {"Content-Type": "application/x-www-form-urlencoded"},
                body: `sender=${encodeURIComponent(currentUser)}&receiver=${encodeURIComponent(currentTarget)}&content=${encodeURIComponent(text)}&msg_type=text`
            });
            input.value = "";
            loadMessages();
        }

        async function sendMediaFile() {
            let fileInput = document.getElementById("media-file-input");
            if(fileInput.files.length === 0 || !currentTarget) return;
            let file = fileInput.files[0];
            let reader = new FileReader();
            reader.readAsDataURL(file);
            reader.onloadend = async () => {
                await fetch("/api/send", {
                    method: "POST",
                    headers: {"Content-Type": "application/x-www-form-urlencoded"},
                    body: `sender=${encodeURIComponent(currentUser)}&receiver=${encodeURIComponent(currentTarget)}&content=${encodeURIComponent(reader.result)}&msg_type=image`
                });
                loadMessages();
            };
        }

        async function deleteMessage(msgId) {
            if(!confirm("Bu mesajı silmek istiyor musun?")) return;
            await fetch(`/api/delete-message?id=${msgId}`, { method: "POST" });
            loadMessages();
        }

        async function loadMessages() {
            if(!currentTarget) return;
            let res = await fetch(`/api/messages?user1=${encodeURIComponent(currentUser)}&user2=${encodeURIComponent(currentTarget)}`);
            let msgs = await res.json();
            let box = document.getElementById("chat-messages");
            box.innerHTML = "";
            msgs.forEach(m => {
                let isMe = m.sender === currentUser;
                let div = document.createElement("div");
                div.className = `flex flex-col ${isMe ? 'items-end' : 'items-start'} my-1 group`;
                
                let contentHtml = "";
                if(m.msg_type === 'text') {
                    contentHtml = `<p class="text-sm">${m.content}</p>`;
                } else if(m.msg_type === 'image') {
                    contentHtml = `<img src="${m.content}" class="max-w-xs rounded-xl cursor-pointer" onclick="window.open(this.src)">`;
                }

                let deleteBtn = isMe ? `<button onclick="deleteMessage(${m.id})" class="text-[10px] text-red-400 hover:text-red-300 ml-2 hidden group-hover:inline" title="Sil"><i class="fa-solid fa-trash"></i></button>` : "";

                div.innerHTML = `
                    <div class="max-w-md px-4 py-2.5 rounded-2xl ${isMe ? 'bg-indigo-600 text-white rounded-br-none' : 'bg-[#1e293b] text-slate-100 rounded-bl-none'} shadow-md relative">
                        ${contentHtml}
                        <div class="flex justify-end items-center mt-1 space-x-1">
                            <span class="text-[10px] ${isMe ? 'text-indigo-200' : 'text-slate-400'}">${m.timestamp.slice(11,16)}</span>
                            ${deleteBtn}
                        </div>
                    </div>
                `;
                box.appendChild(div);
            });
            box.scrollTop = box.scrollHeight;
        }

        function checkEnter(e) { if(e.key === 'Enter') sendMessage(); }

        async function openProfileModal() {
            let res = await fetch(`/api/search-user?query=${encodeURIComponent(currentUser)}¤t=`);
            let me = await res.json();
            if(me) {
                document.getElementById("edit-avatar-url").value = me.avatar;
                document.getElementById("edit-bio").value = me.bio;
                document.getElementById("modal-avatar-preview").src = me.avatar;
            }
            document.getElementById("profile-modal").classList.remove("hidden");
        }
        function closeProfileModal() { document.getElementById("profile-modal").classList.add("hidden"); }

        async function saveProfile() {
            let avatar = document.getElementById("edit-avatar-url").value;
            let bio = document.getElementById("edit-bio").value;
            await fetch("/api/update-profile", {
                method: "POST",
                headers: {"Content-Type": "application/x-www-form-urlencoded"},
                body: `username=${encodeURIComponent(currentUser)}&avatar=${encodeURIComponent(avatar)}&bio=${encodeURIComponent(bio)}`
            });
            closeProfileModal();
            loadFriends();
        }
    </script>
</body>
</html>
    """

@app.post("/api/login")
def login(username: str = Form(...), pin: str = Form(...)):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    if not user:
        cursor.execute("INSERT INTO users (username, pin) VALUES (?, ?)", (username, pin))
        conn.commit()
    conn.close()
    return {"status": "ok"}

@app.get("/api/search-user")
def search_user(query: str, current: str):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT username, bio, avatar FROM users WHERE username = ?", (query,))
    r = cursor.fetchone()
    conn.close()
    if not r or r[0] == current:
        return {"error": "not found"}
    return {"username": r[0], "bio": r[1], "avatar": r[2]}

@app.post("/api/send-request")
def send_request(sender: str = Form(...), receiver: str = Form(...)):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM requests WHERE (sender = ? AND receiver = ?) OR (sender = ? AND receiver = ?)", (sender, receiver, receiver, sender))
    existing = cursor.fetchone()
    if existing:
        conn.close()
        return {"message": "Zaten istek atılmış veya arkadaşsınız!"}
    cursor.execute("INSERT INTO requests (sender, receiver, status) VALUES (?, ?, 'pending')", (sender, receiver))
    conn.commit()
    conn.close()
    return {"message": "Arkadaşlık isteği gönderildi!"}

@app.get("/api/get-requests")
def get_requests(username: str):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, sender FROM requests WHERE receiver = ? AND status = 'pending'", (username,))
    rows = cursor.fetchall()
    result = []
    for r in rows:
        cursor.execute("SELECT avatar FROM users WHERE username = ?", (r[1],))
        u = cursor.fetchone()
        avatar = u[0] if u else "https://i.imgur.com/6VBx3io.png"
        result.append({"id": r[0], "sender": r[1], "avatar": avatar})
    conn.close()
    return result

@app.post("/api/respond-request")
def respond_request(id: int = Form(...), action: str = Form(...)):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    if action == 'accept':
        cursor.execute("UPDATE requests SET status = 'accepted' WHERE id = ?", (id,))
    else:
        cursor.execute("DELETE FROM requests WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return {"status": "ok"}

@app.get("/api/friends")
def get_friends(username: str):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT sender, receiver FROM requests 
        WHERE (sender = ? OR receiver = ?) AND status = 'accepted'
    """, (username, username))
    rows = cursor.fetchall()
    friend_names = set()
    for r in rows:
        if r[0] == username:
            friend_names.add(r[1])
        else:
            friend_names.add(r[0])
    
    friends = []
    for f in friend_names:
        cursor.execute("SELECT username, bio, avatar FROM users WHERE username = ?", (f,))
        u = cursor.fetchone()
        if u:
            friends.append({"username": u[0], "bio": u[1], "avatar": u[2]})
    conn.close()
    return friends

@app.post("/api/update-profile")
def update_profile(username: str = Form(...), avatar: str = Form(...), bio: str = Form(...)):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET avatar = ?, bio = ? WHERE username = ?", (avatar, bio, username))
    conn.commit()
    conn.close()
    return {"status": "ok"}

@app.post("/api/send")
def send_message(sender: str = Form(...), receiver: str = Form(...), content: str = Form(...), msg_type: str = Form("text")):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO messages (sender, receiver, content, msg_type) VALUES (?, ?, ?, ?)", (sender, receiver, content, msg_type))
    conn.commit()
    conn.close()
    return {"status": "ok"}

@app.post("/api/delete-message")
def delete_message(id: int):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return {"status": "ok"}

@app.get("/api/messages")
def get_messages(user1: str, user2: str):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, sender, receiver, content, msg_type, timestamp FROM messages 
        WHERE (sender = ? AND receiver = ?) OR (sender = ? AND receiver = ?)
        ORDER BY id ASC
    """, (user1, user2, user2, user1))
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "sender": r[1], "receiver": r[2], "content": r[3], "msg_type": r[4], "timestamp": r[5]} for r in rows]