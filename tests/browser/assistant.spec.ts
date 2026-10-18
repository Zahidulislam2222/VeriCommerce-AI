import { test, expect } from '@playwright/test';
import type { Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import fixture from '../../src/data/demo.json' with { type: 'json' };

test.setTimeout(60000);

// Mocked lifecycle contracts; actual evidence/API journeys remain in core.spec.ts.
function deferred() { let resolve!: () => void; const promise = new Promise<void>((done) => { resolve = done; }); return { promise, resolve }; }
async function contract(page: Page) {
  const state = { user: 'account-a', products: structuredClone(fixture.products), requests: [] as { query: string; product_id?: string }[],
    holdProducts: undefined as Promise<void> | undefined, productsStarted: deferred(), holdAnswer: undefined as Promise<void> | undefined,
    version: 1, answerError: false, citationProducts: [fixture.products[0].id],
    holdAccount: undefined as Promise<void> | undefined, accountStarted: deferred(), accountError: false, logoutCalls: 0,
    holdSession: undefined as Promise<void> | undefined, sessionStarted: deferred(), sessionTenant: 'tenant-a', sessionCreates: 0, protectedScopes: [] as string[], tenant: 'tenant-a',
    holdLogout: undefined as Promise<void> | undefined, logoutStarted: deferred() };
  await page.route('**/api/**', async (route) => {
    const req = route.request(); const path = new URL(req.url()).pathname.replace('/api', '');
    let data: unknown;
    if (req.headers()['x-workspace-id']) state.protectedScopes.push(req.headers()['x-workspace-id']);
    if (path === '/auth/logout') { state.logoutCalls += 1; data = {}; const hold = state.holdLogout; state.holdLogout = undefined; if (hold) { state.logoutStarted.resolve(); await hold; } }
    else if (path === '/auth/me') { data = { authenticated: true, user: { id: state.user, email: `${state.user}@example.test` }, active_tenant_id: state.tenant, memberships: [{ tenant_id: state.tenant, name: 'First workspace', role: 'owner' }], capabilities: ['read', 'edit', 'approve', 'manage_members', 'shopify'] };
      const fail = state.accountError; const hold = state.holdAccount; state.holdAccount = undefined;
      if (hold) { state.accountStarted.resolve(); await hold; }
      if (fail) { await route.fulfill({ status: 401, contentType: 'application/json', body: JSON.stringify({ detail: 'Expired account' }) }).catch(() => undefined); return; }
    }
    else if (path === '/session') { data = { tenant_id: state.sessionTenant }; if (req.method() === 'POST') state.sessionCreates += 1; const hold = state.holdSession; state.holdSession = undefined; if (hold) { state.sessionStarted.resolve(); await hold; } }
    else if (path === '/capabilities') data = { uploads: { max_bytes: 1024, media_types: ['text/csv'], csv_columns: [] }, retrieval: { methods: ['keyword'], context_max_chars: 4000 }, benchmark: { review_status: 'pending' } };
    else if (path === '/overview') data = { products: 3, sources: 6, passages: 12, drafts: 0, approved_drafts: 0, queued_jobs: 0, retrieval: { status: 'lexical_only', method: 'lexical', model: null, revision: null } };
    else if (path === '/products') { data = { products: structuredClone(state.products) }; const hold = state.holdProducts; state.holdProducts = undefined; if (hold) { state.productsStarted.resolve(); await hold; } }
    else if (path === '/sources') data = { sources: fixture.sources };
    else if (path === '/drafts') data = { drafts: [] };
    else if (path === '/audit') data = { events: [] };
    else if (path === '/evaluations') data = { evaluations: [] };
    else if (path === '/graph') data = { nodes: [], edges: [], impact: { stale_drafts: 0, current_source_revisions: 0 } };
    else if (path === '/answers') {
      const body = req.postDataJSON() as { query: string; product_id?: string }; state.requests.push(body);
      const hold = state.holdAnswer; state.holdAnswer = undefined; if (hold) await hold;
      if (state.answerError) { await route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ detail: 'Evidence service unavailable' }) }).catch(() => undefined); return; }
      data = { answer: `Revision ${state.version}: Current quotation for ${body.query}`, abstained: false, method: 'extractive_source_quotes', citations: state.citationProducts.map((id) => ({ passage_id: `passage-${id}`, product_id: id, product_name: fixture.products.find((product) => product.id === id)?.name || 'Unavailable product', source_id: fixture.sources[0].id, source_name: fixture.sources[0].name, source_version: fixture.sources[0].version, page: '1', text: 'Current product evidence.' })) };
    } else { await route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ detail: 'Test service unavailable' }) }); return; }
    await route.fulfill({ status: 200, contentType: 'application/json', headers: { 'X-Workspace-ID': req.headers()['x-workspace-id'] || '' }, body: JSON.stringify(data) }).catch(() => undefined);
  });
  await page.goto('/engine#ask');
  await expect(page.locator('#core-main')).toHaveAttribute('aria-busy', 'false');
  await expect(page.locator('.core-alert')).toHaveCount(0);
  return state;
}
async function submit(page: Page, query: string) {
  await page.getByRole('textbox', { name: 'What would you like to know?' }).fill(query);
  await page.getByRole('button', { name: 'Find a grounded answer', exact: true }).click();
}

