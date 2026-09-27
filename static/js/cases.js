const casesState = { categories: [], category: "", feed: "latest", currentCaseId: null };

async function casesFetch(url, options = {}) {
  const response = await fetch(url, options);
  const data = await response.json().catch(() => ({}));
  if (response.status === 401) { showAuth(); throw new Error("请先登录"); }
  if (!response.ok) throw new Error(data.error || "请求失败");
  return data;
}

async function initCases() {
  if (!window._user) return;
  if (!casesState.categories.length) {
    const [data, preference] = await Promise.all([casesFetch("/api/cases/categories"), casesFetch("/api/cases/personalization")]);
    casesState.categories = data.categories || [];
    const personalization = document.getElementById("cases-personalization");
    personalization.checked = preference.enabled !== false;
    document.getElementById("case-recommendation-section").classList.toggle("hidden", !personalization.checked);
    const chips = document.getElementById("cases-categories");
    chips.innerHTML = `<button type="button" class="active" data-category="">全部领域</button>${casesState.categories.map(item => `<button type="button" data-category="${escapeHtml(item.slug)}">${escapeHtml(item.name)}</button>`).join("")}`;
    chips.querySelectorAll("button").forEach(button => button.addEventListener("click", () => {
      casesState.category = button.dataset.category || "";
      chips.querySelectorAll("button").forEach(item => item.classList.toggle("active", item === button));
      loadCases();
    }));
    document.querySelectorAll("#cases-feeds button").forEach(button => button.addEventListener("click", () => {
      casesState.feed = button.dataset.feed;
      document.querySelectorAll("#cases-feeds button").forEach(item => item.classList.toggle("active", item === button));
      loadCases();
    }));
  }
  const tasks = [loadCases()];
  if (document.getElementById("cases-personalization")?.checked) tasks.push(loadCaseRecommendations());
  await Promise.all(tasks);
}

async function loadCases() {
  const list = document.getElementById("cases-list");
  if (!list || !window._user) return;
  list.innerHTML = '<div class="module-loading">正在载入权威案例…</div>';
  const params = new URLSearchParams({ feed: casesState.feed, per_page: "20" });
  const query = document.getElementById("cases-query")?.value.trim();
  if (casesState.category) params.set("category", casesState.category);
  if (query) params.set("q", query);
  try {
    const data = await casesFetch(`/api/cases?${params}`);
    const cases = data.cases || [];
    document.getElementById("cases-total").textContent = `共 ${data.pagination?.total || 0} 个已核验案例`;
    list.innerHTML = cases.length ? cases.map(renderCaseCard).join("") : '<div class="module-empty">没有找到匹配的案例。</div>';
  } catch (error) { list.innerHTML = `<div class="module-empty">${escapeHtml(error.message)}</div>`; }
}

function renderCaseCard(item) {
  const number = item.guiding_case_number || item.case_number || item.cause || "公开案例";
  return `<article class="case-card" onclick="openCaseDetail(${item.id})">
    <div class="case-card-top"><span class="case-verified">✓ 来源已核验</span><span class="case-number">${escapeHtml(number)}</span></div>
    <h3>${escapeHtml(item.title)}</h3><p>${escapeHtml(item.summary)}</p>
    <div class="case-card-foot"><span>${escapeHtml(item.court_name || item.cause || "")}</span><span>阅读 ${item.view_count} · 收藏 ${item.favorite_count}</span></div>
  </article>`;
}

async function loadCaseRecommendations() {
  const target = document.getElementById("case-recommendations");
  if (!target || !document.getElementById("cases-personalization")?.checked) return;
  try {
    const data = await casesFetch("/api/cases/recommendations?limit=6");
    target.innerHTML = (data.cases || []).map(item => `<button class="case-recommendation-card" onclick="openCaseDetail(${item.id})"><b>${escapeHtml(item.title)}</b><p>${escapeHtml(item.summary.slice(0, 70))}</p><small>${escapeHtml(item.recommendation?.reasons?.[0] || "权威案例")}</small></button>`).join("") || '<div class="module-empty">浏览、搜索或收藏案例后，推荐会逐步贴合你的关注方向。</div>';
  } catch (error) { target.innerHTML = `<div class="module-empty">${escapeHtml(error.message)}</div>`; }
}

