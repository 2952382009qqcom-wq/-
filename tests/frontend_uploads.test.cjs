const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function setup() {
  const elements = new Map();
  function element(id) {
    if (!elements.has(id)) elements.set(id, {
      value: '', textContent: '', innerHTML: '', files: [], style: {}, focus() {},
      classList: { toggle() {}, add() {}, remove() {} },
    });
    return elements.get(id);
  }
  const alerts = [];
  const revoked = [];
  const context = vm.createContext({
    document: { addEventListener() {}, getElementById: element, querySelectorAll: () => [] },
    URL: { createObjectURL: file => `blob:${file.name}`, revokeObjectURL: url => revoked.push(url) },
    window: {}, alert: message => alerts.push(message), FormData, TextDecoder,
  });
  vm.runInContext(fs.readFileSync(path.join(__dirname, '../static/js/main.js'), 'utf8'), context);
  context.escapeHtml = value => String(value).replaceAll('<', '&lt;').replaceAll('"', '&quot;');
  return { context, element, alerts, revoked, run: source => vm.runInContext(source, context) };
}

function photo(name, size = 20, lastModified = 1) {
  return { name, size, lastModified, type: 'image/png' };
}

test('album multi-select and repeated camera captures append; empty/cancel keeps attachments', () => {
  const { context, run, element } = setup();
  context.album = { files: [photo('1.png'), photo('2.png')], value: 'selected' };
  run('onAgentFileSelected(album)');
  assert.equal(context.album.value, '');
  context.camera = { files: [photo('3.png')], value: 'captured' };
  run('onAgentFileSelected(camera, true)');
  run('onAgentFileSelected({files: [], value: ""}, true)');
  assert.equal(run('legalAgentState.files.map(file => file.name).join(",")'), '1.png,2.png,3.png');
  assert.match(element('agent-attachment-name').textContent, /3 个附件/);
  assert.match(element('agent-attachment-list').innerHTML, /3.png/);
});

test('sorting/deleting affect agent and professional tool queues without leaking object URLs', () => {
  const { context, run, revoked } = setup();
  context.photos = [photo('1.png'), photo('2.png'), photo('3.png')];
  run('updateUploadSelection("review", photos); moveUploadFile("review", 2, -1); removeUploadFile("review", 0)');
  assert.equal(run('getSelectedUploadFiles("review").map(file => file.name).join(",")'), '3.png,2.png');
  assert.equal(run('getSelectedUploadFiles("analyze").length'), 0);
  assert.ok(revoked.includes('blob:1.png'));
});

test('duplicate files are deduplicated, but different captures with the same name are retained', () => {
  const { context, run } = setup();
  context.first = [photo('camera.png')];
  context.second = [photo('camera.png'), photo('camera.png', 20, 2)];
  assert.equal(run('mergeUploadFiles(first, second).length'), 2);
});

test('count/total-size/unsupported limits reject the new selection without losing existing items', () => {
  const { context, run, alerts } = setup();
  context.existing = [photo('1.png')];
  context.overCount = Array.from({ length: 10 }, (_, i) => photo(`extra${i}.png`));
  assert.equal(run('mergeUploadFiles(existing, overCount) === existing'), true);
  context.overSize = [photo('large.png', 15 * 1024 * 1024)];
  assert.equal(run('mergeUploadFiles(existing, overSize) === existing'), true);
  context.bad = [photo('bad.exe')];
  assert.equal(run('mergeUploadFiles(existing, bad) === existing'), true);
  assert.equal(alerts.length, 3);
});

test('attachments cannot be modified while agent submission is in progress', () => {
  const { context, run } = setup();
  context.album = { files: [photo('1.png'), photo('2.png')] };
  run('onAgentFileSelected(album); legalAgentState.sending = true; removeUploadFile("agent",0); moveUploadFile("agent",0,1); clearAgentAttachment()');
  assert.equal(run('legalAgentState.files.map(file => file.name).join(",")'), '1.png,2.png');
});

test('agent submission sends every selected file in order and clears only on success', async () => {
  const { context, run, element } = setup();
  context.photos = [new File(['one'], '1.txt'), new File(['two'], '2.txt')];
  context.appendAgentMessage = () => ({});
  context.appendAgentPending = () => ({});
  context.finishAgentMessage = () => {};
  context.syncFreeQuotaFromResponse = () => {};
  context.setAgentAction = () => {};
  context.updateQuotaHint = () => {};
  context.loadAgentConversations = () => {};
  element('agent-input').value = '分析所有材料';
  let sent;
  context.fetch = async (_url, options) => {
    sent = options.body;
    return new Response('data: {"done":true,"result":{"answer":"已分析"}}\n\n', { headers: { 'content-type': 'text/event-stream' } });
  };
  run('setSelectedUploadFiles("agent", photos)');
  await run('submitLegalAgent()');
  assert.deepEqual(sent.getAll('file').map(file => file.name), ['1.txt', '2.txt']);
  assert.equal(run('legalAgentState.files.length'), 0);
  run('setSelectedUploadFiles("agent", photos)');
  context.fetch = async () => new Response('{"error":"测试失败"}', { status: 422, headers: { 'content-type': 'application/json' } });
  await run('submitLegalAgent()');
  assert.equal(run('legalAgentState.files.length'), 2);
});