test('contract assistant identifies AI and keeps only questions with visible follow-up scope', async ({ page }) => {
  const state = await contract(page);
  await expect(page.getByRole('heading', { name: 'AI assistance for product evidence', exact: true })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Contact the project operator', exact: true })).toHaveAttribute('href', '/contact');
  await submit(page, 'battery life');
  await expect(page.locator('.core-answer-text')).toContainText('battery life');
  await page.getByRole('button', { name: `Follow up about ${fixture.products[0].name}`, exact: true }).click();
  await expect(page.locator('#core-scope')).toHaveValue(fixture.products[0].id);
  await submit(page, 'charging');
  await expect(page.locator('.core-answer-text')).toContainText('charging');
  expect(state.requests[1]).toEqual({ query: 'charging', product_id: fixture.products[0].id });
  await expect(page.locator('.core-question-history')).toContainText('battery life');
  await expect(page.locator('.core-question-history')).not.toContainText('Current quotation');
  await page.getByRole('button', { name: 'Restart questions', exact: true }).click();
  await expect(page.locator('.core-question-history')).toHaveCount(0);
  await expect(page.locator('.core-answer')).toHaveCount(0);
  await expect(page.locator('#core-question')).toBeEmpty();
});

test('contract question history is bounded, fresh on reuse and absent after reload', async ({ page }) => {
  const state = await contract(page);
  for (let i = 1; i <= 7; i += 1) { await submit(page, `documented detail ${i}`); await expect(page.locator('.core-answer-text')).toContainText(`detail ${i}`); }
  await expect(page.locator('.core-question-history li')).toHaveCount(6);
  await expect(page.locator('.core-question-history')).not.toContainText('detail 1');
  await expect(page.locator('.core-answer')).toHaveCount(1);
  state.version = 2;
  await page.getByRole('button', { name: 'Edit or ask again: documented detail 3', exact: true }).click();
  await expect(page.locator('.core-answer')).toHaveCount(0);
  await expect(page.locator('#core-question')).toHaveValue('documented detail 3');
  await page.getByRole('button', { name: 'Find a grounded answer', exact: true }).click();
  await expect(page.locator('.core-answer-text')).toContainText('Revision 2');
  expect(state.requests.at(-1)).toEqual({ query: 'documented detail 3' });
  expect(await page.evaluate(() => Object.keys(localStorage).filter((key) => /question|chat|history|answer/i.test(key)))).toEqual([]);
  expect(await page.evaluate(() => Object.keys(sessionStorage))).toEqual([]);
  await page.reload();
  await expect(page.locator('#core-main')).toHaveAttribute('aria-busy', 'false');
  await expect(page.locator('.core-question-history')).toHaveCount(0);
  await expect(page.locator('.core-answer')).toHaveCount(0);
});

test('contract changed account in the same workspace clears questions and fences its late answer', async ({ page }) => {
  const state = await contract(page);
  await submit(page, 'earlier private question');
  await expect(page.locator('.core-question-history')).toContainText('earlier private question');
  const refresh = deferred(); state.holdProducts = refresh.promise;
  await submit(page, 'old account pending question');
  await state.productsStarted.promise;
  state.user = 'account-b'; refresh.resolve();
  await expect(page.locator('#core-main')).toHaveAttribute('aria-busy', 'false');
  await expect(page.locator('.core-answer')).toHaveCount(0);
  await expect(page.locator('.core-question-history')).toHaveCount(0);
  await expect(page.locator('#core-question')).toBeEmpty();
  await page.locator('nav:visible').getByRole('button', { name: 'Account & team', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'account-b@example.test', exact: true })).toBeVisible();
});

