const chatState = {
  socket: null, threads: [], activeThreadId: null, messages: [], searchTimer: null,
  pollingTimer: null, typingTimer: null, replyTo: null, hasMore: false, onlineUsers: new Set(),
};

async function chatFetch(url, options = {}) {
  const response = await fetch(url, options);
  const data = await response.json().catch(() => ({}));
  if (response.status === 401) { showAuth(); throw new Error("请先登录"); }
  if (!response.ok) throw new Error(data.error || "请求失败");
  return data;
}

function chatClientId() {
  return window.crypto?.randomUUID?.() || `web-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function mergeChatMessages(incoming) {
  const byId = new Map(chatState.messages.map(item => [item.id, item]));
  (incoming || []).forEach(item => byId.set(item.id, item));
  chatState.messages = [...byId.values()].sort((left, right) => Number(left.sequence) - Number(right.sequence));
}

function initMingjianChat() {
  if (!window._user) return;
  if (window.io && !chatState.socket) {
    chatState.socket = window.io("/chat", { transports: ["websocket", "polling"], reconnection: true });
    chatState.socket.on("connect", () => syncActiveChat());
    chatState.socket.on("chat_message", message => {
      if (message.thread_id === chatState.activeThreadId) { mergeChatMessages([message]); renderChatMessages(); markChatRead(); }
      loadChatThreads();
    });
    chatState.socket.on("chat_message_updated", message => { mergeChatMessages([message]); renderChatMessages(); });
    chatState.socket.on("chat_typing", event => { if (event.thread_id === chatState.activeThreadId) showTyping(event.typing); });
    chatState.socket.on("chat_presence", event => {
      if (event.online) chatState.onlineUsers.add(Number(event.user_id)); else chatState.onlineUsers.delete(Number(event.user_id));
      renderChatHeader();
    });
    chatState.socket.on("chat_error", event => alert(event.error || "消息发送失败"));
  }
  loadChatThreads();
}

function disconnectMingjianChat() {
  if (chatState.socket) chatState.socket.disconnect();
  chatState.socket = null; clearInterval(chatState.pollingTimer); chatState.pollingTimer = null;
}
async function openChatDrawer() { document.getElementById("chat-overlay").classList.remove("hidden"); document.getElementById("chat-drawer").classList.remove("hidden"); initMingjianChat(); }
function closeChatDrawer() { document.getElementById("chat-overlay").classList.add("hidden"); document.getElementById("chat-drawer").classList.add("hidden"); }

async function loadChatThreads() {
  if (!window._user) return;
  try {
    const data = await chatFetch("/api/chat/threads"); chatState.threads = data.threads || []; renderChatThreads(); renderChatHeader();
    const unread = chatState.threads.reduce((sum, item) => sum + Number(item.unread_count || 0), 0);
    const badge = document.getElementById("chat-unread-badge"); badge.textContent = unread > 99 ? "99+" : unread; badge.classList.toggle("hidden", !unread);
  } catch (_) {}
}

function renderChatThreads() {
  const target = document.getElementById("chat-thread-list"); if (!target) return;
  target.innerHTML = chatState.threads.length ? chatState.threads.map(item => `<button class="chat-thread ${item.id === chatState.activeThreadId ? "active" : ""}" onclick="openChatThread('${escapeHtml(item.id)}')"><b><span>${escapeHtml(item.other_user?.username || "已注销用户")}</span>${item.unread_count ? `<em>${item.unread_count}</em>` : ""}</b><p>${escapeHtml(item.last_message?.body || "尚无消息")}</p></button>`).join("") : '<div class="chat-empty">搜索用户名开始私聊</div>';
}

function renderChatHeader() {
  const thread = chatState.threads.find(item => item.id === chatState.activeThreadId);
  const user = thread?.other_user;
  const online = user && chatState.onlineUsers.has(Number(user.id));
  document.getElementById("chat-conversation-head").innerHTML = user ? `${escapeHtml(user.username)}<small>${online ? "在线" : "离线"}</small>` : "选择一位用户开始私聊";
}

function searchChatUsers(value) {
  clearTimeout(chatState.searchTimer); const target = document.getElementById("chat-user-results");
  if (!value.trim()) { target.classList.add("hidden"); return; }
  chatState.searchTimer = setTimeout(async () => {
    try {
      const data = await chatFetch(`/api/chat/users?q=${encodeURIComponent(value.trim())}`);
      target.innerHTML = (data.users || []).map(user => `<button class="chat-user-result" onclick="startDirectChat(${user.id})"><span>${escapeHtml(user.username)}</span><small>开始私聊</small></button>`).join("") || '<div class="chat-empty">未找到用户</div>';
      target.classList.remove("hidden");
    } catch (_) {}
  }, 250);
}

async function startDirectChat(userId) {
  try {
    const data = await chatFetch("/api/chat/threads", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ user_id: userId }) });
    document.getElementById("chat-user-results").classList.add("hidden"); document.getElementById("chat-user-query").value = "";
    await loadChatThreads(); await openChatDrawer(); await openChatThread(data.thread.id);
  } catch (error) { alert(error.message); }
}

async function openChatThread(threadId) {
  if (chatState.activeThreadId && chatState.socket) chatState.socket.emit("leave_thread", { thread_id: chatState.activeThreadId });
  chatState.activeThreadId = String(threadId); chatState.messages = []; chatState.replyTo = null; updateReplyBanner();
  document.getElementById("chat-message-input").disabled = false; document.getElementById("chat-send").disabled = false;
  renderChatThreads(); renderChatHeader();
  if (chatState.socket) chatState.socket.emit("join_thread", { thread_id: chatState.activeThreadId });
  await loadChatMessages(); clearInterval(chatState.pollingTimer);
  if (!chatState.socket?.connected) chatState.pollingTimer = setInterval(loadChatMessages, 5000);
}

async function syncActiveChat() {
  if (!chatState.activeThreadId || !chatState.socket?.connected) return;
  const last = chatState.messages.at(-1)?.sequence || 0;
  chatState.socket.emit("join_thread", { thread_id: chatState.activeThreadId }, ack => {
    if (!ack?.ok) return;
    chatState.socket.emit("sync_messages", { thread_id: chatState.activeThreadId, after_sequence: last }, sync => {
      if (sync?.ok) { mergeChatMessages(sync.messages); renderChatMessages(); markChatRead(); }
    });
  });
}

async function loadChatMessages(older = false) {
  if (!chatState.activeThreadId) return;
  try {
    const oldest = chatState.messages[0]?.sequence;
    const cursor = older && oldest ? `?limit=60&before_sequence=${oldest}` : "?limit=60";
    const data = await chatFetch(`/api/chat/threads/${encodeURIComponent(chatState.activeThreadId)}/messages${cursor}`);
    if (!older) chatState.messages = [];
    mergeChatMessages(data.messages); chatState.hasMore = Boolean(data.has_more); renderChatMessages(!older); await markChatRead();
  } catch (error) { document.getElementById("chat-messages").innerHTML = `<div class="chat-empty">${escapeHtml(error.message)}</div>`; }
}

function renderChatMessages(scrollBottom = true) {
  const target = document.getElementById("chat-messages");
  const loadMore = chatState.hasMore ? '<button class="chat-load-more" onclick="loadChatMessages(true)">加载更早消息</button>' : "";
  target.innerHTML = loadMore + (chatState.messages.length ? chatState.messages.map(item => {
    const mine = item.sender_id === window._user?.id;
    const reply = item.reply_to_id ? `<small class="chat-reply-ref">回复一条消息</small>` : "";
    const attachment = item.attachment ? `<a class="chat-attachment" href="${escapeHtml(item.attachment.download_url)}">📎 ${escapeHtml(item.attachment.name)}</a>` : "";
    const actions = item.status === "recalled" || item.status === "moderated" ? "" : `<div class="chat-message-actions"><button onclick="replyChatMessage('${item.id}')">回复</button>${mine && item.message_type === "text" ? `<button onclick="editChatMessage('${item.id}')">编辑</button>` : ""}${mine ? `<button onclick="recallChatMessage('${item.id}')">撤回</button>` : `<button onclick="reportChatMessage('${item.id}')">举报</button>`}</div>`;
    return `<div class="chat-message ${mine ? "mine" : ""}"><div class="chat-bubble">${reply}<div>${item.body_html || escapeHtml(item.body)}</div>${attachment}<time>${formatCommunityTime(item.created_at)}${item.edited_at ? " · 已编辑" : ""}${item.status === "delivered" ? " · 已送达" : ""}</time>${actions}</div></div>`;
  }).join("") : '<div class="chat-empty">还没有消息，友善地打个招呼吧。</div>');
  if (scrollBottom) requestAnimationFrame(() => { target.scrollTop = target.scrollHeight; });
}

async function sendChatMessage(event) {
  event.preventDefault(); const input = document.getElementById("chat-message-input"); const body = input.value.trim();
  if (!body || !chatState.activeThreadId) return;
  const requestBody = { thread_id: chatState.activeThreadId, body, client_message_id: chatClientId(), reply_to_id: chatState.replyTo?.id || null };
  input.value = ""; chatState.replyTo = null; updateReplyBanner();
  if (chatState.socket?.connected) {
    chatState.socket.emit("send_message", requestBody, ack => {
      if (ack?.ok) { mergeChatMessages([ack.message]); renderChatMessages(); loadChatThreads(); }
      else { alert(ack?.error || "发送失败"); input.value = body; }
    });
  } else {
    try {
      const data = await chatFetch(`/api/chat/threads/${encodeURIComponent(chatState.activeThreadId)}/messages`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(requestBody) });
      mergeChatMessages([data.message]); renderChatMessages(); loadChatThreads();
    } catch (error) { alert(error.message); input.value = body; }
  }
}

function replyChatMessage(id) { chatState.replyTo = chatState.messages.find(item => item.id === id) || null; updateReplyBanner(); document.getElementById("chat-message-input").focus(); }
function updateReplyBanner() { const node = document.getElementById("chat-reply-banner"); node.classList.toggle("hidden", !chatState.replyTo); node.querySelector("span").textContent = chatState.replyTo ? `回复：${chatState.replyTo.body.slice(0, 60)}` : ""; }
function cancelChatReply() { chatState.replyTo = null; updateReplyBanner(); }

async function editChatMessage(id) {
  const item = chatState.messages.find(message => message.id === id); const body = prompt("修改消息", item?.body || ""); if (!body?.trim()) return;
  try { const data = await chatFetch(`/api/chat/messages/${id}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ body: body.trim() }) }); mergeChatMessages([data.message]); renderChatMessages(false); } catch (error) { alert(error.message); }
}
async function recallChatMessage(id) { if (!confirm("确定撤回这条消息吗？")) return; try { const data = await chatFetch(`/api/chat/messages/${id}/recall`, { method: "POST" }); mergeChatMessages([data.message]); renderChatMessages(false); } catch (error) { alert(error.message); } }
async function reportChatMessage(id) { const reason = prompt("请简要填写举报原因"); if (!reason?.trim()) return; try { await chatFetch(`/api/chat/messages/${id}/report`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ reason: reason.trim() }) }); alert("举报已提交"); } catch (error) { alert(error.message); } }

