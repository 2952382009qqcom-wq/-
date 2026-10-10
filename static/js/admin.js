'use strict';

/* 明鉴 · 管理控制台。管理员独立入口，只做项目管理，不含任何普通用户功能。 */

const state = {
  user: null,
  sessionVersion: 0,
  review: { page: 1 },
  section: 'dashboard',
  users: { q: '', status: 'all', page: 1, list: [] },
  community: { q: '', status: 'all', page: 1 },
  cases: { q: '', status: '', verification_status: '', legal_domain: '', page: 1, filters: null, editingId: null },
  audit: { q: '', page: 1 },
  logs: { q: '', action: '', page: 1 },
  bw: { list: [] },
};

const SECTIONS = {
  dashboard: '概览', users: '用户管理', review: '内容审核', reports: '举报处理',
  cases: '案例库', audit: '会话审计', logs: '操作日志', system: '系统配置',
};

function $(id) { return document.getElementById(id); }

function esc(value) {
  return String(value == null ? '' : value).replace(/[&<>"']/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
  ));
}

async function api(url, options = {}) {
  const protectedRequest = (url.startsWith('/api/admin/') && url !== '/api/admin/login') || url.startsWith('/api/community/moderation/');
  if (protectedRequest && !(state.user && state.user.is_admin)) throw new Error('请先登录管理员账号');
  const version = state.sessionVersion;
  const opts = Object.assign({ headers: {} }, options);
  if (opts.body && !opts.headers['Content-Type']) opts.headers['Content-Type'] = 'application/json';
  const resp = await fetch(url, opts);
  const data = await resp.json().catch(() => ({}));
  const profileIncorrect = url === '/api/admin/profile' && data.code === 'CURRENT_PASSWORD_INCORRECT';
  if (protectedRequest && [401, 403].includes(resp.status) && !profileIncorrect) resetConsole();
  if (!resp.ok || data.status === 'error') throw new Error(safeMessage(data.error || data.message || ('请求失败（' + resp.status + '）')));
  if (protectedRequest && version !== state.sessionVersion) throw new Error('登录状态已改变，请重新登录');
  return data;
}

function safeMessage(message) {
  const key = $('cfg-key');
  const secret = key && key.value.trim();
  return secret ? String(message).split(secret).join('[密钥已隐藏]') : String(message);
}

function resetConsole() {
  state.user = null;
  state.sessionVersion += 1;
  state.users.list = [];
  state.bw.list = [];
  _confirmCb = null;
  $('admin-app').classList.add('hidden');
  $('admin-login').classList.remove('hidden');
  $('admin-login-password').value = '';
  $('admin-who').textContent = '';
  $('admin-view').innerHTML = '';
  closeAdminModal();
}

function toast(message, isError = false) {
  let box = $('admin-toast');
  if (!box) {
    box = document.createElement('div');
    box.id = 'admin-toast';
    box.style.cssText = 'position:fixed;top:20px;right:24px;z-index:200;padding:10px 16px;border-radius:8px;color:#fff;font-size:13px;box-shadow:0 8px 24px rgba(0,0,0,.2);transition:opacity .3s;';
    document.body.appendChild(box);
  }
  box.textContent = message;
  box.style.background = isError ? '#a8364b' : '#3d6b4f';
  box.style.opacity = '1';
  clearTimeout(box._timer);
  box._timer = setTimeout(() => { box.style.opacity = '0'; }, 2400);
}

function errorBlock(message) {
  return '<div class="admin-empty">加载失败：' + esc(message) + '</div>';
}

function metricCard(value, label) {
  return '<div class="admin-card"><strong>' + esc(value) + '</strong><span>' + esc(label) + '</span></div>';
}

function paginationHtml(p, fn) {
  const pages = Math.max(1, p.pages || 1);
  return '<div class="admin-pagination">'
    + '<button class="admin-btn small" ' + (p.has_prev ? '' : 'disabled') + ' onclick="' + fn + '(-1)">上一页</button>'
    + '<span>第 ' + p.page + '/' + pages + ' 页 · 共 ' + p.total + ' 条</span>'
    + '<button class="admin-btn small" ' + (p.has_next ? '' : 'disabled') + ' onclick="' + fn + '(1)">下一页</button>'
    + '</div>';
}

const statusLabel = (v) => ({ draft: '草稿', published: '已发布', hidden: '已隐藏', deleted: '已删除' }[v] || v);
const verifyLabel = (v) => ({ pending: '待核验', verified: '已核验', stale: '已过时', rejected: '已驳回' }[v] || v);
const sourceTypeLabel = (v) => ({ official_court: '法院官方', official_gazette: '公报', public_database: '公开数据库', manual: '人工录入' }[v] || v);
const severityLabel = (v) => ({ high: '高危', medium: '中危', low: '低危' }[v] || v);
const reportStatusLabel = (v) => ({ pending: '待处理', resolved: '已处理', dismissed: '已驳回' }[v] || v);
const userStatusLabel = (v) => ({ all: '全部', approved: '已授权', pending: '待审核', inactive: '未授权' }[v] || v);

const ACTION_LABELS = {
  user_approve: '通过用户', user_reject: '驳回用户', user_revoke: '撤销权限',
  user_delete: '删除用户', user_set_model: '设置模型', user_reset_quota: '重置额度',
  case_create: '新建案例', case_update: '更新案例', case_delete: '删除案例',
  community_moderate: '社区审核', report_resolve: '处理举报',
  review_approve: '审核通过', review_reject: '审核驳回', review_delete: '审核删除',
  banned_word_create: '新增违禁词', banned_word_update: '更新违禁词', banned_word_delete: '删除违禁词',
};

function severityBadge(v) {
  const cls = { high: 'bad', medium: 'warn', low: '' }[v] || '';
  return '<span class="badge ' + cls + '">' + esc(severityLabel(v)) + '</span>';
}

// 危险操作二次确认弹窗
let _confirmCb = null;
function confirmAction(title, message, confirmLabel, onConfirm) {
  _confirmCb = onConfirm;
  openAdminModal(title, '<p class="admin-confirm-text">' + esc(message) + '</p>'
    + '<div class="admin-actions"><button class="admin-btn danger" onclick="runConfirm()">' + esc(confirmLabel || '确定') + '</button>'
    + '<button class="admin-btn" onclick="closeAdminModal()">取消</button></div>');
}
function runConfirm() {
  const cb = _confirmCb;
  _confirmCb = null;
  closeAdminModal();
  if (cb) cb();
}