test('contract multiple or unavailable citation products never create an inferred follow-up scope', async ({ page }) => {
  const state = await contract(page); state.citationProducts = fixture.products.slice(0, 2).map((product) => product.id);
  await submit(page, 'compare documented products');
  await expect(page.locator('.core-answer-text')).toContainText('compare');
  await expect(page.getByRole('button', { name: /^Follow up about / })).toHaveCount(0);
  await expect(page.locator('#core-scope')).toHaveValue('');
  state.citationProducts = ['not-authorized-here'];
  await submit(page, 'another documented detail');
  await expect(page.locator('.core-answer-text')).toContainText('another');
  await expect(page.getByRole('button', { name: /^Follow up about / })).toHaveCount(0);
});

test('contract assistant outage preserves guidance, contact, keyboard access and layout', async ({ page }) => {
  const state = await contract(page); state.answerError = true;
  await submit(page, 'documented detail');
  await expect(page.getByRole('alert')).toContainText('Evidence service unavailable');
  await expect(page.getByRole('link', { name: 'Read the workflow guide', exact: true })).toHaveAttribute('href', '/docs');
  await expect(page.getByRole('link', { name: 'Contact the project operator', exact: true })).toHaveAttribute('href', '/contact');
  await page.getByRole('button', { name: 'Restart questions', exact: true }).click();
  await expect(page.locator('#core-question')).toBeFocused();
  const violations = (await new AxeBuilder({ page }).analyze()).violations.filter((item) => ['serious', 'critical'].includes(item.impact || ''));
  expect(violations).toEqual([]);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.getByRole('button', { name: 'Add permitted evidence', exact: true }).click();
  await expect(page.locator('.core-title h1')).toContainText('Bring your product knowledge');
});

test('contract stopping during answer refresh fences old snapshot and busy cleanup', async ({ page }) => {
  const state = await contract(page); const first = deferred(); const second = deferred();
  state.holdProducts = first.promise;
  await submit(page, 'first question');
  await state.productsStarted.promise;
  await page.getByRole('button', { name: 'Stop waiting', exact: true }).click();
  await expect(page.getByRole('status').filter({ hasText: 'Stopped waiting for this search.' })).toBeVisible();
  state.products[0].name = 'Updated authorized product'; state.holdAnswer = second.promise;
  await submit(page, 'second question');
  await expect.poll(() => state.requests.length).toBe(2);
  first.resolve();
  await expect(page.getByRole('button', { name: 'Stop waiting', exact: true })).toBeEnabled();
  await expect(page.getByRole('button', { name: 'Find a grounded answer', exact: true })).toBeDisabled();
  second.resolve();
  await expect(page.locator('.core-answer-text')).toContainText('second question');
  await expect(page.locator('#core-scope option').filter({ hasText: 'Updated authorized product' })).toHaveCount(1);
  await expect(page.locator('.core-answer-text')).not.toContainText('first question');
  await expect(page.locator('.core-question-history')).not.toContainText('first question');
});


test('contract canceled account refresh cannot log out a newer active search', async ({ page }) => {
  const state = await contract(page); const old = deferred();
  state.holdAccount = old.promise; state.accountError = true;
  await submit(page, 'old account lookup'); await state.accountStarted.promise;
  await page.getByRole('button', { name: 'Stop waiting', exact: true }).click();
  state.accountError = false;
  await submit(page, 'new account search');
  await expect(page.locator('.core-answer-text')).toContainText('new account search');
  old.resolve();
  // A subsequent complete search is the observable barrier after the stale auth continuation.
  await submit(page, 'current account remains usable');
  await expect(page.locator('.core-answer-text')).toContainText('current account remains usable');
  expect(state.logoutCalls).toBe(0); expect(state.sessionCreates).toBe(0);
  await expect(page.locator('.core-alert')).toHaveCount(0);
});