async function updateCasePersonalization(enabled) {
  try {
    await casesFetch("/api/cases/personalization", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ enabled }) });
    document.getElementById("case-recommendation-section").classList.toggle("hidden", !enabled);
    if (enabled) await loadCaseRecommendations();
  } catch (error) { alert(error.message); }
}

async function openCaseDetail(caseId) {
  casesState.currentCaseId = Number(caseId);
  const modal = document.getElementById("case-detail-modal");
  const target = document.getElementById("case-detail-content");
  modal.classList.remove("hidden"); target.innerHTML = '<div class="module-loading">正在整理案例结构…</div>';
  try {
    const data = await casesFetch(`/api/cases/${caseId}`);
    const item = data.case;
    const refs = (item.law_references || []).map(ref => `${escapeHtml(ref.law_name)} ${escapeHtml(ref.article || "")}`).join(" · ");
    target.innerHTML = `<div class="case-detail-lead"><button class="case-detail-save" onclick="toggleCaseFavorite(${item.id})">${item.favorited ? "★ 已收藏" : "☆ 收藏案例"}</button><div class="case-detail-meta"><span>✓ 已核验</span><span>${escapeHtml(item.guiding_case_number || item.case_number || "")}</span><span>${escapeHtml(item.court_name || "")}</span><span>${escapeHtml(item.decision_date || "")}</span></div><h2>${escapeHtml(item.title)}</h2><div class="case-keywords">${(item.keywords || []).map(word => `<i>${escapeHtml(word)}</i>`).join("")}</div></div>
      <div class="case-structure">
        ${caseSection("案例摘要", item.summary, "full")}${caseSection("争议焦点", item.dispute_focus)}${caseSection("裁判结果", item.judgment_result)}${caseSection("裁判逻辑", item.judgment_reasoning, "full")}${caseSection("AI 通俗解读", item.ai_plain_language, "full ai")}
      </div>
      <div class="case-source"><b>来源：</b>${escapeHtml(item.source.publisher || "权威公开来源")} · ${escapeHtml(item.source.type || "")}　<a href="${escapeHtml(item.source.url)}" target="_blank" rel="noopener noreferrer">查看官方原文 ↗</a>${refs ? `<div class="case-law-refs">涉及法律：${refs}</div>` : ""}</div>
      ${renderCaseCrosslinks(item)}`;
  } catch (error) { target.innerHTML = `<div class="module-empty">${escapeHtml(error.message)}</div>`; }
}

function caseSection(title, body, extra = "") { return `<section class="case-section ${extra}"><h4>${title}</h4><p>${escapeHtml(body || "暂无公开信息")}</p></section>`; }

function renderCaseCrosslinks(item) {
  const related = (item.related_cases || []).map(entry => `<button onclick="openCaseDetail(${entry.id})">${escapeHtml(entry.title)}</button>`).join("") || '<span class="privacy-note">暂无相关案例</span>';
  const discussions = (item.community_discussions || []).map(entry => `<button onclick="closeCaseDetail();switchModule('community');openCommunityPost(${entry.id})">${escapeHtml(entry.title)}</button>`).join("") || '<span class="privacy-note">社区还没有相关讨论</span>';
  return `<div class="crosslink-grid"><section><h3>相关案例</h3><div class="crosslink-list">${related}</div></section><section><h3>社区讨论</h3><div class="crosslink-list">${discussions}</div></section></div>`;
}

async function toggleCaseFavorite(id) { try { await casesFetch(`/api/cases/${id}/favorite`, { method: "POST" }); await openCaseDetail(id); loadCases(); loadCaseRecommendations(); } catch (error) { alert(error.message); } }
function closeCaseDetail() { document.getElementById("case-detail-modal")?.classList.add("hidden"); }
