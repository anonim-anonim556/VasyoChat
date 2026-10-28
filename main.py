import sqlite3
from fastapi import FastAPI, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse
import shutil
import os

app = FastAPI()

DB_FILE = "vasyochat_anonim.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            pin TEXT,
            bio TEXT DEFAULT 'Anonim VasyoChat Kullanıcısı',
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
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stickers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            creator TEXT,
            url TEXT
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
    <title>VasyoChat - Anonim Sohbet</title>
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
                    <span class="text-xs text-emerald-400">Anonim Çevrimiçi</span>
                </div>
            </div>
            <div class="flex items-center space-x-2">
                <button onclick="openRequestsModal()" class="text-slate-400 hover:text-indigo-400 text-sm relative p-2" title="İstekler">
                    <i class="fa-solid fa-user-plus"></i>
                    <span id="req-badge" class="absolute top-1 right-1 bg-red-500 text-white text-[9px] w-4 h-4 rounded-full flex items-center justify-center hidden">0</span>
                </button>
                <button onclick="logout()" class="text-slate-400 hover:text-red-400 text-sm p-2" title="Çıkış Yap"><i class="fa-solid fa-power-off"></i></button>
            </div>
        </div>

        <!-- @ İLE KİŞİ ARAMA ÇUBUĞU -->
        <div class="p-3">
            <div class="relative">
                <i class="fa-solid fa-search absolute left-3 top-3 text-slate-400 text-sm"></i>
                <input type="text" id="search-box" oninput="searchUsers()" placeholder="@kullaniciadi ara..." class="w-full bg-[#0f172a] text-sm rounded-xl pl-9 pr-4 py-2.5 focus:outline-none focus:ring-1 focus:ring-indigo-500 text-slate-200 placeholder-slate-500">
            </div>
        </div>

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
            <!-- SESLİ ARAMA BUTONU -->
            <button onclick="startVoiceCall()" class="bg-emerald-600 hover:bg-emerald-500 text-white px-3.5 py-2 rounded-xl text-xs font-medium flex items-center space-x-2 transition shadow" title="Telefon Numarasız Sesli Ara">
                <i class="fa-solid fa-phone"></i>
                <span>Sesli Ara</span>
            </button>
        </div>

        <div id="chat-messages" class="flex-1 overflow-y-auto p-6 space-y-4 flex flex-col">
            <div class="m-auto text-center text-slate-500">
                <i class="fa-regular fa-comments text-5xl mb-2"></i>
                <p>Sohbet etmek için soldan birini seçin veya @ ile arayıp ekleyin.</p>
            </div>
        </div>

        <!-- STİCKER PANELİ -->
        <div id="sticker-panel" class="bg-[#162032] p-3 border-t border-slate-700 hidden">
            <div class="flex justify-between items-center mb-2">
                <span class="text-xs font-bold text-slate-300">Sticker Koleksiyonu</span>
                <button onclick="openCreateStickerModal()" class="text-xs bg-indigo-600 hover:bg-indigo-500 text-white px-2.5 py-1 rounded-lg">+ Sticker Oluştur</button>
            </div>
            <div id="sticker-container" class="flex space-x-2 overflow-x-auto py-1"></div>
        </div>

        <!-- MESAJ GİRİŞ ÇUBUĞU -->
        <div id="chat-input-bar" class="p-4 bg-[#1e293b] border-t border-slate-700 flex items-center space-x-3 hidden">
            <button onclick="toggleStickerPanel()" class="text-slate-400 hover:text-indigo-400 text-xl px-1" title="Stickerlar"><i class="fa-solid fa-note-sticky"></i></button>
            <button onclick="toggleVoiceRecord()" id="mic-btn" class="text-slate-400 hover:text-indigo-400 text-xl px-1" title="Sesli Mesaj"><i class="fa-solid fa-microphone"></i></button>
            <label class="text-slate-400 hover:text-indigo-400 text-xl cursor-pointer px-1" title="Fotoğraf Gönder">
                <i class="fa-solid fa-image"></i>
                <input type="file" id="media-file-input" accept="image/*" onchange="sendMediaFile()" class="hidden">
            </label>
            <input type="text" id="message-input" onkeypress="checkEnter(event)" placeholder="Anonim mesaj yazın..." class="flex-1 bg-[#0f172a] text-sm rounded-xl px-4 py-3 focus:outline-none focus:ring-1 focus:ring-indigo-500 text-slate-200 placeholder-slate-500">
            <button onclick="sendMessage('text')" class="bg-indigo-600 hover:bg-indigo-500 text-white px-5 py-3 rounded-xl font-medium transition flex items-center space-x-2">
                <span>Gönder</span>
                <i class="fa-solid fa-paper-plane text-xs"></i>
            </button>
        </div>
    </div>

    <!-- SESLİ ARAMA MODALI -->
    <div id="call-modal" class="fixed inset-0 bg-black/80 hidden flex items-center justify-center z-50">
        <div class="bg-[#1e293b] p-8 rounded-3xl w-80 text-center space-y-6 border border-slate-700 shadow-2xl">
            <div class="relative w-24 h-24 mx-auto">
                <img id="call-avatar" src="" class="w-24 h-24 rounded-full object-cover border-4 border-emerald-500 animate-pulse">
            </div>
            <div>
                <h3 id="call-username" class="text-lg font-bold">Kişi</h3>
                <span class="text-xs text-emerald-400 animate-pulse" id="call-status">Sesli Arama Gerçekleşiyor...</span>
            </div>
            <div class="flex justify-center space-x-4 pt-2">
                <button onclick="endVoiceCall()" class="bg-red-600 hover:bg-red-500 text-white w-14 h-14 rounded-full text-lg shadow-lg flex items-center justify-center transition"><i class="fa-solid fa-phone-slash"></i></button>
            </div>
        </div>
    </div>

    <!-- STİCKER OLUŞTURMA MODALI -->
    <div id="sticker-modal" class="fixed inset-0 bg-black/70 hidden flex items-center justify-center z-50">
        <div class="bg-[#1e293b] p-6 rounded-2xl w-96 border border-slate-700 space-y-4 shadow-2xl">
            <h3 class="text-lg font-bold">Yeni Sticker Oluştur</h3>
            <div>
                <label class="text-xs text-slate-400">Görsel URL (İnternet adresi)</label>
                <input type="text" id="new-sticker-url" placeholder="https://ornek.com/resim.png" class="w-full bg-[#0f172a] text-sm p-2.5 rounded-lg border border-slate-700 text-slate-200 mt-1">
            </div>
            <div class="flex justify-end space-x-2 pt-2">
                <button onclick="closeCreateStickerModal()" class="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-sm">İptal</button>
                <button onclick="saveNewSticker()" class="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-sm font-medium">Sticker Üret</button>
            </div>
        </div>
    </div>

    <!-- İSTEKLER MODALI -->
    <div id="requests-modal" class="fixed inset-0 bg-black/70 hidden flex items-center justify-center z-50">
        <div class="bg-[#1e293b] p-6 rounded-2xl w-96 border border-slate-700 space-y-4 shadow-2xl">
            <div class="flex justify-between items-center">
                <h3 class="text-lg font-bold">Anonim İstekler</h3>
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
            <h3 class="text-lg font-bold">Anonim Profilini Düzenle</h3>
            <div class="text-center">
                <img id="modal-avatar-preview" src="" class="w-20 h-20 rounded-full mx-auto object-cover border-2 border-indigo-500 mb-2">
                <input type="text" id="edit-avatar-url" placeholder="Avatar Resim URL'si" class="w-full bg-[#0f172a] text-xs p-2 rounded-lg border border-slate-700 text-slate-300">
            </div>
            <div>
                <label class="text-xs text-slate-400">Anonim Biyografi</label>
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
            <div class="text-indigo-500 text-4xl mb-2"><i class="fa-solid fa-mask"></i></div>
            <h2 class="text-xl font-bold">VasyoChat Anonim Giriş</h2>
            <input type="text" id="auth-username" placeholder="Rumuz / Kullanıcı Adı" class="w-full bg-[#0f172a] text-sm p-3 rounded-xl border border-slate-700 text-slate-200">
            <input type="password" id="auth-pin" placeholder="Gizli PIN" class="w-full bg-[#0f172a] text-sm p-3 rounded-xl border border-slate-700 text-slate-200">
            <button onclick="loginUser()" class="w-full bg-indigo-600 hover:bg-indigo-500 py-3 rounded-xl font-bold transition">Bağlan</button>
        </div>
    </div>

    <script>
        let currentUser = localStorage.getItem("vasyo_user") || null;
        let currentTarget = null;
        let mediaRecorder;
        let audioChunks = [];
        let localStream;

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
            if(!u || !p) return alert("Rumuz ve PIN gir!");
            
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
            await loadStickers();
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
            let query = document.getElementById("search-box").value.trim();
            
            if(!query.startsWith("@")) {
                list.innerHTML = "";
                friends.forEach(u => {
                    if(u.username.toLowerCase() === currentUser.toLowerCase()) {
                        document.getElementById("my-avatar").src = u.avatar || "https://i.imgur.com/6VBx3io.png";
                        return;
                    }
                    let div = document.createElement("div");
                    div.className = `flex items-center space-x-3 p-3 cursor-pointer hover:bg-slate-800/60 transition ${currentTarget === u.username ? 'bg-slate-800' : ''}`;
                    div.onclick = () => selectChat(u.username, u.avatar, u.bio);
                    div.innerHTML = `
                        <img src="${u.avatar || 'https://i.imgur.com/6VBx3io.png'}" class="w-11 h-11 rounded-full object-cover">
                        <div class="flex-1 min-w-0">
                            <h4 class="font-bold text-sm truncate">${u.username}</h4>
                            <p class="text-xs text-slate-400 truncate">${u.bio || 'Anonim Kullanıcı'}</p>
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

            let searchterm = query.substring(1).trim();
            let res = await fetch(`/api/search-user?query=${encodeURIComponent(searchterm)}¤t=${encodeURIComponent(currentUser)}`);
            let user = await res.json();

            list.innerHTML = "";
            if(user.error) {
                list.innerHTML = `<div class="p-4 text-xs text-slate-500 text-center">Anonim kullanıcı bulunamadı.</div>`;
            } else {
                let div = document.createElement("div");
                div.className = "flex items-center justify-between p-3 bg-slate-800/40";
                div.innerHTML = `
                    <div class="flex items-center space-x-3">
                        <img src="${user.avatar || 'https://i.imgur.com/6VBx3io.png'}" class="w-10 h-10 rounded-full object-cover">
                        <div>
                            <h4 class="font-bold text-sm">${user.username}</h4>
                            <p class="text-xs text-slate-400">${user.bio || 'Anonim Kullanıcı'}</p>
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
                            <img src="${r.avatar || 'https://i.imgur.com/6VBx3io.png'}" class="w-9 h-9 rounded-full object-cover">
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
            document.getElementById("active-chat-avatar").src = avatar || 'https://i.imgur.com/6VBx3io.png';
            document.getElementById("active-chat-bio").innerText = bio || 'Anonim Kullanıcı';
            loadMessages();
        }

        async function sendMessage(type, contentOverride = null) {
            let input = document.getElementById("message-input");
            let text = contentOverride || input.value.trim();
            if(!text || !currentTarget) return;

            await fetch("/api/send", {
                method: "POST",
                headers: {"Content-Type": "application/x-www-form-urlencoded"},
                body: `sender=${encodeURIComponent(currentUser)}&receiver=${encodeURIComponent(currentTarget)}&content=${encodeURIComponent(text)}&msg_type=${type}`
            });
            if(!contentOverride) input.value = "";
            loadMessages();
        }

        async function sendMediaFile() {
            let fileInput = document.getElementById("media-file-input");
            if(fileInput.files.length === 0 || !currentTarget) return;
            let file = fileInput.files[0];
            let reader = new FileReader();
            reader.readAsDataURL(file);
            reader.onloadend = async () => {
                await sendMessage('image', reader.result);
            };
        }

        async function toggleVoiceRecord() {
            let btn = document.getElementById("mic-btn");
            if (!mediaRecorder || mediaRecorder.state === "inactive") {
                let stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                mediaRecorder = new MediaRecorder(stream);
                audioChunks = [];
                mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
                mediaRecorder.onstop = async () => {
                    let blob = new Blob(audioChunks, { type: 'audio/webm' });
                    let reader = new FileReader();
                    reader.readAsDataURL(blob);
                    reader.onloadend = async () => {
                        await sendMessage('voice', reader.result);
                    };
                };
                mediaRecorder.start();
                btn.classList.add("text-red-500", "animate-pulse");
            } else {
                mediaRecorder.stop();
                btn.classList.remove("text-red-500", "animate-pulse");
            }
        }

        async function startVoiceCall() {
            if(!currentTarget) return;
            document.getElementById("call-username").innerText = currentTarget;
            document.getElementById("call-avatar").src = document.getElementById("active-chat-avatar").src;
            document.getElementById("call-modal").classList.remove("hidden");
            try {
                localStream = await navigator.mediaDevices.getUserMedia({ audio: true });
            } catch(e) {
                alert("Mikrofon izni alınamadı!");
                endVoiceCall();
            }
        }

        function endVoiceCall() {
            if(localStream) {
                localStream.getTracks().forEach(track => track.stop());
            }
            document.getElementById("call-modal").classList.add("hidden");
        }

        function toggleStickerPanel() {
            let panel = document.getElementById("sticker-panel");
            panel.classList.toggle("hidden");
        }

        async function loadStickers() {
            let res = await fetch("/api/stickers");
            let stickers = await res.json();
            let container = document.getElementById("sticker-container");
            container.innerHTML = "";
            stickers.forEach(s => {
                let img = document.createElement("img");
                img.src = s.url;
                img.className = "w-14 h-14 object-cover rounded-xl cursor-pointer hover:scale-110 transition bg-slate-800 p-1";
                img.onclick = () => sendMessage('sticker', s.url);
                container.appendChild(img);
            });
        }

        function openCreateStickerModal() {
            document.getElementById("sticker-modal").classList.remove("hidden");
        }
        function closeCreateStickerModal() {
            document.getElementById("sticker-modal").classList.add("hidden");
        }

        async function saveNewSticker() {
            let url = document.getElementById("new-sticker-url").value.trim();
            if(!url) return;
            await fetch("/api/add-sticker", {
                method: "POST",
                headers: {"Content-Type": "application/x-www-form-urlencoded"},
                body: `creator=${encodeURIComponent(currentUser)}&url=${encodeURIComponent(url)}`
            });
            document.getElementById("new-sticker-url").value = "";
            closeCreateStickerModal();
            loadStickers();
            alert("Sticker başarıyla oluşturuldu!");
        }

        async function deleteMessage(msgId) {
            if(!confirm("Mesajı silmek istiyor musun?")) return;
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
                let isMe = m.sender.toLowerCase() === currentUser.toLowerCase();
                let div = document.createElement("div");
                div.className = `flex flex-col ${isMe ? 'items-end' : 'items-start'} my-1 group`;
                
                let contentHtml = "";
                if(m.msg_type === 'text') {
                    contentHtml = `<p class="text-sm">${m.content}</p>`;
                } else if(m.msg_type === 'image') {
                    contentHtml = `<img src="${m.content}" class="max-w-xs rounded-xl cursor-pointer" onclick="window.open(this.src)">`;
                } else if(m.msg_type === 'voice') {
                    contentHtml = `<audio controls src="${m.content}" class="h-10 w-48"></audio>`;
                } else if(m.msg_type === 'sticker') {
                    contentHtml = `<img src="${m.content}" class="w-28 h-28 object-contain">`;
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

        function checkEnter(e) { if(e.key === 'Enter') sendMessage('text'); }

        async function openProfileModal() {
            let res = await fetch(`/api/search-user?query=${encodeURIComponent(currentUser)}¤t=`);
            let me = await res.json();
            if(me) {
                document.getElementById("edit-avatar-url").value = me.avatar || "";
                document.getElementById("edit-bio").value = me.bio || "";
                document.getElementById("modal-avatar-preview").src = me.avatar || "https://i.imgur.com/6VBx3io.png";
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
    cursor.execute("SELECT * FROM users WHERE LOWER(username) = LOWER(?)", (username,))
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
    cursor.execute("SELECT username, bio, avatar FROM users WHERE LOWER(username) = LOWER(?)", (query,))
    r = cursor.fetchone()
    conn.close()
    if not r or r[0].lower() == current.lower():
        return {"error": "not found"}
    return {
        "username": r[0], 
        "bio": r[1] or "Anonim VasyoChat Kullanıcısı", 
        "avatar": r[2] or "https://i.imgur.com/6VBx3io.png"
    }

@app.post("/api/send-request")
def send_request(sender: str = Form(...), receiver: str = Form(...)):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM requests 
        WHERE (LOWER(sender) = LOWER(?) AND LOWER(receiver) = LOWER(?)) 
           OR (LOWER(sender) = LOWER(?) AND LOWER(receiver) = LOWER(?))
    """, (sender, receiver, receiver, sender))
    existing = cursor.fetchone()
    if existing:
        conn.close()
        return {"message": "Zaten istek atılmış veya arkadaşsınız!"}
    cursor.execute("INSERT INTO requests (sender, receiver, status) VALUES (?, ?, 'pending')", (sender, receiver))
    conn.commit()
    conn.close()
    return {"message": "Anonim arkadaşlık isteği gönderildi!"}

@app.get("/api/get-requests")
def get_requests(username: str):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, sender FROM requests WHERE LOWER(receiver) = LOWER(?) AND status = 'pending'", (username,))
    rows = cursor.fetchall()
    result = []
    for r in rows:
        cursor.execute("SELECT avatar FROM users WHERE LOWER(username) = LOWER(?)", (r[1],))
        u = cursor.fetchone()
        avatar = (u and u[0]) or "https://i.imgur.com/6VBx3io.png"
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
        WHERE (LOWER(sender) = LOWER(?) OR LOWER(receiver) = LOWER(?)) AND status = 'accepted'
    """, (username, username))
    rows = cursor.fetchall()
    friend_names = set()
    for r in rows:
        if r[0].lower() == username.lower():
            friend_names.add(r[1])
        else:
            friend_names.add(r[0])
    
    friends = []
    for f in friend_names:
        cursor.execute("SELECT username, bio, avatar FROM users WHERE LOWER(username) = LOWER(?)", (f,))
        u = cursor.fetchone()
        if u:
            friends.append({
                "username": u[0], 
                "bio": u[1] or "Anonim VasyoChat Kullanıcısı", 
                "avatar": u[2] or "https://i.imgur.com/6VBx3io.png"
            })
    conn.close()
    return friends

@app.post("/api/update-profile")
def update_profile(username: str = Form(...), avatar: str = Form(...), bio: str = Form(...)):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET avatar = ?, bio = ? WHERE LOWER(username) = LOWER(?)", (avatar, bio, username))
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
        WHERE (LOWER(sender) = LOWER(?) AND LOWER(receiver) = LOWER(?)) 
           OR (LOWER(sender) = LOWER(?) AND LOWER(receiver) = LOWER(?))
        ORDER BY id ASC
    """, (user1, user2, user2, user1))
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "sender": r[1], "receiver": r[2], "content": r[3], "msg_type": r[4], "timestamp": r[5]} for r in rows]

@app.get("/api/stickers")
def get_stickers():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, creator, url FROM stickers")
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "creator": r[1], "url": r[2]} for r in rows]

@app.post("/api/add-sticker")
def add_sticker(creator: str = Form(...), url: str = Form(...)):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO stickers (creator, url) VALUES (?, ?)", (creator, url))
    conn.commit()
    conn.close()
    return {"status": "ok"}