const communityState = { categories: [], category: "", feed: "latest", currentPostId: null };

async function communityFetch(url, options = {}) {
  const response = await fetch(url, options);
  const data = await response.json().catch(() => ({}));
  if (response.status === 401) { showAuth(); throw new Error("请先登录"); }
  if (!response.ok) throw new Error(data.error || "请求失败");
  return data;
}

function formatCommunityTime(value) {
  if (!value) return "";
  const parsed = new Date(value.endsWith("Z") ? value : `${value}Z`);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
}

async function initCommunity() {
  if (!window._user) return;
  if (!communityState.categories.length) {
    const data = await communityFetch("/api/community/categories");
    communityState.categories = data.categories || [];
    const chips = document.getElementById("community-categories");
    chips.innerHTML = `<button type="button" class="active" data-category="">全部领域</button>${communityState.categories.map(item => `<button type="button" data-category="${escapeHtml(item.slug)}">${escapeHtml(item.name)}</button>`).join("")}`;
    chips.querySelectorAll("button").forEach(button => button.addEventListener("click", () => {
      communityState.category = button.dataset.category || "";
      chips.querySelectorAll("button").forEach(item => item.classList.toggle("active", item === button));
      loadCommunityPosts();
    }));
    const select = document.getElementById("community-compose-category");
    select.innerHTML = communityState.categories.map(item => `<option value="${escapeHtml(item.slug)}">${escapeHtml(item.name)}</option>`).join("");
    document.querySelectorAll("#community-feeds button").forEach(button => button.addEventListener("click", () => {
      communityState.feed = button.dataset.feed;
      document.querySelectorAll("#community-feeds button").forEach(item => item.classList.toggle("active", item === button));
      loadCommunityPosts();
    }));
  }
  await loadCommunityPosts();
}

async function loadCommunityPosts() {
  const list = document.getElementById("community-list");
  if (!list || !window._user) return;
  list.innerHTML = '<div class="module-loading">正在加载社区内容…</div>';
  const params = new URLSearchParams({ feed: communityState.feed, per_page: "20" });
  const query = document.getElementById("community-query")?.value.trim();
  const type = document.getElementById("community-type")?.value;
  if (communityState.category) params.set("category", communityState.category);
  if (query) params.set("q", query);
  if (type) params.set("type", type);
  try {
    const data = await communityFetch(`/api/community/posts?${params}`);
    const posts = data.posts || [];
    list.innerHTML = posts.length ? posts.map(renderCommunityCard).join("") : '<div class="module-empty">还没有匹配的讨论。你可以发起第一个问题。</div>';
  } catch (error) { list.innerHTML = `<div class="module-empty">${escapeHtml(error.message)}</div>`; }
}

function renderCommunityCard(post) {
  const help = post.post_type === "legal_help" ? `<span class="help-tag">法律求助 · ${post.help_status === "resolved" ? "已解决" : post.help_status === "answered" ? "已有回应" : "待回应"}</span>` : "";
  return `<article class="community-card" onclick="openCommunityPost(${post.id})">
    <div class="community-card-top"><span class="category-tag">${escapeHtml(post.category.name)}</span>${help}</div>
    <h3>${escapeHtml(post.title)}</h3><p>${escapeHtml(post.body)}</p>
    <div class="community-card-meta"><span>${escapeHtml(post.author.name)} · ${formatCommunityTime(post.created_at)}</span><span>${post.counts.views} 阅读</span></div>
    <div class="community-card-actions"><span>赞同 ${post.counts.likes}</span><span>讨论 ${post.counts.comments}</span><span>收藏 ${post.counts.favorites}</span></div>
  </article>`;
}

