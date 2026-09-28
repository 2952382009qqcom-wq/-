const casesState = { categories: [], category: "", audience: "", feed: "latest", page: 1, hasNext: false, currentCaseId: null };

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
    const studentAudience = (data.audiences || []).find(item => item.slug === "student-verified");
    const studentChip = studentAudience
      ? `<button type="button" class="student-case-chip" data-category="" data-audience="student-verified" title="${escapeHtml(studentAudience.description || "")}">${escapeHtml(studentAudience.name)} · ${studentAudience.count || 0}</button>`
      : "";
    chips.innerHTML = `<button type="button" class="active" data-category="" data-audience="">全部场景</button>${studentChip}${casesState.categories.map(item => `<button type="button" data-category="${escapeHtml(item.slug)}" data-audience="">${escapeHtml(item.name)}</button>`).join("")}`;
    chips.querySelectorAll("button").forEach(button => button.addEventListener("click", () => {
      casesState.category = button.dataset.category || "";
      casesState.audience = button.dataset.audience || "";
      chips.querySelectorAll("button").forEach(item => item.classList.toggle("active", item === button));
      document.getElementById("student-case-note")?.classList.toggle("hidden", casesState.audience !== "student-verified");
      loadCases({ reset: true });
    }));
    document.querySelectorAll("#cases-feeds button").forEach(button => button.addEventListener("click", () => {
      casesState.feed = button.dataset.feed;
      document.querySelectorAll("#cases-feeds button").forEach(item => item.classList.toggle("active", item === button));
      loadCases({ reset: true });
    }));
  }
  const tasks = [loadCases()];
  if (document.getElementById("cases-personalization")?.checked) tasks.push(loadCaseRecommendations());
  await Promise.all(tasks);
}

async function loadCases({ reset = true } = {}) {
  const list = document.getElementById("cases-list");
  if (!list || !window._user) return;
  if (reset) {
    casesState.page = 1;
    list.innerHTML = '<div class="module-loading">正在载入权威案例…</div>';
  }
  const params = new URLSearchParams({ feed: casesState.feed, per_page: "20", page: String(casesState.page) });
  const query = document.getElementById("cases-query")?.value.trim();
  if (casesState.category) params.set("category", casesState.category);
  if (casesState.audience) params.set("audience", casesState.audience);
  if (query) params.set("q", query);
  try {
    const data = await casesFetch(`/api/cases?${params}`);
    const cases = data.cases || [];
    document.getElementById("cases-total").textContent = `共 ${data.pagination?.total || 0} 个已核验案例`;
    const markup = cases.map(renderCaseCard).join("");
    if (reset) list.innerHTML = cases.length ? markup : '<div class="module-empty">没有找到匹配的案例。</div>';
    else list.insertAdjacentHTML("beforeend", markup);
    casesState.hasNext = Boolean(data.pagination?.has_next);
    document.getElementById("cases-load-more")?.classList.toggle("hidden", !casesState.hasNext);
  } catch (error) { list.innerHTML = `<div class="module-empty">${escapeHtml(error.message)}</div>`; }
}

async function loadMoreCases() {
  if (!casesState.hasNext) return;
  casesState.page += 1;
  await loadCases({ reset: false });
}

function renderCaseCard(item) {
  const number = item.guiding_case_number || item.case_number || item.cause || "公开案例";
  const category = item.categories?.[0]?.name || "典型案例";
  const year = item.reference_year ? `${item.reference_year}年` : "年份以原文为准";
  const image = item.media?.image_url;
  const visual = image
    ? `<div class="case-card-media"><img src="${escapeHtml(image)}" alt="${escapeHtml(item.media?.image_alt || item.title)}" loading="lazy" referrerpolicy="no-referrer"></div>`
    : `<div class="case-card-media case-card-placeholder" data-domain="${escapeHtml(item.legal_domain || "civil")}"><span>${escapeHtml(category.slice(0, 4))}</span></div>`;
  return `<article class="case-card" onclick="openCaseDetail(${item.id})">
    ${visual}
    <div class="case-card-top"><span class="case-verified">✓ ${escapeHtml(category)}</span><span class="case-number">${escapeHtml(year)} · ${escapeHtml(number)}</span></div>
    <h3>${escapeHtml(item.title)}</h3><p>${escapeHtml(item.summary)}</p>
    <div class="case-card-foot"><span>${escapeHtml(item.court_name || item.cause || "")}</span><span>阅读 ${item.view_count} · 收藏 ${item.favorite_count}</span></div>
  </article>`;
}