function barChart(series) {
  if (!series || !series.length) return '<div class="admin-empty">暂无数据</div>';
  const values = series.map((d) => Math.max(Number(d.users) || 0, Number(d.posts) || 0));
  const max = Math.max(1, ...values);
  const bars = series.map((d) => {
    const uh = Math.round(((Number(d.users) || 0) / max) * 100);
    const ph = Math.round(((Number(d.posts) || 0) / max) * 100);
    return '<div class="admin-chart-col" title="' + esc(d.date) + ' 新增用户 ' + (d.users || 0) + ' / 帖子 ' + (d.posts || 0) + '">'
      + '<div class="admin-chart-bars">'
      + '<span class="bar users" style="height:' + uh + '%"></span>'
      + '<span class="bar posts" style="height:' + ph + '%"></span>'
      + '</div>'
      + '<span class="admin-chart-label">' + esc(String(d.date).slice(5)) + '</span></div>';
  }).join('');
  return '<div class="admin-chart">' + bars + '</div>'
    + '<div class="admin-chart-legend"><span><i class="dot users"></i>新增用户</span><span><i class="dot posts"></i>新增帖子</span></div>';
}

// ===== 登录闸门 =====
async function adminLogin() {
  const username = $('admin-login-username').value.trim();
  const password = $('admin-login-password').value;
  const err = $('admin-login-error');
  err.textContent = '';
  if (!username || !password) { err.textContent = '请输入账号和密码'; return false; }
  try {
    const data = await api('/api/admin/login', { method: 'POST', body: JSON.stringify({ username, password }) });
    if (!data.user || !data.user.is_admin) {
      err.textContent = '该账号不是管理员，无法登录后台';
      return false;
    }
    enterConsole(data.user);
  } catch (e) {
    err.textContent = e.message;
  } finally { $('admin-login-password').value = ''; }
  return false;
}

async function adminLogout() {
  try { await api('/api/auth/logout', { method: 'POST' }); resetConsole(); }
  catch (e) { toast(e.message, true); }
}

function enterConsole(user) {
  if (!user || !user.is_admin) return;
  state.user = user;
  state.sessionVersion += 1;
  $('admin-login').classList.add('hidden');
  $('admin-app').classList.remove('hidden');
  $('admin-who').textContent = user.username;
  switchSection('dashboard');
}

function switchSection(name) {
  if (!SECTIONS[name]) return;
  state.section = name;
  document.querySelectorAll('#admin-nav button').forEach((b) => b.classList.toggle('active', b.dataset.section === name));
  $('admin-section-title').textContent = SECTIONS[name];
  $('admin-view').innerHTML = '<p class="admin-empty">加载中…</p>';
  ({ dashboard: renderDashboard, users: renderUsers, review: renderReview, reports: renderReports, cases: renderCases, audit: renderAudit, logs: renderLogs, system: renderSystem }[name])();
}

function wireEnter(id, fn) {
  const el = $(id);
  if (el) el.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); fn(); } });
}

// ===== 模态框 =====
function openAdminModal(title, html) {
  $('admin-modal-title').textContent = title;
  $('admin-modal-content').innerHTML = html;
  $('admin-modal').classList.remove('hidden');
}
function closeAdminModal() {
  $('admin-modal').classList.add('hidden');
  $('admin-modal-content').innerHTML = '';
}

// ===== 概览 =====
async function renderDashboard() {
  const view = $('admin-view');
  try {
    const [dash, system] = await Promise.all([api('/api/admin/dashboard'), api('/api/admin/system')]);
    const u = dash.users || {};
    const comp = system.components || {};
    view.innerHTML = ''
      + '<div class="admin-cards">'
      + metricCard(u.total || 0, '注册用户数')
      + metricCard(u.approved || 0, '已授权用户')
      + metricCard(u.pending || 0, '待审核申请')
      + metricCard(dash.today_posts || 0, '今日发帖量')
      + metricCard(dash.pending_reports || 0, '待处理举报')
      + metricCard(dash.pending_reviews || 0, '待审核内容')
      + metricCard(dash.posts_total || 0, '帖子总数')
      + metricCard(dash.comments_total || 0, '回复总数')
      + '</div>'
      + '<div class="admin-block-title">近 7 天趋势</div>'
      + barChart(dash.series || [])
      + '<div class="admin-block-title">运行状态</div>'
      + '<div class="admin-cards">'
      + metricCard(system.version, '版本')
      + metricCard(system.demo_mode ? '演示模式' : '正式模式', '当前模式')
      + metricCard(comp.database ? '正常' : '异常', '数据库')
      + metricCard(comp.external_model ? '已配置' : '未配置', '外部模型 API')
      + metricCard(comp.ocr ? '可用' : '不可用', 'OCR')
      + '</div>';
  } catch (e) {
    view.innerHTML = errorBlock(e.message);
  }
}

// ===== 用户管理 =====
async function renderUsers() {
  const view = $('admin-view');
  const s = state.users;
  try {
    const params = new URLSearchParams({ q: s.q, status: s.status, page: String(s.page), per_page: '20' });
    const data = await api('/api/admin/users?' + params);
    s.list = data.users || [];
    const rows = s.list.length
      ? s.list.map(userRow).join('')
      : '<tr><td colspan="7" class="admin-empty">暂无用户</td></tr>';
    view.innerHTML = ''
      + '<div class="admin-toolbar">'
      + '<input type="search" id="user-q" value="' + esc(s.q) + '" placeholder="搜索用户名">'
      + '<select id="user-status">'
      + ['all', 'approved', 'pending', 'inactive'].map((v) => '<option value="' + v + '"' + (s.status === v ? ' selected' : '') + '>' + userStatusLabel(v) + '</option>').join('')
      + '</select>'
      + '<button class="admin-btn" onclick="applyUserFilter()">查询</button>'
      + '<button class="admin-btn primary" onclick="openTestUserForm()">新建测试账号</button>'
      + '</div>'
      + '<div class="admin-table-wrap"><table class="admin-table"><thead><tr>'
      + '<th>ID</th><th>用户名</th><th>角色</th><th>状态</th><th>额度</th><th>默认模型</th><th>操作</th>'
      + '</tr></thead><tbody>' + rows + '</tbody></table></div>'
      + paginationHtml(data.pagination || { page: 1, pages: 1, total: 0 }, 'usersPage');
    wireEnter('user-q', applyUserFilter);
  } catch (e) {
    view.innerHTML = errorBlock(e.message);
  }
}

