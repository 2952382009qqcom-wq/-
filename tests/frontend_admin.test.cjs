const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const sourceRoot = path.join(__dirname, '..');
const indexHtml = fs.readFileSync(path.join(sourceRoot, 'templates/index.html'), 'utf8');
const adminHtml = fs.readFileSync(path.join(sourceRoot, 'templates/admin.html'), 'utf8');
const mainJs = fs.readFileSync(path.join(sourceRoot, 'static/js/main.js'), 'utf8');
const adminJs = fs.readFileSync(path.join(sourceRoot, 'static/js/admin.js'), 'utf8');

function setup(source = adminJs, html = adminHtml, handler = () => ({})) {
  const elements = new Map();
  const calls = [];
  const redirects = [];
  const readyCallbacks = [];
  class Element {
    constructor(id = '') {
      this.id = id;
      this.value = '';
      this.style = {};
      this.children = [];
      this._text = '';
      this.innerHTML = '';
      this.className = '';
      this.listeners = {};
      const classes = new Set();
      this.classList = {
        add: (...names) => names.forEach(name => classes.add(name)),
        remove: (...names) => names.forEach(name => classes.delete(name)),
        contains: name => classes.has(name),
        toggle: name => classes.has(name) ? classes.delete(name) : classes.add(name),
      };
    }
    get textContent() { return this._text + this.children.map(child => child.textContent).join(''); }
    set textContent(value) { this._text = String(value); this.children = []; }
    appendChild(child) { this.children.push(child); return child; }
    replaceChildren(...children) { this._text = ''; this.children = children; }
    addEventListener(name, callback) { this.listeners[name] = callback; }
    querySelectorAll() { return []; }
    reset() {
      const fields = {
        'admin-model-form': ['admin-model-key', 'admin-model-base-url', 'admin-model-name'],
        'admin-profile-form': ['admin-profile-username', 'admin-current-password', 'admin-new-password', 'admin-confirm-password'],
        'admin-test-user-form': ['test-user-username', 'test-user-password'],
      }[this.id] || [];
      fields.forEach(id => { elements.get(id).value = ''; });
    }
    focus() {}
  }
  for (const match of html.matchAll(/id="([^"]+)"/g)) elements.set(match[1], new Element(match[1]));
  if (elements.has('admin-user-filter')) elements.get('admin-user-filter').value = 'all';
  if (elements.has('admin-model-base-url')) elements.get('admin-model-base-url').value = 'https://api.deepseek.com/v1';
  if (elements.has('admin-model-name')) elements.get('admin-model-name').value = 'deepseek-flash';
  const context = vm.createContext({
    document: {
      getElementById: id => elements.get(id) || null,
      createElement: () => new Element(),
      addEventListener: (name, callback) => { if (name === 'DOMContentLoaded') readyCallbacks.push(callback); },
      querySelectorAll: () => [],
    },
    window: { addEventListener() {}, location: { replace: url => redirects.push(url) } },
    fetch: async (url, options = {}) => {
      calls.push({ url, options });
      const result = await handler(url, options);
      return { ok: (result.statusCode || 200) < 400, status: result.statusCode || 200, json: async () => result.data ?? result };
    },
    confirm: () => true, alert() {}, FormData, TextDecoder,
  });
  vm.runInContext(source, context);
  return { context, calls, redirects, readyCallbacks, element: id => elements.get(id), run: code => vm.runInContext(code, context) };
}

const admin = { id: 1, username: 'manager', is_admin: true, role: 'admin' };
const ordinary = { id: 2, username: 'student', is_admin: false, role: 'user', is_approved: true, ai_unlimited: true, free_api_remaining: null };
const preventEvent = { preventDefault() {} };

function adminResponses(url) {
  if (url === '/api/auth/status') return { authenticated: true, user: admin };
  if (url === '/api/admin/all-users') return { users: [ordinary, admin], administrators: [admin] };
  if (url === '/api/admin/metrics') return { users: { total: 1, quota_exhausted: 0, personal_api: 0 }, usage: { today: 3, last_7_days: 8 } };
  if (url === '/api/admin/model-config') return { has_api_key: true, base_url: 'https://api.deepseek.com/v1', model: 'deepseek-flash' };
  return { status: 'ok' };
}