async function loadCaseRecommendations() {
  const target = document.getElementById("case-recommendations");
  if (!target || !document.getElementById("cases-personalization")?.checked) return;
  try {
    const params = new URLSearchParams({ limit: "6" });
    const query = document.getElementById("cases-query")?.value.trim();
    if (query) params.set("q", query);
    else if (typeof legalAgentState !== "undefined" && legalAgentState.conversationId) params.set("conversation_id", legalAgentState.conversationId);
    const data = await casesFetch(`/api/cases/recommendations?${params}`);
    renderCaseContext(data.context || {});
    target.innerHTML = (data.cases || []).map(item => {
      const year = item.reference_year ? `${item.reference_year}年` : "年份见原文";
      const reason = item.recommendation?.reasons?.[0] || "与当前法律场景相关";
      return `<button class="case-recommendation-card" onclick="openCaseDetail(${item.id})"><span>${escapeHtml(year)} · ${escapeHtml(item.categories?.[0]?.name || "典型案例")}</span><b>${escapeHtml(item.title)}</b><p>${escapeHtml(item.summary.slice(0, 82))}</p><small>${escapeHtml(reason)}</small></button>`;
    }).join("") || '<div class="module-empty">当前咨询没有找到足够可靠且较新的匹配案例。你可以补充更具体的事实，或用上方关键词检索。</div>';
  } catch (error) { target.innerHTML = `<div class="module-empty">${escapeHtml(error.message)}</div>`; }
}

function renderCaseContext(context) {
  const title = document.getElementById("case-context-title");
  const copy = document.getElementById("case-context-copy");
  const banner = document.getElementById("case-context-banner");
  if (!title || !copy || !banner) return;
  const fromConversation = context.source === "conversation";
  title.textContent = fromConversation ? `正在关联：${context.label || "最近一次咨询"}` : (context.label || "尚无咨询上下文");
  copy.textContent = context.domain && context.domain !== "other"
    ? `识别为“${context.domain_label || "综合法律问题"}”场景，只展示明确匹配的案例。`
    : "尚未识别出明确法律场景；完成一次咨询或输入检索词后再为你匹配。";
  banner.classList.toggle("has-context", fromConversation || context.source === "search");
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
    const refs = (item.law_references || []).map(ref => `<li><b>${escapeHtml(ref.law_name)} ${escapeHtml(ref.article || "")}</b>${ref.note ? `<span>${escapeHtml(ref.note)}</span>` : ""}</li>`).join("");
    const hero = item.media?.image_url ? `<figure class="case-detail-media"><img src="${escapeHtml(item.media.image_url)}" alt="${escapeHtml(item.media.image_alt || item.title)}"><figcaption>图片来源：<a href="${escapeHtml(item.media.image_source_url || item.source.url)}" target="_blank" rel="noopener noreferrer">官方原页</a></figcaption></figure>` : "";
    target.innerHTML = `${hero}<div class="case-detail-lead"><button class="case-detail-save" onclick="toggleCaseFavorite(${item.id})">${item.favorited ? "★ 已收藏" : "☆ 收藏案例"}</button><div class="case-detail-meta"><span>✓ 已核验</span><span>${escapeHtml(item.guiding_case_number || item.case_number || "")}</span><span>${escapeHtml(item.court_name || "")}</span><span>${escapeHtml(item.decision_date || "")}</span></div><h2>${escapeHtml(item.title)}</h2><div class="case-keywords">${(item.keywords || []).map(word => `<i>${escapeHtml(word)}</i>`).join("")}</div></div>
      <div class="case-structure">
        ${caseSection("案例摘要", item.summary, "full")}${caseSection("争议焦点", item.dispute_focus)}${caseSection("裁判结果", item.judgment_result)}${caseSection("裁判逻辑", item.judgment_reasoning, "full")}${caseSection("AI 通俗解读", item.ai_plain_language, "full ai")}
      </div>
      <div class="case-source"><b>来源：</b>${escapeHtml(item.source.publisher || "权威公开来源")} · ${escapeHtml(item.source.type || "")}　<a href="${escapeHtml(item.source.url)}" target="_blank" rel="noopener noreferrer">查看官方原文 ↗</a>${refs ? `<div class="case-law-refs"><h4>关联法条与阅读提示</h4><ul>${refs}</ul></div>` : ""}</div>
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