function userRow(u) {
  const role = u.is_admin ? '<span class="badge warn">管理员</span>' : '<span class="badge">普通用户</span>';
  let status;
  if (u.is_admin) status = '<span class="badge ok">内置</span>';
  else if (u.is_approved) status = '<span class="badge ok">已授权</span>';
  else if (u.approval_requested) status = '<span class="badge warn">待审核</span>';
  else status = '<span class="badge">未申请</span>';
  const quota = u.is_admin ? '—' : ((u.ai_unlimited || u.is_approved || u.free_api_remaining === null) ? '不限应用次数' : (u.free_api_remaining + '/' + u.free_api_limit)) + (u.has_llm_api_key ? ' · 个人API' : '');
  const actions = [];
  if (!u.is_admin) {
    if (!u.is_approved) actions.push('<button class="admin-btn small primary" onclick="approveUser(' + u.id + ')">通过</button>');
    if (u.approval_requested) actions.push('<button class="admin-btn small" onclick="rejectUser(' + u.id + ')">驳回</button>');
    if (u.is_approved) actions.push('<button class="admin-btn small" onclick="revokeUser(' + u.id + ')">撤销权限</button>');
    actions.push('<button class="admin-btn small" onclick="resetQuota(' + u.id + ')">重置额度</button>');
    actions.push('<button class="admin-btn small" onclick="setUserModel(' + u.id + ')">设置模型</button>');
    actions.push('<button class="admin-btn small danger" onclick="deleteUser(' + u.id + ')">删除</button>');
  }
  return '<tr><td>' + u.id + '</td><td>' + esc(u.username) + '</td><td>' + role + '</td><td>' + status + '</td>'
    + '<td>' + esc(quota) + '</td><td>' + esc(u.llm_model || '—') + '</td>'
    + '<td class="actions">' + (actions.join('') || '—') + '</td></tr>';
}

function applyUserFilter() {
  state.users.q = $('user-q').value.trim();
  state.users.status = $('user-status').value;
  state.users.page = 1;
  renderUsers();
}
function usersPage(delta) {
  state.users.page = Math.max(1, state.users.page + delta);
  renderUsers();
}
function userById(id) { return state.users.list.find((x) => x.id === id); }

async function approveUser(id) {
  try { await api('/api/admin/approve/' + id, { method: 'POST' }); toast('已通过审核'); renderUsers(); }
  catch (e) { toast(e.message, true); }
}
async function rejectUser(id) {
  try { await api('/api/admin/reject/' + id, { method: 'POST' }); toast('已驳回'); renderUsers(); }
  catch (e) { toast(e.message, true); }
}
function revokeUser(id) {
  const u = userById(id);
  confirmAction('撤销权限', '确定撤销用户「' + (u ? u.username : id) + '」的使用权限？', '确定撤销', async () => {
    try { await api('/api/admin/revoke/' + id, { method: 'POST' }); toast('已撤销'); renderUsers(); }
    catch (e) { toast(e.message, true); }
  });
}
function deleteUser(id) {
  const u = userById(id);
  confirmAction('删除用户', '确定删除用户「' + (u ? u.username : id) + '」？该操作不可恢复。', '确定删除', async () => {
    try { await api('/api/admin/delete-user/' + id, { method: 'POST' }); toast('已删除'); renderUsers(); }
    catch (e) { toast(e.message, true); }
  });
}
function resetQuota(id) {
  const u = userById(id);
  confirmAction('重置额度', '确定将用户「' + (u ? u.username : id) + '」的免费额度重置为 0 次已用？', '确定重置', async () => {
    try { await api('/api/admin/reset-quota/' + id, { method: 'POST' }); toast('已重置额度'); renderUsers(); }
    catch (e) { toast(e.message, true); }
  });
}
async function setUserModel(id) {
  const u = userById(id);
  openAdminModal('修改用户模型', '<p>用户：' + esc(u ? u.username : id) + '</p>'
    + '<label class="admin-field">模型标识<input id="user-model-value" value="' + esc(u ? u.llm_model : '') + '" placeholder="deepseek-flash；留空使用全局默认"></label>'
    + '<p class="admin-note">模型需属于共享服务供应商。未授权账号仍需先通过审核，个人 API 账号使用自己的密钥。</p>'
    + '<button class="admin-btn primary" onclick="confirmUserModel(' + id + ')">下一步确认</button>');
}

function confirmUserModel(id) {
  const model = $('user-model-value').value.trim();
  confirmAction('确认修改模型', '确定将该用户的模型改为「' + (model || '全局默认') + '」？', '确认修改', async () => {
    try { await api('/api/admin/set-model/' + id, { method: 'POST', body: JSON.stringify({ llm_model: model }) }); toast('已更新模型'); renderUsers(); }
    catch (e) { toast(e.message, true); }
  });
}

function openTestUserForm() {
  openAdminModal('新建普通测试账号', '<p class="admin-note">不限应用内次数，没有管理员权限。不要在公开材料中放入真实密码。</p>'
    + '<label class="admin-field">用户名<input id="test-user-name" minlength="3" maxlength="80"></label>'
    + '<label class="admin-field">密码（至少12位）<input id="test-user-password" type="password" autocomplete="new-password"></label>'
    + '<button class="admin-btn primary" onclick="createTestUser()">创建测试账号</button>');
}

async function createTestUser() {
  const username = $('test-user-name').value.trim();
  const password = $('test-user-password').value;
  if (username.length < 3 || password.length < 12) return toast('用户名至少3位，密码至少12位', true);
  try {
    await api('/api/admin/test-users', { method: 'POST', body: JSON.stringify({ username, password }) });
    closeAdminModal(); toast('测试账号已创建'); renderUsers();
  } catch (e) { toast(e.message, true); }
}

