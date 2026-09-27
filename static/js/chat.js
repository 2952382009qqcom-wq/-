const chatState = { socket: null, threads: [], activeThreadId: null, messages: [], searchTimer: null, pollingTimer: null, typingTimer: null };

async function chatFetch(url, options = {}) {
  const response = await fetch(url, options); const data = await response.json().catch(() => ({}));
  if (response.status === 401) { showAuth(); throw new Error("请先登录"); }
  if (!response.ok) throw new Error(data.error || "请求失败"); return data;
}

function initMingjianChat() {
  if (!window._user) return;
  if (window.io && !chatState.socket) {
    chatState.socket = window.io("/chat", { transports: ["websocket", "polling"] });
    chatState.socket.on("chat_message", message => { if (message.thread_id === chatState.activeThreadId) { if (!chatState.messages.some(item => item.id === message.id)) { chatState.messages.push(message); renderChatMessages(); markChatRead(); } } loadChatThreads(); });
    chatState.socket.on("chat_typing", event => { if (event.thread_id === chatState.activeThreadId) showTyping(event.typing); });
    chatState.socket.on("chat_error", event => alert(event.error || "消息发送失败"));
  }
  loadChatThreads();
}

function disconnectMingjianChat() { if (chatState.socket) chatState.socket.disconnect(); chatState.socket = null; clearInterval(chatState.pollingTimer); chatState.pollingTimer = null; }
async function openChatDrawer() { document.getElementById("chat-overlay").classList.remove("hidden"); document.getElementById("chat-drawer").classList.remove("hidden"); initMingjianChat(); }
function closeChatDrawer() { document.getElementById("chat-overlay").classList.add("hidden"); document.getElementById("chat-drawer").classList.add("hidden"); }

async function loadChatThreads() {
  if (!window._user) return;
  try { const data = await chatFetch("/api/chat/threads"); chatState.threads = data.threads || []; renderChatThreads(); const unread = chatState.threads.reduce((sum, item) => sum + Number(item.unread_count || 0), 0); const badge = document.getElementById("chat-unread-badge"); badge.textContent = unread > 99 ? "99+" : unread; badge.classList.toggle("hidden", !unread); } catch (_) {}
}

function renderChatThreads() {
  const target = document.getElementById("chat-thread-list"); if (!target) return;
  target.innerHTML = chatState.threads.length ? chatState.threads.map(item => `<button class="chat-thread ${item.id === chatState.activeThreadId ? "active" : ""}" onclick="openChatThread('${escapeHtml(item.id)}')"><b><span>${escapeHtml(item.other_user?.username || "已注销用户")}</span>${item.unread_count ? `<em>${item.unread_count}</em>` : ""}</b><p>${escapeHtml(item.last_message?.body || "尚无消息")}</p></button>`).join("") : '<div class="chat-empty">搜索用户名开始私聊</div>';
}

function searchChatUsers(value) {
  clearTimeout(chatState.searchTimer); const target = document.getElementById("chat-user-results");
  if (!value.trim()) { target.classList.add("hidden"); return; }
  chatState.searchTimer = setTimeout(async () => { try { const data = await chatFetch(`/api/chat/users?q=${encodeURIComponent(value.trim())}`); target.innerHTML = (data.users || []).map(user => `<button class="chat-user-result" onclick="startDirectChat(${user.id},'${escapeHtml(user.username)}')"><span>${escapeHtml(user.username)}</span><small>开始私聊</small></button>`).join("") || '<div class="chat-empty">未找到用户</div>'; target.classList.remove("hidden"); } catch (_) {} }, 250);
}

async function startDirectChat(userId) {
  try { const data = await chatFetch("/api/chat/threads", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ user_id: userId }) }); document.getElementById("chat-user-results").classList.add("hidden"); document.getElementById("chat-user-query").value = ""; await loadChatThreads(); await openChatDrawer(); await openChatThread(data.thread.id); } catch (error) { alert(error.message); }
}

async function openChatThread(threadId) {
  if (chatState.activeThreadId && chatState.socket) chatState.socket.emit("leave_thread", { thread_id: chatState.activeThreadId });
  chatState.activeThreadId = String(threadId); const thread = chatState.threads.find(item => item.id === chatState.activeThreadId);
  document.getElementById("chat-conversation-head").textContent = thread?.other_user?.username || "私聊";
  document.getElementById("chat-message-input").disabled = false; document.getElementById("chat-send").disabled = false; renderChatThreads();
  if (chatState.socket) chatState.socket.emit("join_thread", { thread_id: chatState.activeThreadId });
  await loadChatMessages(); clearInterval(chatState.pollingTimer); if (!chatState.socket?.connected) chatState.pollingTimer = setInterval(loadChatMessages, 5000);
}

async function loadChatMessages() { if (!chatState.activeThreadId) return; try { const data = await chatFetch(`/api/chat/threads/${encodeURIComponent(chatState.activeThreadId)}/messages`); chatState.messages = data.messages || []; renderChatMessages(); await markChatRead(); } catch(error) { document.getElementById("chat-messages").innerHTML = `<div class="chat-empty">${escapeHtml(error.message)}</div>`; } }
function renderChatMessages() { const target = document.getElementById("chat-messages"); target.innerHTML = chatState.messages.length ? chatState.messages.map(item => `<div class="chat-message ${item.sender_id === window._user?.id ? "mine" : ""}"><div class="chat-bubble">${escapeHtml(item.body)}<time>${formatCommunityTime(item.created_at)}</time></div></div>`).join("") : '<div class="chat-empty">还没有消息，友善地打个招呼吧。</div>'; requestAnimationFrame(() => { target.scrollTop = target.scrollHeight; }); }

async function sendChatMessage(event) {
  event.preventDefault(); const input = document.getElementById("chat-message-input"); const body = input.value.trim(); if (!body || !chatState.activeThreadId) return; input.value = "";
  if (chatState.socket?.connected) chatState.socket.emit("send_message", { thread_id: chatState.activeThreadId, body });
  else { try { const data = await chatFetch(`/api/chat/threads/${encodeURIComponent(chatState.activeThreadId)}/messages`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ body }) }); chatState.messages.push(data.message); renderChatMessages(); loadChatThreads(); } catch(error) { alert(error.message); input.value = body; } }
}

async function markChatRead() { if (!chatState.activeThreadId || !chatState.messages.length) return; const id = chatState.messages[chatState.messages.length - 1].id; try { if (chatState.socket?.connected) chatState.socket.emit("mark_read", { thread_id: chatState.activeThreadId, message_id: id }); else await chatFetch(`/api/chat/threads/${encodeURIComponent(chatState.activeThreadId)}/read`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ message_id: id }) }); } catch (_) {} }
function emitChatTyping() { if (!chatState.socket?.connected || !chatState.activeThreadId) return; chatState.socket.emit("typing", { thread_id: chatState.activeThreadId, typing: true }); clearTimeout(chatState.typingTimer); chatState.typingTimer = setTimeout(() => chatState.socket?.emit("typing", { thread_id: chatState.activeThreadId, typing: false }), 900); }
function showTyping(active) { let node = document.querySelector(".chat-typing"); if (!node) { node = document.createElement("div"); node.className = "chat-typing"; document.querySelector(".chat-conversation").insertBefore(node, document.querySelector(".chat-composer")); } node.textContent = active ? "对方正在输入…" : ""; }