test('contract canceled session checkpoint cannot install a different workspace scope', async ({ page }) => {
  const state = await contract(page); const old = deferred();
  state.holdSession = old.promise; state.sessionTenant = 'tenant-b';
  await submit(page, 'old session checkpoint'); await state.sessionStarted.promise;
  await page.getByRole('button', { name: 'Stop waiting', exact: true }).click();
  state.sessionTenant = 'tenant-a';
  await submit(page, 'new workspace checkpoint');
  await expect(page.locator('.core-answer-text')).toContainText('new workspace checkpoint');
  old.resolve();
  await submit(page, 'current workspace remains usable');
  await expect(page.locator('.core-answer-text')).toContainText('current workspace remains usable');
  await expect(page.locator('.core-alert')).toHaveCount(0);
  await expect(page.locator('.core-question-history')).not.toContainText('old session checkpoint');
  expect(new Set(state.protectedScopes)).toEqual(new Set(['tenant-a']));
});

test('contract direct hash exit fences a late answer and clears its question context', async ({ page }) => {
  const state = await contract(page); const old = deferred(); state.holdAnswer = old.promise;
  await submit(page, 'private pending question');
  await expect.poll(() => state.requests.length).toBe(1);
  await page.evaluate(() => { window.location.hash = 'evidence'; });
  await expect(page.locator('.core-title h1')).toContainText('Follow every detail to its source.');
  old.resolve();
  await page.evaluate(() => { window.location.hash = 'ask'; });
  await expect(page.locator('#core-main')).toHaveAttribute('aria-busy', 'false');
  await expect(page.locator('#core-question')).toBeEmpty();
  await expect(page.locator('.core-answer')).toHaveCount(0);
  await expect(page.locator('.core-question-history')).toHaveCount(0);
  await submit(page, 'new navigation question');
  await expect(page.locator('.core-answer-text')).toContainText('new navigation question');
});


test('contract current refresh discovers cookie workspace changes and reboots access', async ({ page }) => {
  const state = await contract(page); const old = deferred();
  await submit(page, 'old workspace history');
  await expect(page.locator('.core-answer-text')).toContainText('old workspace history');
  state.holdAnswer = old.promise; await submit(page, 'workspace changes externally');
  await expect.poll(() => state.requests.length).toBe(2);
  state.tenant = 'tenant-b'; state.sessionTenant = 'tenant-b'; old.resolve();
  await expect(page.locator('#core-main')).toHaveAttribute('aria-busy', 'false');
  await expect(page.locator('.core-question-history')).toHaveCount(0);
  await expect(page.locator('.core-answer')).toHaveCount(0);
  await expect(page.locator('#core-question')).toBeEmpty();
  await expect(page.getByRole('alert')).toContainText('The active workspace changed. Reload before continuing.');
  await submit(page, 'new authorized workspace');
  await expect(page.locator('.core-answer-text')).toContainText('new authorized workspace');
  expect(state.protectedScopes.at(-1)).toBe('tenant-b');
});


test('contract observed expired account clears private questions before cookie recovery finishes', async ({ page }) => {
  const state = await contract(page); const logout = deferred();
  await submit(page, 'previous private question');
  await expect(page.locator('.core-question-history')).toContainText('previous private question');
  state.accountError = true; state.holdLogout = logout.promise;
  await submit(page, 'access expires during this search'); await state.logoutStarted.promise;
  const stop = page.getByRole('button', { name: 'Stop waiting', exact: true });
  if (await stop.count()) await stop.click();
  await expect(page.locator('.core-question-history')).toHaveCount(0);
  await expect(page.locator('.core-question-form')).toHaveCount(0);
  state.accountError = false; logout.resolve();
  await expect(page.locator('#core-main')).toHaveAttribute('aria-busy', 'false');
  await expect(page.locator('.core-question-history')).toHaveCount(0);
  await expect(page.locator('#core-question')).toBeEmpty();
  expect(state.logoutCalls).toBe(1);
});