// ===== 内容审核 =====
async function renderReview() {
  const view = $('admin-view');
  const s = state.community;
  try {
    const params = new URLSearchParams({ q: s.q, status: s.status, page: String(s.page), per_page: '20' });
    const [pending, overview] = await Promise.all([
      api('/api/admin/review/queue?per_page=20&page=' + state.review.page),
      api('/api/community/moderation/overview?' + params),
    ]);
    const items = pending.items || [];
    const m = overview.metrics || {};
    const posts = overview.posts || [];
    view.innerHTML = ''
      + '<div class="admin-cards">'
      + metricCard((pending.pagination || {}).total || 0, '待审核内容')
      + metricCard(m.posts || 0, '帖子总数') + metricCard(m.published_posts || 0, '公开')
      + metricCard(m.hidden_posts || 0, '已隐藏') + metricCard(m.comments || 0, '回复数')
      + '</div>'
      + '<div class="admin-block-title">待审核队列</div>'
      + (items.length ? items.map(reviewCard).join('') : '<div class="admin-empty">暂无待审核内容</div>')
      + paginationHtml(pending.pagination || { page: 1, pages: 1, total: 0 }, 'reviewPage')
      + '<div class="admin-block-title">全部社区内容</div>'
      + '<div class="admin-toolbar">'
      + '<input type="search" id="community-q" value="' + esc(s.q) + '" placeholder="搜索标题/正文/账号">'
      + '<select id="community-status">'
      + ['all', 'published', 'hidden', 'deleted'].map((v) => '<option value="' + v + '"' + (s.status === v ? ' selected' : '') + '>' + ({ all: '全部', published: '公开', hidden: '已隐藏', deleted: '已删除' }[v]) + '</option>').join('')
      + '</select>'
      + '<button class="admin-btn" onclick="applyCommunityFilter()">查询</button>'
      + '</div>'
      + '<div class="admin-table-wrap"><table class="admin-table"><thead><tr>'
      + '<th>ID</th><th>标题</th><th>作者</th><th>状态</th><th>互动</th><th>时间</th><th>操作</th>'
      + '</tr></thead><tbody>'
      + (posts.length ? posts.map(postRow).join('') : '<tr><td colspan="7" class="admin-empty">无内容</td></tr>')
      + '</tbody></table></div>'
      + paginationHtml(overview.pagination || { page: 1, pages: 1, total: 0 }, 'communityPage');
    wireEnter('community-q', applyCommunityFilter);
  } catch (e) {
    view.innerHTML = errorBlock(e.message);
  }
}

function reviewPage(delta) {
  state.review.page = Math.max(1, state.review.page + delta);
  renderReview();
}

function reviewCard(it) {
  const body = it.exists
    ? '<pre>' + esc(it.body || '') + '</pre>'
    : '<div class="admin-empty">内容已不存在</div>';
  return '<div class="admin-report">'
    + '<div class="meta">' + severityBadge(it.severity)
    + '<span class="badge">' + esc(it.target_type === 'post' ? '帖子' : '回复') + ' #' + esc(it.target_id) + '</span>'
    + '<span>' + esc(it.created_at) + '</span></div>'
    + '<div class="meta"><span>标题：' + esc(it.title || '') + '</span><span>作者：' + esc(it.author || '—') + '</span></div>'
    + body
    + '<div class="admin-note">命中原因：' + esc(it.reason || '') + '</div>'
    + '<div class="admin-actions">'
    + '<button class="admin-btn small primary" onclick="reviewDecision(\'' + it.target_type + '\',' + it.target_id + ',\'approve\')">通过</button>'
    + '<button class="admin-btn small" onclick="reviewDecision(\'' + it.target_type + '\',' + it.target_id + ',\'reject\')">驳回</button>'
    + '<button class="admin-btn small danger" onclick="reviewDecision(\'' + it.target_type + '\',' + it.target_id + ',\'delete\')">删除</button>'
    + '</div></div>';
}

function reviewDecision(type, id, action) {
  const label = { approve: '通过', reject: '驳回', delete: '删除' }[action];
  const run = async () => {
    try {
      await api('/api/admin/review/' + type + '/' + id, { method: 'POST', body: JSON.stringify({ action }) });
      toast('已' + label);
      renderReview();
    } catch (e) { toast(e.message, true); }
  };
  if (action === 'approve') { run(); return; }
  confirmAction('审核操作', '确定要' + label + '该内容？', '确定' + label, run);
}

// ===== 举报处理 =====
async function renderReports() {
  const view = $('admin-view');
  try {
    const data = await api('/api/community/moderation/reports');
    const reports = data.reports || [];
    const rows = reports.length
      ? reports.map(reportRow).join('')
      : '<tr><td colspan="7" class="admin-empty">暂无举报</td></tr>';
    view.innerHTML = ''
      + '<div class="admin-table-wrap"><table class="admin-table"><thead><tr>'
      + '<th>ID</th><th>举报对象</th><th>理由</th><th>状态</th><th>处理人</th><th>处理时间</th><th>操作</th>'
      + '</tr></thead><tbody>' + rows + '</tbody></table></div>';
  } catch (e) {
    view.innerHTML = errorBlock(e.message);
  }
}

function reportRow(r) {
  const target = r.target || {};
  const sBadge = r.status === 'pending'
    ? '<span class="badge warn">待处理</span>'
    : '<span class="badge ok">' + esc(reportStatusLabel(r.status)) + '</span>';
  let actions = '—';
  if (r.status === 'pending') {
    const btns = ['<button class="admin-btn small" onclick="resolveReport(' + r.id + ',\'dismiss\')">驳回举报</button>'];
    if (['post', 'comment'].includes(r.target_type) && target.exists) {
      btns.push('<button class="admin-btn small" onclick="resolveReport(' + r.id + ',\'hide\')">隐藏内容</button>');
      btns.push('<button class="admin-btn small danger" onclick="resolveReport(' + r.id + ',\'delete\')">删除内容</button>');
    }
    actions = btns.join('');
  }
  return '<tr><td>' + r.id + '</td>'
    + '<td>' + esc(r.target_type) + ' #' + esc(r.target_id) + '<div class="admin-note">' + esc(target.summary || '') + '</div></td>'
    + '<td>' + esc(r.reason || '') + (r.detail ? '<div class="admin-note">' + esc(r.detail) + '</div>' : '') + '</td>'
    + '<td>' + sBadge + '</td>'
    + '<td>' + esc(r.resolved_by || '—') + '</td>'
    + '<td>' + esc(r.resolved_at || '—') + '</td>'
    + '<td class="actions">' + actions + '</td></tr>';
}

function postRow(p) {
  const counts = p.counts || {};
  const actions = '<button class="admin-btn small" onclick="openPostDetail(' + p.id + ')">详情</button>';
  const toggle = p.status === 'hidden'
    ? '<button class="admin-btn small" onclick="moderateContent(\'post\',' + p.id + ',\'restore\')">恢复</button>'
    : '<button class="admin-btn small" onclick="moderateContent(\'post\',' + p.id + ',\'hide\')">隐藏</button>';
  return '<tr><td>' + p.id + '</td>'
    + '<td>' + esc(p.title) + (p.is_anonymous ? '<div class="admin-note">匿名发布 · 真实账号仅管理员可见</div>' : '') + '</td>'
    + '<td>' + esc((p.author_account || {}).username || '—') + '</td>'
    + '<td>' + esc(statusLabel(p.status)) + '</td>'
    + '<td>' + (counts.views || 0) + ' 阅 / ' + (counts.likes || 0) + ' 赞 / ' + (counts.comments || 0) + ' 评</td>'
    + '<td>' + esc(p.created_at) + '</td>'
    + '<td class="actions">' + actions + toggle + '<button class="admin-btn small danger" onclick="moderateContent(\'post\',' + p.id + ',\'delete\')">删除</button></td></tr>';
}