test('ordinary template and script contain no embedded administrator panel or management requests', () => {
  assert.doesNotMatch(indexHtml, /admin-panel|admin-content|admin-overlay|toggleAdminPanel/);
  assert.doesNotMatch(mainJs, /\/api\/admin\//);
  assert.match(indexHtml, /href="\/admin"/);
  assert.match(indexHtml, /value="deepseek-flash">DeepSeek V4\.1 Flash/);
  assert.doesNotMatch(adminHtml, /main\.js|community\.js|chat\.js/);
  assert.doesNotMatch(adminJs, /localStorage|sessionStorage|console\.|innerHTML|["']\/api\/config/);
});

test('null quota and explicit unlimited state display unlimited rather than zero; personal API remains supported', () => {
  const app = setup(mainJs, indexHtml);
  for (const state of [{ free_api_remaining: null }, { ai_unlimited: true, free_api_remaining: 0 }, { quota_mode: 'unlimited' }, { remaining: null }]) {
    app.context.window._user = { username: 'student', ...state };
    app.run('updateQuotaHint()');
    assert.equal(app.element('free-quota-text').textContent, 'AI 不限次数');
    assert.equal(app.element('free-quota-text').classList.contains('quota-exhausted'), false);
  }
  app.context.window._user = { has_llm_api_key: true, free_api_remaining: 0 };
  app.run('updateQuotaHint()');
  assert.equal(app.element('free-quota-text').textContent, '个人 API 已启用');
  app.context.window._user = { free_api_remaining: 0, free_api_limit: 10 };
  app.run('updateQuotaHint()');
  assert.equal(app.element('free-quota-text').textContent, '免费额度 0/10');
  assert.equal(app.element('free-quota-text').classList.contains('quota-exhausted'), true);
});

test('administrator on ordinary page redirects without requesting user histories or touching removed DOM', () => {
  const app = setup(mainJs, indexHtml);
  app.context.person = admin;
  app.run('applyUserUI(person); updateStatusBadge(false)');
  assert.deepEqual(app.redirects, ['/admin']);
  assert.equal(app.calls.length, 0);
});

test('anonymous and ordinary sessions cannot load administrator data', async () => {
  for (const auth of [{ authenticated: false }, { authenticated: true, user: ordinary }]) {
    const app = setup(adminJs, adminHtml, () => auth);
    await app.run('initAdminPage()');
    assert.deepEqual(app.calls.map(call => call.url), ['/api/auth/status']);
    assert.equal(app.element('admin-dashboard').classList.contains('hidden'), true);
    assert.equal(app.element('admin-login-view').classList.contains('hidden'), false);
    await assert.rejects(app.run('adminRequest("/api/admin/all-users")'), /先登录管理员/);
    assert.equal(app.calls.length, 1);
  }
});

test('administrator loads its own API endpoints and separate user and administrator lists', async () => {
  const app = setup(adminJs, adminHtml, adminResponses);
  await app.run('initAdminPage()');
  assert.equal(app.element('admin-dashboard').classList.contains('hidden'), false);
  assert.equal(app.element('admin-identity').textContent, 'manager');
  assert.match(app.element('admin-users-list').textContent, /student.*AI 不限次数/);
  assert.doesNotMatch(app.element('admin-users-list').textContent, /manager/);
  assert.match(app.element('admin-administrators-list').textContent, /manager.*当前账号/);
  assert.equal(app.element('admin-model-key').value, '');
  assert.equal(app.element('admin-model-name').value, 'deepseek-flash');
  assert.deepEqual(app.calls.map(call => call.url).sort(), ['/api/admin/all-users', '/api/admin/metrics', '/api/admin/model-config', '/api/auth/status'].sort());
});

test('expired administrator session clears data and form secrets', async () => {
  let expired = false;
  const app = setup(adminJs, adminHtml, url => expired ? { statusCode: 403, data: { error: '无权限' } } : adminResponses(url));
  await app.run('initAdminPage()');
  app.element('admin-model-key').value = 'transient-provider-secret';
  app.element('admin-new-password').value = 'transient-account-password';
  expired = true;
  await assert.rejects(app.run('adminRequest("/api/admin/all-users")'), /无权限/);
  assert.equal(app.element('admin-dashboard').classList.contains('hidden'), true);
  assert.equal(app.element('admin-users-list').textContent, '');
  assert.equal(app.element('admin-administrators-list').textContent, '');
  assert.equal(app.element('admin-model-key').value, '');
  assert.equal(app.element('admin-new-password').value, '');
});

test('administrator profile enforces password length and submits only the current account change', async () => {
  const app = setup(adminJs, adminHtml, adminResponses);
  await app.run('initAdminPage()');
  app.context.event = preventEvent;
  app.element('admin-profile-username').value = 'renamed-manager';
  app.element('admin-current-password').value = 'old-password';
  app.element('admin-new-password').value = 'short';
  app.element('admin-confirm-password').value = 'short';
  const before = app.calls.length;
  await app.run('saveAdminProfile(event)');
  assert.equal(app.calls.length, before);
  assert.match(app.element('admin-profile-message').textContent, /至少 12/);
  app.element('admin-new-password').value = 'new-password-with-space ';
  app.element('admin-confirm-password').value = 'new-password-with-space ';
  await app.run('saveAdminProfile(event)');
  const request = app.calls.find(call => call.url === '/api/admin/profile');
  assert.deepEqual(JSON.parse(request.options.body), { current_password: 'old-password', username: 'renamed-manager', password: 'new-password-with-space ' });
  assert.equal(app.element('admin-current-password').value, '');
  assert.equal(app.element('admin-new-password').value, '');
  assert.equal(app.element('admin-identity').textContent, 'renamed-manager');
});

test('incorrect current password keeps the administrator session only for the explicit profile error code', async () => {
  const app = setup(adminJs, adminHtml, url => url === '/api/admin/profile' ? { statusCode: 401, data: { error: '当前密码错误', code: 'CURRENT_PASSWORD_INCORRECT' } } : adminResponses(url));
  await app.run('initAdminPage()');
  app.context.event = preventEvent;
  app.element('admin-current-password').value = 'incorrect-password';
  await app.run('saveAdminProfile(event)');
  assert.equal(app.element('admin-dashboard').classList.contains('hidden'), false);
  assert.equal(app.element('admin-identity').textContent, 'manager');
  assert.match(app.element('admin-profile-message').textContent, /当前密码错误/);
});

test('global config keeps existing secret when blank and sends new secret only to administrator config API', async () => {
  const app = setup(adminJs, adminHtml, adminResponses);
  await app.run('initAdminPage()');
  app.context.event = preventEvent;
  await app.run('saveAdminModel(event)');
  const first = app.calls.find(call => call.url === '/api/admin/model-config' && call.options.method === 'POST');
  assert.equal(Object.hasOwn(JSON.parse(first.options.body), 'api_key'), false);
  app.element('admin-model-key').value = 'test-secret-only-in-request';
  await app.run('saveAdminModel(event)');
  const saves = app.calls.filter(call => call.url === '/api/admin/model-config' && call.options.method === 'POST');
  assert.equal(JSON.parse(saves[1].options.body).api_key, 'test-secret-only-in-request');
  assert.equal(app.element('admin-model-key').value, '');
  assert.equal(app.calls.some(call => call.url === '/api/config'), false);
});

test('server messages redact the entered API key and user names are rendered as text', async () => {
  const unsafeName = '<img src=x onerror=alert(1)>';
  const app = setup(adminJs, adminHtml, url => url === '/api/admin/all-users' ? { users: [{ ...ordinary, username: unsafeName }], administrators: [admin] } : adminResponses(url));
  await app.run('initAdminPage()');
  const nameElement = app.element('admin-users-list').children[0].children[0].children[0];
  assert.equal(nameElement.textContent, unsafeName);
  assert.equal(nameElement.innerHTML, '');
  app.element('admin-model-key').value = 'sensitive-key-value';
  app.context.serverMessage = 'failed for sensitive-key-value';
  app.run('adminMessage("admin-model-message", serverMessage, "error")');
  assert.equal(app.element('admin-model-message').textContent, 'failed for [密钥已隐藏]');
});

test('test-user creation is manual and administrator login uses its independent endpoint', async () => {
  const app = setup(adminJs, adminHtml, url => url === '/api/admin/login' ? { status: 'ok', user: admin } : adminResponses(url));
  app.context.event = preventEvent;
  app.element('admin-login-username').value = 'manager';
  app.element('admin-login-password').value = 'login-secret ';
  await app.run('adminLogin(event)');
  const login = app.calls.find(call => call.url === '/api/admin/login');
  assert.equal(JSON.parse(login.options.body).password, 'login-secret ');
  assert.equal(app.element('admin-login-password').value, '');
  assert.equal(app.calls.some(call => call.url === '/api/admin/test-users'), false);
  app.element('test-user-username').value = 'manual-test-user';
  app.element('test-user-password').value = 'test-user-password';
  await app.run('createAdminTestUser(event)');
  assert.equal(app.calls.filter(call => call.url === '/api/admin/test-users').length, 1);
  assert.equal(app.element('test-user-password').value, '');
});