function openCommunityComposer(prefill = null) {
  const modal = document.getElementById("community-compose-modal");
  document.getElementById("community-compose-title-input").value = prefill?.title || "";
  document.getElementById("community-compose-body").value = prefill?.body || "";
  document.getElementById("community-compose-type").value = prefill?.post_type || "legal_help";
  document.getElementById("community-compose-anonymous").checked = prefill ? prefill.is_anonymous !== false : true;
  document.getElementById("community-draft-token").value = prefill?.draft_token || "";
  const category = document.getElementById("community-compose-category");
  if (prefill?.category && [...category.options].some(option => option.value === prefill.category)) category.value = prefill.category;
  document.getElementById("community-ai-origin").classList.toggle("hidden", !prefill?.draft_token);
  modal.classList.remove("hidden");
}

function closeCommunityComposer() { document.getElementById("community-compose-modal")?.classList.add("hidden"); }

async function submitCommunityPost(event) {
  event.preventDefault();
  const payload = {
    category: document.getElementById("community-compose-category").value,
    post_type: document.getElementById("community-compose-type").value,
    title: document.getElementById("community-compose-title-input").value,
    body: document.getElementById("community-compose-body").value,
    is_anonymous: document.getElementById("community-compose-anonymous").checked,
    draft_token: document.getElementById("community-draft-token").value,
  };
  try {
    const data = await communityFetch("/api/community/posts", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    closeCommunityComposer(); await loadCommunityPosts(); await openCommunityPost(data.post.id);
    if (data.privacy_meta?.masked_count) alert(`发布前已自动隐藏 ${data.privacy_meta.masked_count} 处个人信息。`);
  } catch (error) { alert(error.message); }
}

async function openAiCommunityDraft() {
  if (!legalAgentState?.conversationId) { alert("请先完成并保存一次 AI 咨询"); return; }
  try {
    const data = await communityFetch("/api/community/ai-draft", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ conversation_id: legalAgentState.conversationId }) });
    if (!communityState.categories.length) await initCommunity();
    openCommunityComposer(data.draft);
  } catch (error) { alert(error.message); }
}

async function openCommunityPost(postId) {
  communityState.currentPostId = Number(postId);
  const modal = document.getElementById("community-detail-modal");
  const target = document.getElementById("community-detail-content");
  modal.classList.remove("hidden"); target.innerHTML = '<div class="module-loading">正在打开讨论…</div>';
  try {
    const data = await communityFetch(`/api/community/posts/${postId}`);
    const post = data.post;
    const canChat = post.author?.id && post.author.id !== window._user?.id ? `<button class="author-chat" onclick="event.stopPropagation();startDirectChat(${post.author.id},'${escapeHtml(post.author.name)}')">私聊作者</button>` : "";
    const status = post.viewer.can_edit && post.post_type === "legal_help" ? `<select class="post-status-select" onchange="updateHelpStatus(${post.id},this.value)"><option value="open" ${post.help_status === "open" ? "selected" : ""}>待回应</option><option value="answered" ${post.help_status === "answered" ? "selected" : ""}>已有回应</option><option value="resolved" ${post.help_status === "resolved" ? "selected" : ""}>已解决</option></select>` : "";
    target.innerHTML = `<div class="community-card-top"><span class="category-tag">${escapeHtml(post.category.name)}</span><span class="privacy-note">${post.is_anonymous ? "匿名求助 · 身份受保护" : escapeHtml(post.author.name)}</span></div>
      <h2 class="community-detail-title">${escapeHtml(post.title)}</h2><div class="community-detail-body">${escapeHtml(post.body)}</div>
      <div class="detail-actions"><button onclick="togglePostReaction(${post.id},'like')">${post.viewer.liked ? "已赞同" : "赞同"} ${post.counts.likes}</button><button onclick="togglePostReaction(${post.id},'favorite')">${post.viewer.favorited ? "已收藏" : "收藏"} ${post.counts.favorites}</button>${canChat}${status}<button onclick="reportCommunity('post',${post.id})">举报</button></div>
      ${renderRelatedCases(post.related_cases || [])}
      <h3 class="comments-heading">讨论与回复 <small>${post.counts.comments}</small></h3>
      <form class="comment-composer" onsubmit="submitCommunityComment(event,${post.id})"><textarea id="community-comment-body" maxlength="4000" required placeholder="提供建设性建议，避免公开个人身份信息"></textarea><button class="btn-primary" type="submit">回复</button></form>
      <div id="community-comments">${renderComments(data.comments || [])}</div>`;
  } catch (error) { target.innerHTML = `<div class="module-empty">${escapeHtml(error.message)}</div>`; }
}