function applyCommunityFilter() {
  const s = state.community;
  s.q = $('community-q').value.trim();
  s.status = $('community-status').value;
  s.page = 1;
  renderReview();
}
function communityPage(delta) {
  state.community.page = Math.max(1, state.community.page + delta);
  renderReview();
}
async function moderateContent(type, id, action) {
  try { await api('/api/community/moderation/content/' + type + '/' + id, { method: 'POST', body: JSON.stringify({ action }) }); toast('已处理'); renderReview(); }
  catch (e) { toast(e.message, true); }
}
async function resolveReport(reportId, action) {
  try { await api('/api/community/moderation/reports/' + reportId + '/resolve', { method: 'POST', body: JSON.stringify({ action }) }); toast('已处理'); renderReports(); }
  catch (e) { toast(e.message, true); }
}
async function openPostDetail(postId) {
  try {
    const data = await api('/api/community/moderation/posts/' + postId);
    const post = data.post || {};
    const comments = data.comments || [];
    const commentHtml = comments.length ? comments.map((c) => '<div class="admin-report">'
      + '<pre>' + esc(c.body) + '</pre>'
      + '<div class="meta"><span>' + esc((c.author_account || {}).username || '—') + '</span><span>' + esc(statusLabel(c.status)) + '</span></div>'
      + '<div class="admin-actions">'
      + '<button class="admin-btn small" onclick="moderateContent(\'comment\',' + c.id + ',\'hide\')">隐藏</button>'
      + '<button class="admin-btn small" onclick="moderateContent(\'comment\',' + c.id + ',\'restore\')">恢复</button>'
      + '<button class="admin-btn small danger" onclick="moderateContent(\'comment\',' + c.id + ',\'delete\')">删除</button>'
      + '</div></div>').join('') : '<div class="admin-empty">暂无回复</div>';
    openAdminModal('帖子详情', '<div class="admin-report"><pre>' + esc(post.body || '') + '</pre>'
      + '<div class="meta"><span>作者：' + esc((post.author_account || {}).username || '—') + '</span><span>状态：' + esc(statusLabel(post.status)) + '</span>' + (post.is_anonymous ? '<span>匿名发布</span>' : '') + '</div></div>'
      + '<div class="admin-block-title">回复（' + comments.length + '）</div>' + commentHtml);
  } catch (e) { toast(e.message, true); }
}

// ===== 案例库 =====
async function renderCases() {
  const view = $('admin-view');
  const s = state.cases;
  try {
    const params = new URLSearchParams({ q: s.q, status: s.status, verification_status: s.verification_status, legal_domain: s.legal_domain, source_type: s.source_type, page: String(s.page), per_page: '20' });
    const data = await api('/api/admin/cases?' + params);
    if (!s.filters) s.filters = data.filters;
    const f = s.filters || { domains: [], statuses: [], verification_statuses: [], source_types: [] };
    const cases = data.cases || [];
    view.innerHTML = ''
      + '<div class="admin-toolbar">'
      + '<input type="search" id="case-q" value="' + esc(s.q) + '" placeholder="搜索标题/案号/摘要">'
      + '<select id="case-domain"><option value="">全部领域</option>' + (f.domains || []).map((d) => '<option value="' + esc(d.value) + '"' + (s.legal_domain === d.value ? ' selected' : '') + '>' + esc(d.label) + '</option>').join('') + '</select>'
      + '<select id="case-status"><option value="">全部状态</option>' + (f.statuses || []).map((v) => '<option value="' + v + '"' + (s.status === v ? ' selected' : '') + '>' + statusLabel(v) + '</option>').join('') + '</select>'
      + '<select id="case-verify"><option value="">全部核验</option>' + (f.verification_statuses || []).map((v) => '<option value="' + v + '"' + (s.verification_status === v ? ' selected' : '') + '>' + verifyLabel(v) + '</option>').join('') + '</select>'
      + '<button class="admin-btn" onclick="applyCaseFilter()">查询</button>'
      + '<button class="admin-btn primary" onclick="openCaseForm()">新建案例</button>'
      + '</div>'
      + '<div class="admin-table-wrap"><table class="admin-table"><thead><tr>'
      + '<th>ID</th><th>标题</th><th>领域</th><th>状态</th><th>核验</th><th>来源</th><th>操作</th>'
      + '</tr></thead><tbody>'
      + (cases.length ? cases.map(caseRow).join('') : '<tr><td colspan="7" class="admin-empty">暂无案例</td></tr>')
      + '</tbody></table></div>'
      + paginationHtml(data.pagination || { page: 1, pages: 1, total: 0 }, 'casesPage');
    wireEnter('case-q', applyCaseFilter);
  } catch (e) {
    view.innerHTML = errorBlock(e.message);
  }
}

function caseRow(c) {
  const toggle = c.status === 'published'
    ? '<button class="admin-btn small" onclick="setCaseStatus(' + c.id + ',\'hidden\')">下架</button>'
    : '<button class="admin-btn small" onclick="setCaseStatus(' + c.id + ',\'published\')">上架</button>';
  return '<tr><td>' + c.id + '</td>'
    + '<td>' + esc(c.title) + '<div class="admin-note">' + esc(c.case_number || '') + '</div></td>'
    + '<td>' + esc(c.legal_domain_label || c.legal_domain) + '</td>'
    + '<td>' + esc(statusLabel(c.status)) + '</td>'
    + '<td>' + esc(verifyLabel(c.verification_status)) + '</td>'
    + '<td>' + esc(sourceTypeLabel(c.source_type)) + '</td>'
    + '<td class="actions">'
    + '<button class="admin-btn small" onclick="openCaseForm(' + c.id + ')">编辑</button>'
    + toggle
    + '<button class="admin-btn small danger" onclick="deleteCase(' + c.id + ')">删除</button>'
    + '</td></tr>';
}