async function sendChatAttachment(input) {
  const file = input.files?.[0]; if (!file || !chatState.activeThreadId) return;
  const form = new FormData(); form.append("file", file); form.append("client_message_id", chatClientId()); if (chatState.replyTo) form.append("reply_to_id", chatState.replyTo.id);
  try { const data = await chatFetch(`/api/chat/threads/${encodeURIComponent(chatState.activeThreadId)}/attachments`, { method: "POST", body: form }); mergeChatMessages([data.message]); renderChatMessages(); chatState.replyTo = null; updateReplyBanner(); } catch (error) { alert(error.message); } finally { input.value = ""; }
}

async function markChatRead() {
  if (!chatState.activeThreadId || !chatState.messages.length) return;
  const id = chatState.messages.at(-1).id;
  try {
    if (chatState.socket?.connected) chatState.socket.emit("mark_read", { thread_id: chatState.activeThreadId, message_id: id });
    else await chatFetch(`/api/chat/threads/${encodeURIComponent(chatState.activeThreadId)}/read`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ message_id: id }) });
  } catch (_) {}
}
function emitChatTyping() { if (!chatState.socket?.connected || !chatState.activeThreadId) return; chatState.socket.emit("typing", { thread_id: chatState.activeThreadId, typing: true }); clearTimeout(chatState.typingTimer); chatState.typingTimer = setTimeout(() => chatState.socket?.emit("typing", { thread_id: chatState.activeThreadId, typing: false }), 900); }
function showTyping(active) { let node = document.querySelector(".chat-typing"); if (!node) { node = document.createElement("div"); node.className = "chat-typing"; document.querySelector(".chat-conversation").insertBefore(node, document.querySelector(".chat-composer")); } node.textContent = active ? "对方正在输入…" : ""; }