function renderRelatedCases(cases) {
  if (!cases.length) return "";
  return `<h3 class="comments-heading">相关真实案例</h3><div class="related-case-list">${cases.map(item => `<button class="related-case-item" onclick="closeCommunityDetail();switchModule('cases');openCaseDetail(${item.id})"><b>${escapeHtml(item.title)}</b><small>${escapeHtml(item.court_name || item.guiding_case_number || "权威公开案例")}</small></button>`).join("")}</div>`;
}

function renderComments(comments) {
  if (!comments.length) return '<div class="module-empty">还没有回复，来说说你的建议。</div>';
  const roots = comments.filter(item => !item.parent_id);
  return roots.map(root => renderComment(root, false) + comments.filter(item => item.parent_id === root.id).map(item => renderComment(item, true)).join("")).join("");
}

function renderComment(item, reply) {
  const chat = item.author?.id && item.author.id !== window._user?.id ? `<button class="comment-action author-chat" onclick="startDirectChat(${item.author.id},'${escapeHtml(item.author.name)}')">私聊</button>` : "";
  return `<article class="comment-item ${reply ? "reply" : ""}"><div class="comment-meta"><b>${escapeHtml(item.author.name)}${item.author.is_owner ? " · 楼主" : ""}</b><time>${formatCommunityTime(item.created_at)}</time></div><p>${escapeHtml(item.body)}</p><div class="comment-actions"><button class="comment-action" onclick="prepareCommentReply(${item.id},'${escapeHtml(item.author.name)}')">回复</button><button class="comment-action" onclick="toggleCommentLike(${item.id})">${item.liked ? "已赞" : "赞"} ${item.like_count}</button>${chat}<button class="comment-action" onclick="reportCommunity('comment',${item.id})">举报</button></div></article>`;
}

let communityReplyTo = null;
function prepareCommentReply(id, name) { communityReplyTo = id; const input = document.getElementById("community-comment-body"); input.placeholder = `回复 ${name}`; input.focus(); }
async function submitCommunityComment(event, postId) { event.preventDefault(); const input = document.getElementById("community-comment-body"); try { await communityFetch(`/api/community/posts/${postId}/comments`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ body: input.value, parent_id: communityReplyTo }) }); communityReplyTo = null; await openCommunityPost(postId); } catch(error) { alert(error.message); } }
async function togglePostReaction(id, type) { try { await communityFetch(`/api/community/posts/${id}/${type}`, { method: "POST" }); await openCommunityPost(id); loadCommunityPosts(); } catch(error) { alert(error.message); } }
async function toggleCommentLike(id) { try { await communityFetch(`/api/community/comments/${id}/like`, { method: "POST" }); await openCommunityPost(communityState.currentPostId); } catch(error) { alert(error.message); } }
async function updateHelpStatus(id, value) { try { await communityFetch(`/api/community/posts/${id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ help_status: value }) }); await openCommunityPost(id); } catch(error) { alert(error.message); } }
async function reportCommunity(type, id) { const reason = prompt("请简要说明举报原因（如：泄露隐私、骚扰、违法内容）"); if (!reason) return; try { await communityFetch("/api/community/reports", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ target_type: type, target_id: id, reason }) }); alert("举报已提交，管理员会尽快处理。"); } catch(error) { alert(error.message); } }
function closeCommunityDetail() { document.getElementById("community-detail-modal")?.classList.add("hidden"); }
