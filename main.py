import sqlite3
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def init_db():
    try:
        conn = sqlite3.connect("vasyochat.db")
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, pin TEXT)")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT, receiver TEXT, content TEXT, 
                msg_type TEXT DEFAULT 'text', is_deleted INTEGER DEFAULT 0
            )
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        print("DB Hatası:", e)

init_db()

class RegisterReq(BaseModel):
    username: str
    pin: str

class SendReq(BaseModel):
    sender: str
    receiver: str
    content: str
    msg_type: str = "text"

class RestoreReq(BaseModel):
    username: str
    pin: str

@app.post("/api/register")
def register(req: RegisterReq):
    u = req.username.strip().lower()
    if not u.startswith("@"): u = "@" + u
    try:
        conn = sqlite3.connect("vasyochat.db")
        cursor = conn.cursor()
        cursor.execute("SELECT pin FROM users WHERE username = ?", (u,))
        user = cursor.fetchone()
        if user:
            if user[0] != req.pin:
                conn.close()
                raise HTTPException(status_code=400, detail="Hatalı PIN! Bu kullanıcı adı başka bir şifreyle kayıtlı.")
        else:
            cursor.execute("INSERT INTO users (username, pin) VALUES (?, ?)", (u, req.pin))
            conn.commit()
        conn.close()
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "ok", "username": u}

@app.get("/api/check-user/{username}")
def check_user(username: str):
    u = username.strip().lower()
    if not u.startswith("@"): u = "@" + u
    conn = sqlite3.connect("vasyochat.db")
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM users WHERE username = ?", (u,))
    user = cursor.fetchone()
    conn.close()
    if not user:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı!")
    return {"status": "exists", "username": u}

@app.post("/api/send")
def send_msg(req: SendReq):
    conn = sqlite3.connect("vasyochat.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO messages (sender, receiver, content, msg_type) VALUES (?, ?, ?, ?)", 
                   (req.sender, req.receiver, req.content, req.msg_type))
    conn.commit()
    conn.close()
    return {"status": "sent"}

