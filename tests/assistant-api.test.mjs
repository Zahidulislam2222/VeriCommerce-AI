import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import ts from 'typescript';
import { Buffer } from 'node:buffer';
import { URL } from 'node:url';
import { setTimeout, clearTimeout } from 'node:timers';
const { Response, AbortController, DOMException } = globalThis;

// Execute the actual helper with browser boundaries replaced, without a new dependency.
const moduleUrl = (source) => `data:text/javascript;base64,${Buffer.from(source).toString('base64')}`;
const configSource = (await readFile(new URL('../src/config.ts', import.meta.url), 'utf8')).replaceAll('import.meta.env', '({})');
const configUrl = moduleUrl(ts.transpileModule(configSource, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ES2022 } }).outputText);
let source = await readFile(new URL('../src/core/api.ts', import.meta.url), 'utf8');
source = source.replace("'../config'", JSON.stringify(configUrl));
for (const name of ['core', 'phase-workspace']) {
  const data = JSON.parse(await readFile(new URL(`../src/data/${name}.json`, import.meta.url), 'utf8'));
  source = source.replace(`'../data/${name}.json'`, JSON.stringify(moduleUrl(`export default ${JSON.stringify(data)}`)));
}
const api = await import(moduleUrl(ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ES2022 } }).outputText));
const { appConfig } = await import(configUrl);
const answerPath = appConfig.core.paths.answers;
const reply = (data = {}, status = 200, workspace = 'workspace-a') => new Response(JSON.stringify(data), { status, headers: { 'X-Workspace-ID': workspace, 'Content-Type': 'application/json' } });
const browserTimers = { setTimeout, clearTimeout };
globalThis.window = browserTimers;

test('caller abort stops only its read and removes its bridge listener', async () => {
  api.setWorkspaceScope('workspace-a');
  const caller = new AbortController(); let added = 0; let removed = 0; let received;
  const add = caller.signal.addEventListener.bind(caller.signal); const remove = caller.signal.removeEventListener.bind(caller.signal);
  caller.signal.addEventListener = (...args) => { added += 1; return add(...args); };
  caller.signal.removeEventListener = (...args) => { removed += 1; return remove(...args); };
  globalThis.fetch = async (_path, options) => { received = options; return new Promise((_resolve, reject) => options.signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')), { once: true })); };
  const pending = api.request(answerPath, { method: 'POST', body: '{}', signal: caller.signal });
  caller.abort();
  await assert.rejects(pending, api.CoreRequestStopped);
  assert.equal(received.credentials, 'same-origin'); assert.equal(received.headers['X-Workspace-ID'], 'workspace-a');
  assert.equal(added, 1); assert.equal(removed, 1); assert.equal(received.signal.aborted, true);
});

test('already aborted caller remains a neutral stop even if fetch resolves late', async () => {
  const caller = new AbortController(); caller.abort(); let signal;
  globalThis.fetch = async (_path, options) => { signal = options.signal; return reply(); };
  await assert.rejects(api.request(answerPath, { signal: caller.signal }), api.CoreRequestStopped);
  assert.equal(signal.aborted, true);
});

test('own deadline is preserved and distinguished from a caller stop', async () => {
  let expire; let cleared = false; let observedMs;
  globalThis.window = { setTimeout: (callback, milliseconds) => { expire = callback; observedMs = milliseconds; return 7; }, clearTimeout: (id) => { cleared = id === 7; } };
  globalThis.fetch = async (_path, options) => new Promise((_resolve, reject) => options.signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')), { once: true }));
  const pending = api.request(answerPath); expire();
  await assert.rejects(pending, (error) => error instanceof api.CoreError && !(error instanceof api.CoreRequestStopped));
  assert.equal(observedMs, appConfig.core.requestTimeoutSeconds * 1000); assert.equal(cleared, true);
  globalThis.window = browserTimers;
});

test('scope and authorization failures are never converted to success or retried', async () => {
  api.setWorkspaceScope('workspace-a'); let calls = 0;
  globalThis.fetch = async () => { calls += 1; api.setWorkspaceScope('workspace-b'); return reply(); };
  await assert.rejects(api.request(answerPath), api.WorkspaceScopeError); assert.equal(calls, 1);
  api.setWorkspaceScope('workspace-a'); calls = 0;
  globalThis.fetch = async () => { calls += 1; return reply({ detail: 'Access denied' }, 403); };
  await assert.rejects(api.request(answerPath), (error) => error instanceof api.CoreError && error.status === 403);
  assert.equal(calls, 1);
});

test('guarded session bootstrap does not POST after cancellation during its GET', async () => {
  let current = true; let calls = 0;
  globalThis.fetch = async () => { calls += 1; current = false; return reply({ detail: 'No session' }, 401); };
  await assert.rejects(api.ensureSession(() => { if (!current) throw new api.CoreRequestStopped(); }), api.CoreRequestStopped);
  assert.equal(calls, 1);
});

test('normal concurrent session bootstrap retains one GET and one fallback POST', async () => {
  const methods = [];
  globalThis.fetch = async (_path, options) => { methods.push(options.method || 'GET'); return methods.length === 1 ? reply({ detail: 'No session' }, 401) : reply({ tenant_id: 'workspace-a' }); };
  const [first, second] = await Promise.all([api.ensureSession(), api.ensureSession()]);
  assert.deepEqual(first, { tenant_id: 'workspace-a' }); assert.deepEqual(second, first);
  assert.deepEqual(methods, ['GET', 'POST']);
});
