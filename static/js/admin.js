"use strict";

const adminState = { user: null, users: [], administrators: [], hasApiKey: false };
const adminElement = id => document.getElementById(id);

function isAdministrator(user) {
  return Boolean(user && (user.is_admin || user.role === "admin"));
}

function adminUnlimited(user) {
  return Boolean(user && (user.ai_unlimited || user.quota_mode === "unlimited" ||
    user.is_approved || user.free_api_remaining === null || user.remaining === null));
}

function adminText(tag, content, className = "") {
  const element = document.createElement(tag);
  element.textContent = String(content ?? "");
  if (className) element.className = className;
  return element;
}

function adminSafeMessage(value) {
  let message = String(value || "操作失败，请稍后重试");
  const key = adminElement("admin-model-key").value.trim();
  if (key) message = message.split(key).join("[密钥已隐藏]");
  return message;
}

function adminMessage(id, message = "", kind = "") {
  const element = adminElement(id);
  element.textContent = message ? adminSafeMessage(message) : "";
  element.classList.remove("error", "success");
  if (kind) element.classList.add(kind);
}

function clearAdminView(note = "请使用管理员账号登录。") {
  adminState.user = null;
  adminState.users = [];
  adminState.administrators = [];
  adminState.hasApiKey = false;
  adminElement("admin-dashboard").classList.add("hidden");
  adminElement("admin-login-view").classList.remove("hidden");
  adminElement("admin-identity").textContent = "";
  adminElement("admin-identity").classList.add("hidden");
  adminElement("admin-logout").classList.add("hidden");
  ["admin-users-list", "admin-administrators-list", "admin-metrics"].forEach(id => adminElement(id).replaceChildren());
  ["admin-model-form", "admin-profile-form", "admin-test-user-form"].forEach(id => adminElement(id).reset());
  adminElement("admin-model-key-status").textContent = "";
  adminElement("admin-user-count").textContent = "";
  adminElement("admin-access-note").textContent = note;
  ["admin-page-message", "admin-model-message", "admin-profile-message", "admin-test-user-message"].forEach(id => adminMessage(id));
}

function showAdminView(user) {
  if (!isAdministrator(user)) return false;
  adminState.user = user;
  adminElement("admin-login-view").classList.add("hidden");
  adminElement("admin-dashboard").classList.remove("hidden");
  adminElement("admin-identity").textContent = user.username;
  adminElement("admin-identity").classList.remove("hidden");
  adminElement("admin-logout").classList.remove("hidden");
  adminElement("admin-profile-username").value = user.username;
  adminElement("admin-login-password").value = "";
  return true;
}

async function adminRequest(url, options = {}) {
  const protectedRequest = url.startsWith("/api/admin/") && url !== "/api/admin/login";
  if (protectedRequest && !isAdministrator(adminState.user)) throw new Error("请先登录管理员账号。");
  const response = await fetch(url, { credentials: "same-origin", cache: "no-store", ...options });
  const data = await response.json().catch(() => ({}));
  const profilePasswordIncorrect = response.status === 401 && url === "/api/admin/profile" && data.code === "CURRENT_PASSWORD_INCORRECT";
  if (protectedRequest && !profilePasswordIncorrect && (response.status === 401 || response.status === 403)) {
    const error = adminSafeMessage(data.error || "管理员登录已失效，请重新登录。");
    clearAdminView("管理员登录已失效，请重新登录。");
    throw new Error(error);
  }
  if (!response.ok || data.error || data.status === "error") throw new Error(adminSafeMessage(data.error || data.message || "请求失败，请稍后重试。"));
  return data;
}