@app.get("/api/messages/{user1}/{user2}")
def get_messages(user1: str, user2: str):
    conn = sqlite3.connect("vasyochat.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, sender, receiver, content, msg_type FROM messages 
        WHERE is_deleted = 0 AND ((sender = ? AND receiver = ?) OR (sender = ? AND receiver = ?))
        ORDER BY id ASC
    """, (user1, user2, user2, user1))
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "sender": r[1], "receiver": r[2], "content": r[3], "msg_type": r[4]} for r in rows]

@app.post("/api/delete-msg/{msg_id}")
def delete_msg(msg_id: int):
    conn = sqlite3.connect("vasyochat.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE messages SET is_deleted = 1 WHERE id = ?", (msg_id,))
    conn.commit()
    conn.close()
    return {"status": "deleted"}

@app.post("/api/restore")
def restore_msgs(req: RestoreReq):
    conn = sqlite3.connect("vasyochat.db")
    cursor = conn.cursor()
    cursor.execute("SELECT pin FROM users WHERE username = ?", (req.username,))
    user = cursor.fetchone()
    if not user or user[0] != req.pin:
        conn.close()
        raise HTTPException(status_code=400, detail="Hatalı PIN!")
    cursor.execute("UPDATE messages SET is_deleted = 0 WHERE sender = ? OR receiver = ?", (req.username, req.username))
    conn.commit()
    conn.close()
    return {"status": "restored"}

@app.get("/", response_class=HTMLResponse)
def index():
    return """
<!DOCTYPE html>
<html lang="tr" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VasyoChat</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
</head>
<body class="bg-slate-950 text-slate-100 h-screen flex flex-col font-sans select-none overflow-hidden">

    <div id="login-box" class="flex-1 flex items-center justify-center p-4 bg-slate-950">
        <div class="bg-slate-900 border border-slate-800 p-8 rounded-2xl w-full max-w-md shadow-2xl text-center">
            <h1 class="text-3xl font-bold text-indigo-400 mb-2">VasyoChat</h1>
            <p class="text-xs text-slate-400 mb-6">Güvenli Mesajlaşma</p>
            <input type="text" id="reg-user" placeholder="@kullaniciadi" class="w-full bg-slate-950 border border-slate-800 p-3 rounded-xl mb-3 text-sm focus:outline-none focus:border-indigo-500">
            <input type="password" id="reg-pin" placeholder="PIN Kodu" class="w-full bg-slate-950 border border-slate-800 p-3 rounded-xl mb-5 text-sm focus:outline-none focus:border-indigo-500">
            <button onclick="doRegister()" class="w-full bg-indigo-600 hover:bg-indigo-500 font-bold py-3 rounded-xl text-sm transition">Giriş Yap / Kaydol</button>
        </div>
    </div>

    <div id="app-box" class="flex-1 flex hidden h-full overflow-hidden">
        <div class="w-80 border-r border-slate-800 flex flex-col bg-slate-900">
            <div class="p-4 border-b border-slate-800 flex justify-between items-center">
                <span id="my-name" class="font-bold text-indigo-400 text-sm"></span>
                <button onclick="openVault()" class="text-xs bg-red-950 text-red-400 border border-red-900 px-3 py-1.5 rounded-lg">Kasa</button>
            </div>
            <div class="p-3 border-b border-slate-800 flex gap-2">
                <input type="text" id="add-target" placeholder="@kullaniciadi ekle..." class="flex-1 bg-slate-950 border border-slate-800 p-2 rounded-lg text-xs focus:outline-none">
                <button onclick="addUser()" class="bg-indigo-600 px-3 py-1 rounded-lg text-xs font-bold">+</button>
            </div>
            <div id="user-list" class="flex-1 overflow-y-auto divide-y divide-slate-800/40"></div>
        </div>

        <div class="flex-1 flex flex-col bg-slate-950">
            <div id="chat-header" class="p-4 border-b border-slate-800 font-semibold text-sm text-slate-300">Sohbet seçin</div>
            <div id="msg-flow" class="flex-1 p-4 overflow-y-auto space-y-3"></div>
            <div id="input-bar" class="p-3 border-t border-slate-800 flex gap-2 items-center bg-slate-900 hidden">
                <input type="text" id="msg-input" placeholder="Mesaj yazın..." onkeypress="if(event.key==='Enter') sendText()" class="flex-1 bg-slate-950 border border-slate-800 p-3 rounded-xl text-sm focus:outline-none">
                <button onclick="sendText()" class="bg-indigo-600 px-5 py-3 rounded-xl font-bold text-sm">Gönder</button>
            </div>
        </div>
    </div>

    <div id="vault-modal" class="fixed inset-0 bg-black/80 hidden flex items-center justify-center p-4 z-50">
        <div class="bg-slate-900 border border-slate-800 p-6 rounded-2xl w-full max-w-sm">
            <h2 class="text-lg font-bold text-red-400 mb-2">Silinen Mesajları Kurtar</h2>
            <input type="password" id="vault-pin-input" placeholder="PIN Kodunuz" class="w-full bg-slate-950 border border-slate-800 p-3 rounded-xl text-sm mb-4 focus:outline-none">
            <div class="flex justify-end gap-2">
                <button onclick="restoreAll()" class="bg-indigo-600 text-xs px-4 py-2 rounded-xl font-bold">Kurtar</button>
                <button onclick="closeVault()" class="bg-slate-800 text-xs px-4 py-2 rounded-xl">Kapat</button>
            </div>
        </div>
    </div>

    <script>
        let me = localStorage.getItem('v_user') || null;
        let activeTarget = null;

        if(me) { showApp(); }

        async function doRegister() {
            let u = document.getElementById('reg-user').value.trim();
            let p = document.getElementById('reg-pin').value.trim();
            if(!u || !p) { alert("Boş bırakma!"); return; }
            
            try {
                let res = await fetch('/api/register', { 
                    method: 'POST', 
                    headers: {'Content-Type': 'application/json'}, 
                    body: JSON.stringify({username: u, pin: p}) 
                });
                
                let text = await res.text();
                let data;
                try {
                    data = JSON.parse(text);
                } catch(e) {
                    alert("Sunucu Hatası: " + text);
                    return;
                }

                if(res.ok) { 
                    localStorage.setItem('v_user', data.username); 
                    me = data.username; 
                    showApp(); 
                } else {
                    alert(data.detail || "Giriş yapılırken hata oluştu.");
                }
            } catch(err) {
                alert("Bağlantı hatası oluştu.");
            }
        }

        function showApp() {
            document.getElementById('login-box').classList.add('hidden');
            document.getElementById('app-box').classList.remove('hidden');
            document.getElementById('my-name').innerText = me;
            loadContacts();
            setInterval(fetchMessages, 2000);
        }

        async function addUser() {
            let target = document.getElementById('add-target').value.trim();
            if(!target) return;
            let res = await fetch('/api/check-user/' + encodeURIComponent(target));
            if(!res.ok) { alert("Kullanıcı bulunamadı!"); return; }
            let data = await res.json();
            let contacts = JSON.parse(localStorage.getItem('v_contacts_' + me) || '[]');
            if(!contacts.includes(data.username)) { 
                contacts.push(data.username); 
                localStorage.setItem('v_contacts_' + me, JSON.stringify(contacts)); 
                loadContacts(); 
            }
            document.getElementById('add-target').value = '';
        }

        function loadContacts() {
            let contacts = JSON.parse(localStorage.getItem('v_contacts_' + me) || '[]');
            let list = document.getElementById('user-list');
            list.innerHTML = '';
            contacts.forEach(c => {
                let div = document.createElement('div');
                div.className = "p-3 hover:bg-slate-800 cursor-pointer text-sm font-medium flex justify-between items-center";
                div.innerHTML = `<span>${c}</span>`;
                div.onclick = () => selectChat(c);
                list.appendChild(div);
            });
        }

        function selectChat(target) {
            activeTarget = target;
            document.getElementById('chat-header').innerText = target + " ile Sohbet";
            document.getElementById('input-bar').classList.remove('hidden');
            fetchMessages();
        }

        async function sendText() {
            let input = document.getElementById('msg-input');
            let txt = input.value.trim();
            if(!txt || !activeTarget) return;
            await fetch('/api/send', { 
                method: 'POST', 
                headers: {'Content-Type': 'application/json'}, 
                body: JSON.stringify({sender: me, receiver: activeTarget, content: txt, msg_type: 'text'}) 
            });
            input.value = ''; 
            fetchMessages();
        }

        async function fetchMessages() {
            if(!activeTarget) return;
            let res = await fetch(`/api/messages/${encodeURIComponent(me)}/${encodeURIComponent(activeTarget)}`);
            let msgs = await res.json();
            let flow = document.getElementById('msg-flow'); 
            flow.innerHTML = '';
            msgs.forEach(m => {
                let isMe = m.sender === me;
                flow.innerHTML += `<div class="flex ${isMe ? 'justify-end' : 'justify-start'}"><div class="p-3 rounded-xl max-w-xs text-sm ${isMe ? 'bg-indigo-600 text-white' : 'bg-slate-900 border border-slate-800'}">${m.content}</div></div>`;
            });
        }

        function openVault() { document.getElementById('vault-modal').classList.remove('hidden'); }
        function closeVault() { document.getElementById('vault-modal').classList.add('hidden'); }
        
        async function restoreAll() {
            let p = document.getElementById('vault-pin-input').value;
            let res = await fetch('/api/restore', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({username: me, pin: p}) });
            if(res.ok) { alert("Mesajlar kurtarıldı!"); closeVault(); fetchMessages(); } else { alert("Hatalı PIN!"); }
        }
    </script>
</body>
</html>
    """