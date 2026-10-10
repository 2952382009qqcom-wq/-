const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.join(__dirname, '..');
const source = fs.readFileSync(path.join(root, 'static/js/admin.js'), 'utf8');
const html = fs.readFileSync(path.join(root, 'templates/admin.html'), 'utf8');
const main = fs.readFileSync(path.join(root, 'static/js/main.js'), 'utf8');

function setup(handler = () => ({})) {
  const elements = new Map();
  const calls = [];
  function el(id) {
    if (!elements.has(id)) {
      const classes = new Set();
      elements.set(id, { id, value:'', textContent:'', innerHTML:'', style:{}, dataset:{},
        classList:{add:x=>classes.add(x), remove:x=>classes.delete(x),
          contains:x=>classes.has(x), toggle:(x,on)=>on?classes.add(x):classes.delete(x)},
        addEventListener(){}, appendChild(){}, focus(){} });
    }
    return elements.get(id);
  }
  const context = vm.createContext({
    document:{getElementById:el, querySelectorAll:()=>[], createElement:()=>el('admin-toast'), body:{appendChild(){}}},
    fetch:async(url,options={})=>{
      calls.push({url,options});
      const data = await handler(url,options);
      return {ok:!(data.statusCode>=400), status:data.statusCode||200, json:async()=>data.body||data};
    },
    URLSearchParams, setTimeout:()=>1, clearTimeout(){},
  });
  vm.runInContext(source, context);
  return {el,calls,run:s=>vm.runInContext(s,context)};
}
const flush = () => new Promise(resolve => setImmediate(resolve));

test('independent admin form prevents default submission and contains all teacher sections', () => {
  assert.match(html,/event.preventDefault\(\); adminLogin\(\); return false/);
  for (const name of ['dashboard','users','review','reports','logs','system']) {
    assert.ok(html.includes('data-section="'+name+'"'));
  }
  assert.doesNotMatch(main,/toggleAdminPanel|id="admin-panel"/);
  assert.match(main,/window.location.replace\("\/admin"\)/);
});

test('ordinary session cannot load management and is not silently logged out', async () => {
  const app=setup(()=>({authenticated:true,user:{is_admin:false}}));
  await flush();
  assert.ok(!app.calls.some(x=>x.url==='/api/auth/logout'));
  await assert.rejects(app.run("api('/api/admin/users')"),/管理员/);
  assert.ok(!app.calls.some(x=>x.url==='/api/admin/users'));
});

test('admin login uses dedicated endpoint and clears password', async () => {
  const app=setup(url=>url==='/api/admin/login'?{user:{is_admin:true,username:'manager'}}:{});
  app.el('admin-login-username').value='manager';
  app.el('admin-login-password').value='offline-password';
  await app.run('adminLogin()');
  assert.ok(app.calls.some(x=>x.url==='/api/admin/login'));
  assert.equal(app.el('admin-login-password').value,'');
  assert.equal(app.run('state.user.username'),'manager');
});

test('expired session clears sensitive DOM and pending confirmation', async () => {
  const app=setup(()=>({statusCode:401,body:{error:'expired'}}));
  await flush();
  app.run("state.user={is_admin:true}; _confirmCb=()=>{}");
  app.el('admin-view').innerHTML='sensitive content';
  app.el('admin-modal-content').innerHTML='private form';
  await assert.rejects(app.run("api('/api/admin/users')"));
  assert.equal(app.run('state.user'),null);
  assert.equal(app.run('_confirmCb'),null);
  assert.equal(app.el('admin-view').innerHTML,'');
  assert.equal(app.el('admin-modal-content').innerHTML,'');
});

test('incorrect current password does not clear valid admin session', async () => {
  const app=setup(()=>({statusCode:401,body:{code:'CURRENT_PASSWORD_INCORRECT',error:'wrong'}}));
  await flush();
  app.run("state.user={is_admin:true}");
  await assert.rejects(app.run("api('/api/admin/profile',{method:'POST'})"));
  assert.equal(app.run('state.user.is_admin'),true);
});

test('system settings use admin endpoint, preserve blank key and clear entered key', async () => {
  const app=setup(()=>({status:'ok'}));
  await flush();
  app.run("state.user={is_admin:true}");
  app.el('cfg-key').value='';
  app.el('cfg-url').value='https://api.deepseek.com/v1';
  app.el('cfg-model').value='deepseek-flash';
  await app.run('saveSystemConfig()');
  const call=app.calls.find(x=>x.url==='/api/admin/model-config');
  assert.equal(JSON.parse(call.options.body).api_key,'');
  app.el('cfg-key').value='offline-secret-not-real';
  await app.run('saveSystemConfig()');
  assert.equal(app.el('cfg-key').value,'');
});

test('user quota correctly renders unlimited and content is escaped', () => {
  const app=setup();
  const row=app.run("userRow({id:2,username:'<script>bad</script>',is_admin:false,is_approved:true,free_api_remaining:null})");
  assert.ok(row.includes('不限应用次数'));
  assert.ok(!row.includes('null/'));
  assert.ok(!row.includes('<script>'));
});

test('reset quota and model change wait for second confirmation', async () => {
  const app=setup();
  await flush();
  app.run("state.user={is_admin:true}; state.users.list=[{id:2,username:'student',llm_model:'deepseek-flash'}]");
  app.run('resetQuota(2)');
  assert.ok(!app.calls.some(x=>x.url.includes('reset-quota')));
  assert.equal(app.run('typeof _confirmCb'),'function');
  app.run('setUserModel(2)');
  app.el('user-model-value').value='deepseek-flash';
  app.run('confirmUserModel(2)');
  assert.ok(!app.calls.some(x=>x.url.includes('set-model')));
});

test('review and reports include reason, handler, time, pagination and escaped bodies', () => {
  const app=setup();
  const card=app.run("reviewCard({exists:true,target_type:'post',target_id:'1',body:'<script>x</script>',reason:'命中中危',severity:'medium'})");
  assert.ok(card.includes('命中原因'));
  assert.ok(!card.includes('<script>'));
  const report=app.run("reportRow({id:1,target_type:'post',target_id:'1',status:'resolved',resolved_by:'teacher',resolved_at:'2026-10-10',target:{}})");
  assert.ok(report.includes('teacher'));
  assert.ok(report.includes('2026-10-10'));
  assert.match(source,/review\/queue\?per_page=20&page=/);
  assert.match(source,/pending.pagination/);
});