function adminPost(url, body) {
  return adminRequest(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
}

async function adminBusy(form, action) {
  const buttons = Array.from(form.querySelectorAll("button"));
  buttons.forEach(button => { button.disabled = true; });
  try { return await action(); }
  finally { buttons.forEach(button => { button.disabled = false; }); }
}

async function initAdminPage() {
  try {
    const data = await adminRequest("/api/auth/status");
    if (data.authenticated && showAdminView(data.user)) await loadAdminDashboard();
    else clearAdminView(data.authenticated ? "当前登录的是普通用户账号，请使用独立管理员账号登录。" : "请使用管理员账号登录。");
  } catch (error) {
    clearAdminView("无法检查登录状态，请重新登录或刷新页面。");
  }
}

async function adminLogin(event) {
  event.preventDefault();
  const username = adminElement("admin-login-username").value.trim();
  const password = adminElement("admin-login-password").value;
  if (!username || !password) return adminMessage("admin-login-message", "请输入用户名和密码。", "error");
  adminMessage("admin-login-message");
  await adminBusy(adminElement("admin-login-form"), async () => {
    try {
      const data = await adminPost("/api/admin/login", { username, password });
      if (!showAdminView(data.user)) throw new Error("此账号没有管理员权限。");
      await loadAdminDashboard();
    } catch (error) {
      adminMessage("admin-login-message", error.message, "error");
    } finally { adminElement("admin-login-password").value = ""; }
  });
}

async function adminLogout() {
  try {
    await adminPost("/api/auth/logout");
    clearAdminView("已退出管理员账号。");
  } catch (error) { adminMessage("admin-page-message", error.message, "error"); }
}

async function loadAdminDashboard() {
  if (!isAdministrator(adminState.user)) return;
  adminMessage("admin-page-message", "正在加载…");
  const results = await Promise.allSettled([loadAdminUsers(), loadAdminMetrics(), loadAdminModelConfig()]);
  if (!isAdministrator(adminState.user)) return;
  const failures = results.filter(result => result.status === "rejected");
  adminMessage("admin-page-message", failures.length ? failures.map(result => result.reason.message).join("；") : "", failures.length ? "error" : "");
}

async function loadAdminUsers() {
  const data = await adminRequest("/api/admin/all-users");
  if (!isAdministrator(adminState.user)) return;
  adminState.users = (data.users || []).filter(user => !isAdministrator(user));
  adminState.administrators = (data.administrators || []).filter(isAdministrator);
  renderAdminUsers();
  renderAdministrators();
}

function adminApprovalTime(value) {
  if (!value) return "申请时间未知";
  const raw = String(value);
  const date = new Date(/(?:Z|[+-]\d{2}:\d{2})$/i.test(raw) ? raw : `${raw}Z`);
  return Number.isNaN(date.getTime()) ? "申请时间未知" : date.toLocaleString("zh-CN", { hour12: false });
}

function adminUserBadge(user) {
  if (user.has_llm_api_key) return adminText("span", "个人 API", "badge success");
  if (adminUnlimited(user)) return adminText("span", "AI 不限次数", "badge success");
  const remaining = Number.isFinite(Number(user.free_api_remaining)) ? Number(user.free_api_remaining) : 10;
  const limit = Number.isFinite(Number(user.free_api_limit)) ? Number(user.free_api_limit) : 10;
  return adminText("span", `免费 ${remaining}/${limit}`, remaining <= 0 ? "badge danger" : "badge");
}

function adminUserAction(label, user, action, danger = false) {
  const button = adminText("button", label, danger ? "danger" : "");
  button.type = "button";
  button.addEventListener("click", () => updateAdminUser(user, action, button));
  return button;
}

function renderAdminUsers() {
  const query = adminElement("admin-user-search").value.trim().toLocaleLowerCase();
  const filter = adminElement("admin-user-filter").value;
  const users = adminState.users.filter(user => {
    if (!String(user.username || "").toLocaleLowerCase().includes(query)) return false;
    if (filter === "pending") return user.approval_requested && !user.is_approved;
    if (filter === "unlimited") return adminUnlimited(user);
    if (filter === "trial") return !adminUnlimited(user) && !user.has_llm_api_key;
    return true;
  });
  const list = adminElement("admin-users-list");
  list.replaceChildren();
  adminElement("admin-user-count").textContent = `共 ${adminState.users.length} 位用户`;
  if (!users.length) {
    list.appendChild(adminText("p", adminState.users.length ? "没有符合条件的用户。" : "暂无普通用户。", "empty-note"));
    return;
  }
  for (const user of users) {
    const row = adminText("article", "", "user-row");
    const info = adminText("div", "", "user-info");
    info.appendChild(adminText("div", user.username, "user-name"));
    const tags = adminText("div", "", "user-tags");
    tags.appendChild(adminUserBadge(user));
    if (user.approval_requested && !user.is_approved) tags.appendChild(adminText("span", "待审批", "badge"));
    if (user.approval_requested_at) tags.appendChild(adminText("span", `申请于 ${adminApprovalTime(user.approval_requested_at)}`, "muted"));
    info.appendChild(tags);
    const actions = adminText("div", "", "user-actions");
    if (!user.is_approved) actions.appendChild(adminUserAction("开通不限次数", user, "approve"));
    if (user.approval_requested && !user.is_approved) actions.appendChild(adminUserAction("驳回申请", user, "reject"));
    if (user.is_approved) actions.appendChild(adminUserAction("撤销开通", user, "revoke", true));
    actions.appendChild(adminUserAction("删除用户", user, "delete-user", true));
    row.appendChild(info);
    row.appendChild(actions);
    list.appendChild(row);
  }
}

function renderAdministrators() {
  const list = adminElement("admin-administrators-list");
  list.replaceChildren();
  for (const user of adminState.administrators) {
    const item = adminText("div", "", "administrator");
    item.appendChild(adminText("strong", user.username));
    item.appendChild(adminText("span", user.id === adminState.user?.id ? "当前账号" : "管理员", "badge"));
    list.appendChild(item);
  }
  if (!adminState.administrators.length) list.appendChild(adminText("p", "暂未取得管理员账号列表。", "empty-note"));
}

async function updateAdminUser(user, action, button) {
  if (!Number.isInteger(Number(user.id)) || isAdministrator(user)) return;
  if (action === "delete-user" && !confirm(`确定删除用户“${user.username}”及其历史记录吗？此操作无法撤销。`)) return;
  if (action === "revoke" && !confirm(`确定撤销用户“${user.username}”的不限次数权限吗？`)) return;
  button.disabled = true;
  try {
    await adminPost(`/api/admin/${action}/${Number(user.id)}`);
    adminMessage("admin-page-message", "用户权限已更新。", "success");
    await Promise.all([loadAdminUsers(), loadAdminMetrics()]);
  } catch (error) { adminMessage("admin-page-message", error.message, "error"); }
  finally { button.disabled = false; }
}

async function loadAdminMetrics() {
  const data = await adminRequest("/api/admin/metrics");
  if (!isAdministrator(adminState.user)) return;
  const users = data.users || {};
  const usage = data.usage || {};
  const entries = [["普通用户", users.total], ["额度已用完", users.quota_exhausted], ["个人 API 用户", users.personal_api], ["今日 AI 调用", usage.today], ["近 7 日 AI 调用", usage.last_7_days]];
  const container = adminElement("admin-metrics");
  container.replaceChildren();
  entries.forEach(([label, count]) => {
    const item = adminText("div", "", "metric");
    item.appendChild(adminText("strong", Number(count || 0).toLocaleString("zh-CN")));
    item.appendChild(adminText("span", label));
    container.appendChild(item);
  });
}

async function loadAdminModelConfig() {
  const data = await adminRequest("/api/admin/model-config");
  if (!isAdministrator(adminState.user)) return;
  adminState.hasApiKey = Boolean(data.has_api_key);
  adminElement("admin-model-key").value = "";
  adminElement("admin-model-key").placeholder = data.has_api_key ? "已保存；输入新密钥可替换" : "请输入 API Key";
  adminElement("admin-model-key-status").textContent = data.has_api_key ? "服务密钥已保存" : "尚未设置服务密钥";
  adminElement("admin-model-base-url").value = data.base_url || "https://api.deepseek.com/v1";
  const models = ["deepseek-flash", "deepseek-v4-pro", "deepseek-chat"];
  adminElement("admin-model-name").value = models.includes(data.model) ? data.model : "deepseek-flash";
}

function adminModelValues() {
  const values = {
    base_url: adminElement("admin-model-base-url").value.trim(),
    model: adminElement("admin-model-name").value,
  };
  const key = adminElement("admin-model-key").value.trim();
  if (key) values.api_key = key;
  return values;
}

async function saveAdminModel(event) {
  event.preventDefault();
  const values = adminModelValues();
  if (!adminState.hasApiKey && !values.api_key) return adminMessage("admin-model-message", "请输入服务 API Key。", "error");
  await adminBusy(adminElement("admin-model-form"), async () => {
    try {
      await adminPost("/api/admin/model-config", values);
      adminElement("admin-model-key").value = "";
      await loadAdminModelConfig();
      adminMessage("admin-model-message", "全局配置已保存。", "success");
    } catch (error) { adminMessage("admin-model-message", error.message, "error"); }
  });
}

async function testAdminModel() {
  const values = adminModelValues();
  if (!adminState.hasApiKey && !values.api_key) return adminMessage("admin-model-message", "请输入服务 API Key。", "error");
  await adminBusy(adminElement("admin-model-form"), async () => {
    adminMessage("admin-model-message", "正在测试连接…");
    try {
      await adminPost("/api/admin/model-config/test", values);
      adminMessage("admin-model-message", "连接测试成功。", "success");
    } catch (error) { adminMessage("admin-model-message", error.message, "error"); }
  });
}

async function saveAdminProfile(event) {
  event.preventDefault();
  const username = adminElement("admin-profile-username").value.trim();
  const currentPassword = adminElement("admin-current-password").value;
  const password = adminElement("admin-new-password").value;
  const confirmation = adminElement("admin-confirm-password").value;
  if (!currentPassword) return adminMessage("admin-profile-message", "请输入当前密码。", "error");
  if (username && username.length < 3) return adminMessage("admin-profile-message", "用户名至少 3 个字符。", "error");
  if (password && password.length < 12) return adminMessage("admin-profile-message", "管理员新密码至少 12 位。", "error");
  if (password !== confirmation) return adminMessage("admin-profile-message", "两次输入的新密码不一致。", "error");
  await adminBusy(adminElement("admin-profile-form"), async () => {
    try {
      const data = await adminPost("/api/admin/profile", { current_password: currentPassword, username, password });
      if (data.user) showAdminView(data.user);
      else if (username) showAdminView({ ...adminState.user, username });
      ["admin-current-password", "admin-new-password", "admin-confirm-password"].forEach(id => { adminElement(id).value = ""; });
      await loadAdminUsers();
      adminMessage("admin-profile-message", "我的账号已更新。", "success");
    } catch (error) { adminMessage("admin-profile-message", error.message, "error"); }
  });
}

async function createAdminTestUser(event) {
  event.preventDefault();
  const username = adminElement("test-user-username").value.trim();
  const password = adminElement("test-user-password").value;
  if (username.length < 3 || password.length < 12) return adminMessage("admin-test-user-message", "用户名至少 3 个字符，密码至少 12 位。", "error");
  await adminBusy(adminElement("admin-test-user-form"), async () => {
    try {
      await adminPost("/api/admin/test-users", { username, password });
      adminElement("admin-test-user-form").reset();
      await Promise.all([loadAdminUsers(), loadAdminMetrics()]);
      adminMessage("admin-test-user-message", "普通测试账号已创建，并已开通不限次数。", "success");
    } catch (error) { adminMessage("admin-test-user-message", error.message, "error"); }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  adminElement("admin-login-form").addEventListener("submit", adminLogin);
  adminElement("admin-logout").addEventListener("click", adminLogout);
  adminElement("admin-refresh").addEventListener("click", loadAdminDashboard);
  adminElement("admin-user-search").addEventListener("input", renderAdminUsers);
  adminElement("admin-user-filter").addEventListener("change", renderAdminUsers);
  adminElement("admin-model-form").addEventListener("submit", saveAdminModel);
  adminElement("admin-model-test").addEventListener("click", testAdminModel);
  adminElement("admin-profile-form").addEventListener("submit", saveAdminProfile);
  adminElement("admin-test-user-form").addEventListener("submit", createAdminTestUser);
  initAdminPage();
});

window.addEventListener("pagehide", () => {
  ["admin-model-key", "admin-login-password", "admin-current-password", "admin-new-password", "admin-confirm-password", "test-user-password"].forEach(id => { adminElement(id).value = ""; });
});