function applyCaseFilter() {
  const s = state.cases;
  s.q = $('case-q').value.trim();
  s.legal_domain = $('case-domain').value;
  s.status = $('case-status').value;
  s.verification_status = $('case-verify').value;
  s.page = 1;
  renderCases();
}
function casesPage(delta) {
  state.cases.page = Math.max(1, state.cases.page + delta);
  renderCases();
}
async function setCaseStatus(id, status) {
  try { await api('/api/admin/cases/' + id, { method: 'PUT', body: JSON.stringify({ status }) }); toast('已更新'); renderCases(); }
  catch (e) { toast(e.message, true); }
}
function deleteCase(id) {
  confirmAction('删除案例', '确定删除该案例？该操作不可恢复。', '确定删除', async () => {
    try { await api('/api/admin/cases/' + id, { method: 'DELETE' }); toast('已删除'); renderCases(); }
    catch (e) { toast(e.message, true); }
  });
}

function textField(k, label, value, full) {
  return '<label class="admin-field ' + (full ? 'full' : '') + '">' + esc(label) + '<input id="f-' + k + '" value="' + esc(value) + '"></label>';
}
function textAreaField(k, label, value, full) {
  return '<label class="admin-field ' + (full ? 'full' : '') + '">' + esc(label) + '<textarea id="f-' + k + '">' + esc(value) + '</textarea></label>';
}
function selectField(k, label, options, selected) {
  const opts = options.map((o) => (typeof o === 'string' ? { value: o, label: o } : o));
  return '<label class="admin-field">' + esc(label) + '<select id="f-' + k + '">'
    + opts.map((o) => '<option value="' + esc(o.value) + '"' + (String(o.value) === String(selected) ? ' selected' : '') + '>' + esc(o.label) + '</option>').join('')
    + '</select></label>';
}

async function openCaseForm(id) {
  const s = state.cases;
  let c = {};
  if (id) {
    try { c = (await api('/api/admin/cases/' + id)).case; }
    catch (e) { toast(e.message, true); return; }
  }
  s.editingId = id || null;
  const f = s.filters || { domains: [], categories: [], statuses: ['draft', 'published', 'hidden'], verification_statuses: ['pending', 'verified', 'stale', 'rejected'], source_types: ['official_court', 'manual'] };
  const val = (k) => (c[k] == null ? '' : c[k]);
  const html = '<div class="admin-form">'
    + textField('title', '标题 *', val('title'), true)
    + textField('case_number', '案号', val('case_number'))
    + textField('court_name', '法院', val('court_name'))
    + selectField('case_type', '案件类型', ['民事', '刑事', '行政', '执行', '其他'], c.case_type || '民事')
    + textField('cause', '案由', val('cause'))
    + selectField('legal_domain', '法律领域', (f.domains || []).map((d) => ({ value: d.value, label: d.label })), c.legal_domain || '')
    + selectField('category_slug', '分类', [{ value: '', label: '（自动推断）' }].concat((f.categories || []).map((x) => ({ value: x.slug, label: x.name }))), c.category_slug || '')
    + '<label class="admin-field">裁判日期<input id="f-decision_date" type="date" value="' + esc(val('decision_date')) + '"></label>'
    + textField('source_publisher', '来源发布方 *', val('source_publisher'))
    + selectField('source_type', '来源类型', (f.source_types || []).map((v) => ({ value: v, label: sourceTypeLabel(v) })), c.source_type || 'official_court')
    + textField('source_url', '来源链接 *', val('source_url'), true)
    + selectField('status', '状态', (f.statuses || []).map((v) => ({ value: v, label: statusLabel(v) })), c.status || 'published')
    + selectField('verification_status', '核验状态', (f.verification_statuses || []).map((v) => ({ value: v, label: verifyLabel(v) })), c.verification_status || 'verified')
    + textField('keywords', '关键词（逗号分隔）', val('keywords'), true)
    + textAreaField('summary', '案情摘要 *', val('summary'), true)
    + textAreaField('dispute_focus', '争议焦点 *', val('dispute_focus'), true)
    + textAreaField('judgment_result', '裁判结果 *', val('judgment_result'), true)
    + textAreaField('judgment_reasoning', '裁判说理 *', val('judgment_reasoning'), true)
    + textAreaField('ai_plain_language', '白话解读 *', val('ai_plain_language'), true)
    + textAreaField('tags', '标签（逗号分隔）', (c.tags || []).join(','), true)
    + textAreaField('law_references', '法律依据（每行：法律名称|条款|说明）', (c.law_references || []).map((r) => [r.law_name, r.article, r.note].join('|')).join('\n'), true)
    + '</div>'
    + '<p id="case-form-error" class="admin-error"></p>'
    + '<div class="admin-actions"><button class="admin-btn primary" onclick="saveCase()">保存</button><button class="admin-btn" onclick="closeAdminModal()">取消</button></div>';
  openAdminModal(id ? '编辑案例' : '新建案例', html);
}

async function saveCase() {
  const id = state.cases.editingId;
  const g = (k) => { const el = $('f-' + k); return el ? el.value.trim() : ''; };
  const payload = {
    title: g('title'), case_number: g('case_number'), court_name: g('court_name'),
    case_type: g('case_type'), cause: g('cause'), legal_domain: g('legal_domain'),
    category_slug: g('category_slug'), decision_date: g('decision_date'),
    source_publisher: g('source_publisher'), source_type: g('source_type'),
    source_url: g('source_url'), status: g('status'), verification_status: g('verification_status'),
    keywords: g('keywords'), summary: g('summary'), dispute_focus: g('dispute_focus'),
    judgment_result: g('judgment_result'), judgment_reasoning: g('judgment_reasoning'),
    ai_plain_language: g('ai_plain_language'),
    tags: g('tags').split(',').map((x) => x.trim()).filter(Boolean),
    law_references: g('law_references').split('\n').map((line) => {
      const parts = line.split('|');
      return { law_name: (parts[0] || '').trim(), article: (parts[1] || '').trim(), note: (parts[2] || '').trim() };
    }).filter((r) => r.law_name),
  };
  const errEl = $('case-form-error');
  try {
    if (id) await api('/api/admin/cases/' + id, { method: 'PUT', body: JSON.stringify(payload) });
    else await api('/api/admin/cases', { method: 'POST', body: JSON.stringify(payload) });
    closeAdminModal();
    toast('已保存');
    renderCases();
  } catch (e) {
    errEl.textContent = e.message;
  }
}

// ===== 会话审计 =====
async function renderAudit() {
  const view = $('admin-view');
  const s = state.audit;
  try {
    const params = new URLSearchParams({ q: s.q, page: String(s.page), per_page: '20' });
    const data = await api('/api/admin/audit/conversations?' + params);
    const rows = (data.conversations || []).length
      ? data.conversations.map((row) => '<tr>'
        + '<td>' + esc(row.title) + '<div class="admin-note">' + esc(String(row.id).slice(0, 8)) + '…</div></td>'
        + '<td>' + esc(row.username) + '</td><td>' + row.message_count + '</td><td>' + esc(row.updated_at) + '</td>'
        + '<td class="actions"><button class="admin-btn small" onclick="openConversation(\'' + row.id + '\')">查看</button></td></tr>').join('')
      : '<tr><td colspan="5" class="admin-empty">暂无会话</td></tr>';
    view.innerHTML = ''
      + '<div class="audit-banner">会话内容在入库前已脱敏，后台只可查看脱敏后的文本，不含原始个人标识。</div>'
      + '<div class="admin-toolbar"><input type="search" id="audit-q" value="' + esc(s.q) + '" placeholder="搜索标题或账号"><button class="admin-btn" onclick="applyAuditFilter()">查询</button></div>'
      + '<div class="admin-table-wrap"><table class="admin-table"><thead><tr><th>会话标题</th><th>用户</th><th>消息数</th><th>更新时间</th><th>操作</th></tr></thead><tbody>' + rows + '</tbody></table></div>'
      + paginationHtml(data.pagination || { page: 1, pages: 1, total: 0 }, 'auditPage');
    wireEnter('audit-q', applyAuditFilter);
  } catch (e) {
    view.innerHTML = errorBlock(e.message);
  }
}

function applyAuditFilter() {
  state.audit.q = $('audit-q').value.trim();
  state.audit.page = 1;
  renderAudit();
}
function auditPage(delta) {
  state.audit.page = Math.max(1, state.audit.page + delta);
  renderAudit();
}
async function openConversation(id) {
  try {
    const data = await api('/api/admin/audit/conversations/' + id);
    const convo = data.conversation || {};
    const messages = data.messages || [];
    const body = messages.length ? messages.map((m) => '<div class="audit-msg ' + (m.role === 'user' ? 'user' : 'assistant') + '">'
      + '<div class="role">' + (m.role === 'user' ? '用户' : '明鉴') + ' · ' + esc(m.created_at) + '</div>'
      + '<div class="content">' + esc(m.content) + '</div></div>').join('') : '<div class="admin-empty">无消息</div>';
    openAdminModal('会话详情 · ' + convo.username, '<div class="audit-banner">' + esc(data.note || '内容为脱敏后的结果。') + '</div>'
      + '<div class="admin-note" style="margin:10px 0">标题：' + esc(convo.title || '') + ' · 创建：' + esc(convo.created_at || '') + '</div>' + body);
  } catch (e) { toast(e.message, true); }
}

// ===== 操作日志 =====
async function renderLogs() {
  const view = $('admin-view');
  const s = state.logs;
  try {
    const params = new URLSearchParams({ q: s.q, action: s.action, page: String(s.page), per_page: '30' });
    const data = await api('/api/admin/logs?' + params);
    const logs = data.logs || [];
    const rows = logs.length
      ? logs.map((row) => '<tr>'
        + '<td>' + esc(row.created_at) + '</td>'
        + '<td>' + esc(row.actor_username) + '</td>'
        + '<td>' + esc(ACTION_LABELS[row.action] || row.action) + '<div class="admin-note">' + esc(row.action) + '</div></td>'
        + '<td>' + esc(row.target_type) + (row.target_id ? ' #' + esc(row.target_id) : '') + '</td>'
        + '<td>' + esc(row.detail || '—') + '</td>'
        + '<td>' + esc(row.ip || '—') + '</td></tr>').join('')
      : '<tr><td colspan="6" class="admin-empty">暂无操作记录</td></tr>';
    view.innerHTML = ''
      + '<div class="admin-toolbar">'
      + '<input type="search" id="log-q" value="' + esc(s.q) + '" placeholder="搜索操作人/动作/详情">'
      + '<button class="admin-btn" onclick="applyLogFilter()">查询</button>'
      + '</div>'
      + '<div class="admin-table-wrap"><table class="admin-table"><thead><tr>'
      + '<th>时间</th><th>操作人</th><th>动作</th><th>对象</th><th>详情</th><th>IP</th>'
      + '</tr></thead><tbody>' + rows + '</tbody></table></div>'
      + paginationHtml(data.pagination || { page: 1, pages: 1, total: 0 }, 'logsPage');
    wireEnter('log-q', applyLogFilter);
  } catch (e) {
    view.innerHTML = errorBlock(e.message);
  }
}

function applyLogFilter() {
  state.logs.q = $('log-q').value.trim();
  state.logs.page = 1;
  renderLogs();
}
function logsPage(delta) {
  state.logs.page = Math.max(1, state.logs.page + delta);
  renderLogs();
}

// ===== 系统设置 =====
async function renderSystem() {
  const view = $('admin-view');
  try {
    const [system, config, words] = await Promise.all([
      api('/api/admin/system'), api('/api/admin/model-config'), api('/api/admin/banned-words'),
    ]);
    const comp = system.components || {};
    state.bw.list = words.words || [];
    view.innerHTML = ''
      + '<div class="admin-cards">'
      + metricCard(system.version, '应用版本')
      + metricCard(system.demo_mode ? '演示模式' : '正式模式', '当前模式')
      + metricCard(comp.database ? '正常' : '异常', '数据库')
      + metricCard(comp.ocr ? '可用' : '不可用', 'OCR')
      + '</div>'
      + '<div class="admin-block-title">全局模型配置（对所有用户生效）</div>'
      + '<div class="admin-form">'
      + '<label class="admin-field">API Key<input id="cfg-key" type="password" placeholder="' + (config.has_api_key ? '已配置，留空则不变' : 'sk-...') + '"></label>'
      + '<label class="admin-field">Base URL<input id="cfg-url" value="' + esc(config.base_url || '') + '"></label>'
      + '<label class="admin-field">模型<input id="cfg-model" value="' + esc(config.model || '') + '"></label>'
      + '</div>'
      + '<div class="admin-actions"><button class="admin-btn primary" onclick="saveSystemConfig()">保存配置</button><button class="admin-btn" onclick="testSystemConfig()">测试连接</button></div>'
      + '<p id="cfg-msg" class="admin-note"></p>'
      + '<div class="admin-block-title">违禁词库（高危=直接拒绝发布 / 中危=转人工审核 / 低危=提示但放行）</div>'
      + '<div class="admin-toolbar">'
      + '<input id="bw-word" placeholder="违禁词">'
      + '<select id="bw-severity"><option value="high">高危</option><option value="medium" selected>中危</option><option value="low">低危</option></select>'
      + '<input id="bw-category" placeholder="分类（可选）">'
      + '<button class="admin-btn primary" onclick="addBannedWord()">添加</button>'
      + '</div>'
      + bwTable(state.bw.list)
      + '<div class="admin-block-title">管理员本人账号（与普通用户分开）</div>'
      + '<div class="admin-form">'
      + '<label class="admin-field">用户名<input id="profile-name" value="' + esc(state.user.username) + '"></label>'
      + '<label class="admin-field">当前密码<input id="profile-current" type="password" autocomplete="current-password"></label>'
      + '<label class="admin-field">新密码（至少12位，留空不变）<input id="profile-new" type="password" autocomplete="new-password"></label>'
      + '<label class="admin-field">确认新密码<input id="profile-confirm" type="password" autocomplete="new-password"></label>'
      + '</div><button class="admin-btn primary" onclick="saveAdminProfile()">保存本人账号</button>';
  } catch (e) {
    view.innerHTML = errorBlock(e.message);
  }
}

function bwTable(words) {
  const rows = words.length ? words.map((w) => '<tr>'
    + '<td>' + esc(w.word) + '</td>'
    + '<td>' + severityBadge(w.severity) + '</td>'
    + '<td>' + esc(w.category || '—') + '</td>'
    + '<td>' + (w.is_active ? '<span class="badge ok">启用</span>' : '<span class="badge">停用</span>') + '</td>'
    + '<td class="actions">'
    + '<button class="admin-btn small" onclick="cycleSeverity(' + w.id + ')">改等级</button>'
    + '<button class="admin-btn small" onclick="toggleBannedWord(' + w.id + ',' + (!w.is_active) + ')">' + (w.is_active ? '停用' : '启用') + '</button>'
    + '<button class="admin-btn small danger" onclick="deleteBannedWord(' + w.id + ')">删除</button>'
    + '</td></tr>').join('') : '<tr><td colspan="5" class="admin-empty">暂无违禁词</td></tr>';
  return '<div class="admin-table-wrap"><table class="admin-table"><thead><tr>'
    + '<th>违禁词</th><th>等级</th><th>分类</th><th>状态</th><th>操作</th>'
    + '</tr></thead><tbody>' + rows + '</tbody></table></div>';
}

function bwById(id) { return state.bw.list.find((x) => x.id === id); }

async function addBannedWord() {
  const word = $('bw-word').value.trim();
  const severity = $('bw-severity').value;
  const category = $('bw-category').value.trim();
  if (!word) { toast('请输入违禁词', true); return; }
  try {
    await api('/api/admin/banned-words', { method: 'POST', body: JSON.stringify({ word, severity, category }) });
    toast('已添加');
    renderSystem();
  } catch (e) { toast(e.message, true); }
}

async function cycleSeverity(id) {
  const w = bwById(id);
  if (!w) return;
  const order = ['high', 'medium', 'low'];
  const next = order[(order.indexOf(w.severity) + 1) % order.length];
  try {
    await api('/api/admin/banned-words/' + id, { method: 'PUT', body: JSON.stringify({ severity: next }) });
    toast('已改为' + severityLabel(next));
    renderSystem();
  } catch (e) { toast(e.message, true); }
}

async function toggleBannedWord(id, active) {
  try {
    await api('/api/admin/banned-words/' + id, { method: 'PUT', body: JSON.stringify({ is_active: active }) });
    toast(active ? '已启用' : '已停用');
    renderSystem();
  } catch (e) { toast(e.message, true); }
}

function deleteBannedWord(id) {
  const w = bwById(id);
  confirmAction('删除违禁词', '确定删除违禁词「' + (w ? w.word : id) + '」？', '确定删除', async () => {
    try {
      await api('/api/admin/banned-words/' + id, { method: 'DELETE' });
      toast('已删除');
      renderSystem();
    } catch (e) { toast(e.message, true); }
  });
}

async function saveSystemConfig() {
  try {
    await api('/api/admin/model-config', { method: 'POST', body: JSON.stringify({ api_key: $('cfg-key').value.trim(), base_url: $('cfg-url').value.trim(), model: $('cfg-model').value.trim() }) });
    $('cfg-key').value = '';
    $('cfg-msg').textContent = '配置已保存';
    toast('已保存');
  } catch (e) { if ($('cfg-msg')) $('cfg-msg').textContent = e.message; toast(e.message, true); }
}

async function testSystemConfig() {
  const msg = $('cfg-msg');
  msg.textContent = '测试中…';
  try {
    const data = await api('/api/admin/model-config/test', { method: 'POST', body: JSON.stringify({ api_key: $('cfg-key').value.trim(), base_url: $('cfg-url').value.trim(), model: $('cfg-model').value.trim() }) });
    msg.textContent = (data.status === 'ok' ? '✓ ' : '✗ ') + (data.message || data.error || '未知结果');
  } catch (e) { msg.textContent = '网络错误：' + e.message; }
}

async function saveAdminProfile() {
  const username = $('profile-name').value.trim();
  const current_password = $('profile-current').value;
  const password = $('profile-new').value;
  if (!current_password || password !== $('profile-confirm').value || (password && password.length < 12)) {
    return toast('请填写当前密码，新密码至少12位且两次一致', true);
  }
  try {
    const data = await api('/api/admin/profile', { method: 'POST', body: JSON.stringify({ username, current_password, password }) });
    state.user = data.user;
    $('admin-who').textContent = data.user.username;
    ['profile-current', 'profile-new', 'profile-confirm'].forEach(id => { if ($(id)) $(id).value = ''; });
    toast('本人账号已更新，重启不会恢复旧密码');
  } catch (e) { toast(e.message, true); }
}

// ===== 启动 =====
(async function bootstrap() {
  document.querySelectorAll('#admin-nav button').forEach((b) => b.addEventListener('click', () => switchSection(b.dataset.section)));
  try {
    const data = await api('/api/auth/status');
    if (data.authenticated && data.user && data.user.is_admin) { enterConsole(data.user); return; }
  } catch (e) { /* 未登录 */ }
  $('admin-login').classList.remove('hidden');
})();
