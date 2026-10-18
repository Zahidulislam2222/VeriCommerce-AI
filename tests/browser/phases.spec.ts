import { test, expect } from '@playwright/test';
import type { Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import fixture from '../../src/data/demo.json' with { type: 'json' };

test.setTimeout(90000);

// Contract fixtures exercise UI boundaries only. Real PostgreSQL/provider flows
// remain separate integration gates and are never inferred from these responses.
function account(tenant = 'tenant-a', capabilities = ['read', 'edit', 'approve', 'manage_members', 'shopify']) {
  return { authenticated: true, user: { id: 'account-a', email: 'owner@example.test' }, memberships: [{ tenant_id: 'tenant-a', name: 'First workspace', role: 'owner' }, { tenant_id: 'tenant-b', name: 'Second workspace', role: 'viewer' }], active_tenant_id: tenant, capabilities };
}
async function mock(page: Page, authenticated = true) {
  let identity = authenticated ? account() : { authenticated: false, memberships: [], capabilities: ['read', 'edit', 'approve'] };
  const calls: { path: string; method: string; body: unknown }[] = [];
  await page.route('**/api/**', async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname.replace('/api', '');
    const body: unknown = request.postDataJSON();
    calls.push({ path, method: request.method(), body });
    let data: unknown;
    if (path === '/session') data = { tenant_id: identity.authenticated && 'active_tenant_id' in identity ? identity.active_tenant_id : 'demo' };
    else if (path === '/auth/me') data = identity;
    else if (path === '/auth/tenant/select') { identity = account('tenant-b', ['read']); data = identity; }
    else if (path === '/auth/logout') { identity = { authenticated: false, memberships: [], capabilities: ['read', 'edit', 'approve'] }; data = identity; }
    else if (path === '/capabilities') data = { uploads: { max_bytes: 64, media_types: ['text/csv', 'image/png'], csv_columns: ['product_id', 'passage'] }, retrieval: { methods: ['keyword', 'dense', 'hybrid', 'rerank'], context_max_chars: 4000 }, benchmark: { review_status: 'pending' } };
    else if (path === '/overview') data = { products: 3, sources: 4, passages: 8, drafts: 0, approved_drafts: 0, queued_jobs: 0, retrieval: { status: 'dense_available', method: 'hybrid_rrf', model: null, revision: null } };
    else if (path === '/products') data = { products: identity.authenticated && 'active_tenant_id' in identity && identity.active_tenant_id === 'tenant-b' ? [] : fixture.products };
    else if (path === '/sources') data = { sources: fixture.sources };
    else if (path === '/drafts') data = { drafts: [] };
    else if (path === '/audit') data = { events: [] };
    else if (path === '/evaluations') data = { evaluations: [] };
    else if (path === '/graph') data = { nodes: [], edges: [], impact: { stale_drafts: 0, current_source_revisions: 0 } };
    else if (path === '/shopify') data = { configured: false, connection: null, syncs: [], webhooks: { total: 0, latest: null } };
    else if (path === '/jobs') data = { jobs: [{ id: 'job-a', kind: 'upload', status: 'dead_letter', error: 'Parser limit exceeded' }] };
    else if (path === '/context') data = { method: 'dense', available: false, results: [], context: { selected: [], excluded: [{ passage_id: 'passage-a', reason: 'method unavailable' }], budget_chars: 4000, used_chars: 0, snapshot_hash: 'snapshot-a', authority: 'current tenant sources' }, retrieval: { status: 'unavailable' } };
    else if (path === '/benchmark-dataset') data = { version: 'test-corpus', hash: 'a'.repeat(64), review_status: 'pending', license: 'original synthetic fixtures', products: [], questions: [{ id: 'question-a', product_id: 'forma', split: 'test', query: 'Which source proves battery life?', expected_source_id: 'forma-manual', expected_abstain: false, reviewed: false }], images: [], reviews: [] };
    else if (path === '/benchmark-reviews') data = { review: { id: 'review-a' } };
    else if (path.startsWith('/intelligence/')) data = { product_id: path.split('/').pop(), contradictions: [], blocked_claims: [], relations: [], image_reviews: [], drafts: [], json_ld: { available: false, document: null, blocked: ['Missing evidence for price'], provenance: {} } };
    else { await route.fulfill({ status: 503, contentType: 'application/json', headers: { 'X-Workspace-ID': route.request().headers()['x-workspace-id'] || '' }, body: JSON.stringify({ detail: 'Test service unavailable' }) }); return; }
    await route.fulfill({ status: 200, contentType: 'application/json', headers: { 'X-Workspace-ID': route.request().headers()['x-workspace-id'] || '' }, body: JSON.stringify(data) });
  });
  return calls;
}
async function open(page: Page, view: string) { await page.goto(`/engine#${view}`); await expect(page.locator('.core-loading')).toHaveCount(0); await expect(page.locator('.core-alert')).toHaveCount(0); await expect(page.locator('#core-main')).toHaveAttribute('aria-busy', 'false'); }

test('contract UI clears tenant data and disables forbidden writes', async ({ page }) => {
  const calls = await mock(page);
  await open(page, 'account');
  await page.getByLabel('Active workspace').selectOption('tenant-b');
  await expect(page.getByLabel('Active workspace')).toHaveValue('tenant-b');
  await page.goto('/engine#drafts');
  await expect(page.getByRole('button', { name: 'Forma One', exact: true })).toHaveCount(0);
  await page.goto('/engine#import');
  await expect(page.getByRole('button', { name: 'Upload and process', exact: true })).toBeDisabled();
  expect(calls.filter((call) => call.path === '/auth/tenant/select')).toHaveLength(1);
  expect(await page.evaluate(() => Object.keys(localStorage).filter((key) => /auth|password|token|account/i.test(key)))).toEqual([]);
});

test('contract UI rejects oversized uploads before reading or sending content', async ({ page }) => {
  const calls = await mock(page);
  await open(page, 'import');
  await page.getByLabel('Catalog or source file').setInputFiles({ name: 'catalog.csv', mimeType: 'text/csv', buffer: Buffer.alloc(65, 'a') });
  await page.getByLabel('Related product').selectOption(fixture.products[0].id);
  await page.getByLabel('Stable source ID').fill('test-source');
  await page.getByLabel('Source revision', { exact: true }).fill('v1');
  await page.getByRole('button', { name: 'Upload and process', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('exceeds');
  expect(calls.filter((call) => call.path === '/uploads' && call.method === 'POST')).toHaveLength(0);
});

test('contract UI shows unavailable retrieval and unconfigured Shopify honestly', async ({ page }) => {
  await mock(page);
  await open(page, 'compare');
  await page.getByRole('textbox', { name: 'Question or constraints', exact: true }).fill('Battery life');
  await page.getByLabel('Retrieval method').selectOption('dense');
  await page.getByRole('button', { name: 'Inspect context', exact: true }).click();
  await expect(page.getByText('This method is unavailable.', { exact: false })).toBeVisible();
  await expect(page.getByText('snapshot-a', { exact: false })).toBeVisible();
  await page.goto('/engine#connections');
  await page.getByRole('button', { name: 'Refresh records', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Connect read-only store', exact: true })).toBeDisabled();
  await expect(page.getByRole('button', { name: 'Synchronize catalog', exact: true })).toBeDisabled();
  await expect(page.getByRole('button', { name: 'Retire imported evidence', exact: true })).toBeDisabled();
});

test('contract human-review UI requires inspected IDs, notes and explicit confirmation', async ({ page }) => {
  const calls = await mock(page);
  await open(page, 'lab');
  await page.getByRole('button', { name: 'Inspect the review dataset', exact: true }).click();
  const submit = page.getByRole('button', { name: 'Record human review', exact: true });
  await expect(submit).toBeDisabled();
  await page.getByText('Question labels (1)', { exact: true }).click();
  await page.getByRole('checkbox', { name: 'Which source proves battery life?', exact: false }).check();
  await page.getByLabel('Review notes and corrections').fill('Reviewed against source; label needs human source verification.');
  await expect(submit).toBeDisabled();
  await page.getByRole('checkbox', { name: 'I inspected every selected', exact: false }).check();
  await submit.click();
  await expect(page.getByRole('status').filter({ hasText: 'Human review record saved.' })).toBeVisible();
  expect(calls.find((call) => call.path === '/benchmark-reviews')?.body).toMatchObject({ question_ids: ['question-a'], image_ids: [], decision: 'needs_changes' });
});

test('contract phase views remain accessible and wrap at desktop and mobile widths', async ({ page }, testInfo) => {
  await mock(page);
  for (const view of ['account', 'connections', 'compare', 'review', 'import', 'activity', 'lab', 'evidence']) {
    await open(page, view);
    if (view === 'review') { await page.getByLabel('Product to inspect').selectOption(fixture.products[0].id); await page.getByRole('button', { name: 'Inspect current evidence', exact: true }).click(); }
    const violations = (await new AxeBuilder({ page }).analyze()).violations.filter((item) => ['critical', 'serious'].includes(item.impact || ''));
    expect(violations, view).toEqual([]);
    for (const width of [360, 375, 768, 1440]) { await page.setViewportSize({ width, height: 900 }); expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `${view} @ ${width}`).toBe(true); }
  }
  await page.setViewportSize(testInfo.project.use.viewport!);
  await page.goto('/engine#compare');
  await page.getByRole('textbox', { name: 'Question or constraints', exact: true }).fill('Battery life');
  await page.getByRole('button', { name: 'Inspect context', exact: true }).click();
  await page.locator('.core-title h1').focus();
  await page.evaluate(() => scrollTo(0, 0));
  await page.screenshot({ path: `memory/screenshots/phase-contract-${testInfo.project.name}.png`, fullPage: true });
});

test('contract accounts without a membership can create or select a workspace', async ({ page }) => {
  const calls = await mock(page);
  await page.route('**/api/auth/me', (route) => route.fulfill({ contentType: 'application/json', headers: { 'X-Workspace-ID': route.request().headers()['x-workspace-id'] || '' }, body: JSON.stringify({ authenticated: true, user: { id: 'orphan', email: 'orphan@example.test' }, active_tenant_id: 'revoked-membership', memberships: [], capabilities: [] }) }));
  await open(page, 'account');
  await expect(page.getByRole('button', { name: 'Create workspace', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Sign out', exact: true })).toBeVisible();
  expect(calls.filter((call) => call.path === '/overview')).toHaveLength(0);
});

test('contract connector rejects an authorization URL outside the permitted Shopify host', async ({ page }) => {
  await mock(page);
  await page.route('**/api/shopify', (route) => route.fulfill({ contentType: 'application/json', headers: { 'X-Workspace-ID': route.request().headers()['x-workspace-id'] || '' }, body: JSON.stringify({ configured: true, connection: null, syncs: [], webhooks: { total: 0, latest: null } }) }));
  await page.route('**/api/shopify/connect', (route) => route.fulfill({ contentType: 'application/json', headers: { 'X-Workspace-ID': route.request().headers()['x-workspace-id'] || '' }, body: JSON.stringify({ authorization_url: 'https://merchant.myshopify.com.evil.example/admin/oauth/authorize' }) }));
  await open(page, 'connections');
  await page.getByRole('button', { name: 'Refresh records', exact: true }).click();
  await page.getByLabel('Shop domain').fill('merchant.myshopify.com');
  await page.getByRole('button', { name: 'Connect read-only store', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('invalid authorization destination');
  await expect(page).toHaveURL(/\/engine#connections$/);
});


test('contract expired account cookie is cleared once and login controls recover', async ({ page }) => {
  await mock(page, false);
  let expired = true;
  let revoked = 0;
  await page.route('**/api/auth/me', (route) => route.fulfill({ status: expired ? 401 : 200, contentType: 'application/json', headers: { 'X-Workspace-ID': route.request().headers()['x-workspace-id'] || '' }, body: JSON.stringify(expired ? { detail: 'Account session expired' } : { authenticated: false, memberships: [], capabilities: ['read', 'edit', 'approve'] }) }));
  await page.route('**/api/auth/logout', (route) => { expired = false; revoked++; return route.fulfill({ contentType: 'application/json', headers: { 'X-Workspace-ID': route.request().headers()['x-workspace-id'] || '' }, body: '{}' }); });
  await open(page, 'account');
  await expect(page.getByRole('button', { name: 'Sign in', exact: true })).toBeVisible();
  expect(revoked).toBe(1);
});

test('contract delayed intelligence cannot be reviewed under a different product', async ({ page }) => {
  await mock(page);
  let release: () => void = () => undefined;
  const pending = new Promise<void>((resolve) => { release = resolve; });
  await page.route('**/api/intelligence/**', async (route) => {
    await pending;
    await route.fulfill({ contentType: 'application/json', headers: { 'X-Workspace-ID': route.request().headers()['x-workspace-id'] || '' }, body: JSON.stringify({ product_id: fixture.products[0].id, contradictions: [], blocked_claims: [], relations: [], image_reviews: [], drafts: [], json_ld: { available: false, document: null, blocked: ['First product only'], provenance: {} } }) });
  });
  await open(page, 'review');
  const selection = page.getByLabel('Product to inspect');
  await selection.selectOption(fixture.products[0].id);
  await page.getByRole('button', { name: 'Inspect current evidence', exact: true }).click();
  await expect(selection).toBeDisabled();
  release();
  await expect(page.locator('#core-main')).toHaveAttribute('aria-busy', 'false');
  await expect(page.getByText('First product only', { exact: false })).toBeVisible();
  await selection.selectOption(fixture.products[1].id);
  await expect(page.getByText('First product only', { exact: false })).toHaveCount(0);
  await page.getByRole('button', { name: 'Inspect current evidence', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('different product');
  await expect(page.getByText('First product only', { exact: false })).toHaveCount(0);
});

test('contract source history and retrieval controls are stable during delayed requests', async ({ page }) => {
  await mock(page);
  let releaseVersions: () => void = () => undefined;
  const versions = new Promise<void>((resolve) => { releaseVersions = resolve; });
  await page.route('**/api/sources/*/versions', async (route) => { await versions; await route.fulfill({ contentType: 'application/json', headers: { 'X-Workspace-ID': route.request().headers()['x-workspace-id'] || '' }, body: JSON.stringify({ versions: [{ revision_id: 'revision-a', metadata: { version: 'a' }, created_at: '2026-10-18T00:00:00Z', current: true, content_hash: 'abc', passages: [{ passage_id: 'a', label: 'Battery', value: '40 hours', text: 'First source only', page: '1' }] }] }) }); });
  await open(page, 'evidence');
  const source = page.getByLabel('Source', { exact: false }).first();
  await source.selectOption(fixture.sources[0].id);
  await page.getByRole('button', { name: 'Inspect source history', exact: true }).click();
  await expect(source).toBeDisabled();
  releaseVersions();
  await expect(page.locator('#core-main')).toHaveAttribute('aria-busy', 'false');
  await source.selectOption(fixture.sources[1].id);
  await expect(page.getByText('First source only', { exact: false })).toHaveCount(0);

  let releaseContext: () => void = () => undefined;
  const context = new Promise<void>((resolve) => { releaseContext = resolve; });
  await page.route('**/api/context', async (route) => { await context; await route.fulfill({ contentType: 'application/json', headers: { 'X-Workspace-ID': route.request().headers()['x-workspace-id'] || '' }, body: JSON.stringify({ method: 'keyword', available: true, results: [], context: { selected: [], excluded: [], budget_chars: 4000, used_chars: 0, snapshot_hash: 'current', authority: 'current tenant' }, retrieval: {} }) }); });
  await page.goto('/engine#compare');
  const query = page.getByRole('textbox', { name: 'Question or constraints', exact: true });
  await query.fill('Battery life');
  await page.getByRole('button', { name: 'Inspect context', exact: true }).click();
  await expect(query).toBeDisabled();
  await expect(page.getByLabel('Retrieval method')).toBeDisabled();
  await expect(page.getByLabel('First product')).toBeDisabled();
  releaseContext();
  await expect(query).toBeEnabled();
});

test('contract viewer cannot run legacy or expanded evaluations', async ({ page }) => {
  await mock(page);
  await page.route('**/api/auth/me', (route) => route.fulfill({ contentType: 'application/json', headers: { 'X-Workspace-ID': route.request().headers()['x-workspace-id'] || '' }, body: JSON.stringify(account('tenant-a', ['read'])) }));
  await open(page, 'lab');
  await expect(page.getByRole('button', { name: 'Run measured checks', exact: true })).toBeDisabled();
  await expect(page.getByRole('button', { name: 'Run benchmark', exact: true })).toBeDisabled();
});

test('contract cross-tab cursor change retries reads with the verified workspace scope', async ({ page }) => {
  const calls = await mock(page);
  let cursor = 'tenant-a';
  await page.route('**/api/auth/me', (route) => route.fulfill({ contentType: 'application/json', body: JSON.stringify(account(cursor)) }));
  await page.route('**/api/session', (route) => { cursor = 'tenant-b'; return route.fulfill({ contentType: 'application/json', body: JSON.stringify({ tenant_id: cursor }) }); });
  await open(page, 'account');
  await expect(page.getByLabel('Active workspace')).toHaveValue('tenant-b');
  expect(calls.filter((call) => call.path === '/products')).toHaveLength(1);
});

test('contract observed authorization loss clears private panel data and old role controls', async ({ page }) => {
  await mock(page);
  let revoked = false;
  await page.route('**/api/auth/me', (route) => route.fulfill({ contentType: 'application/json', body: JSON.stringify(account('tenant-a', revoked ? ['read'] : ['read', 'edit', 'approve', 'manage_members', 'shopify'])) }));
  await page.route('**/api/context', (route) => { revoked = true; return route.fulfill({ status: 403, contentType: 'application/json', body: JSON.stringify({ detail: 'Workspace membership changed' }) }); });
  await open(page, 'compare');
  await page.getByRole('textbox', { name: 'Question or constraints', exact: true }).fill('Private previous query');
  await page.getByRole('button', { name: 'Inspect context', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('Workspace membership changed');
  await expect(page.getByRole('textbox', { name: 'Question or constraints', exact: true })).toHaveValue('');
  await page.goto('/engine#lab');
  await expect(page.getByRole('button', { name: 'Run measured checks', exact: true })).toBeDisabled();
});

test('contract functional corpus images open actual facts without leaving the evaluation route', async ({ page }) => {
  await mock(page);
  const product = fixture.products[0];
  await page.route('**/api/benchmark-dataset', (route) => route.fulfill({ contentType: 'application/json', headers: { 'X-Workspace-ID': route.request().headers()['x-workspace-id'] || '' }, body: JSON.stringify({ version: 'purpose-test', hash: 'a'.repeat(64), review_status: 'agent_reviewed', agent_review_status: 'agent_reviewed', human_review_status: 'pending', license: 'original fixtures', products: [{ id: product.id, name: product.name, family: 'Forma', split: 'test' }], catalog: { products: [product], sources: [] }, questions: [], images: [{ id: 'decorative-image', product_id: product.id, path: '/images/hero-headphones.webp', purpose: 'decorative', expected_alt: '', usage_context: 'Decorative separator beside the named product.', function: '', destination: '', reviewed: false }, { id: 'functional-image', product_id: product.id, path: '/images/hero-headphones.webp', purpose: 'functional', expected_alt: 'Open Forma One source facts', usage_context: 'Link to the product source facts.', function: 'Open Forma One source facts', destination: `#benchmark-product-${product.id}`, reviewed: false }], reviews: [] }) }));
  await open(page, 'lab');
  await page.getByRole('button', { name: 'Inspect the review dataset', exact: true }).click();
  await page.getByText('Image labels and purpose (2)', { exact: true }).click();
  await expect(page.locator('article').filter({ hasText: 'decorative-image' }).locator('img')).toHaveAttribute('alt', '');
  await page.getByRole('link', { name: 'Open Forma One source facts', exact: true }).click();
  await expect(page).toHaveURL(/#lab$/);
  await expect(page.locator(`#benchmark-product-${product.id}`)).toBeVisible();
  await expect(page.locator(`#benchmark-product-${product.id}`)).toBeFocused();
  await expect(page.locator(`#benchmark-product-${product.id}`)).toContainText('40 hours');
  await expect(page.getByText('Human review state: pending', { exact: false })).toBeVisible();
});

test('contract anonymous capacity exhaustion preserves account access without fake catalog data', async ({ page }) => {
  const calls = await mock(page, false);
  await page.route('**/api/session', (route) => route.fulfill({ status: 429, contentType: 'application/json', body: JSON.stringify({ detail: 'Temporary workspace capacity reached' }) }));
  await open(page, 'account');
  await expect(page.getByRole('button', { name: 'Sign in', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Create account', exact: true })).toBeVisible();
  await expect(page.getByText('Temporary workspace capacity reached', { exact: true })).toBeVisible();
  expect(calls.filter((call) => ['/products', '/sources', '/overview'].includes(call.path))).toHaveLength(0);
});

test('contract leaving during file reading prevents a write to a cleared workspace', async ({ page }) => {
  await page.addInitScript(() => {
    const NativeReader = window.FileReader;
    window.FileReader = class extends NativeReader {
      override readAsDataURL(blob: Blob) {
        Reflect.set(window, 'releasePhaseFile', () => { this.addEventListener('loadend', () => Reflect.set(window, 'phaseFileFinished', true), { once: true }); super.readAsDataURL(blob); });
      }
    };
  });
  const calls = await mock(page);
  await open(page, 'import');
  await page.getByLabel('Catalog or source file').setInputFiles({ name: 'catalog.csv', mimeType: 'text/csv', buffer: Buffer.from('name\npermitted\n') });
  await page.getByLabel('Stable source ID').fill('delayed-source');
  await page.getByLabel('Source revision', { exact: true }).fill('1');
  await page.getByRole('button', { name: 'Upload and process', exact: true }).click();
  await expect(page.locator('#core-main')).toHaveAttribute('aria-busy', 'true');
  await page.locator('.core-brand:visible, .core-mobile-home:visible').click();
  await expect(page.getByRole('heading', { level: 1 })).toContainText('Real evidence.');
  await page.evaluate(() => Reflect.get(window, 'releasePhaseFile')());
  await expect.poll(() => page.evaluate(() => Reflect.get(window, 'phaseFileFinished'))).toBe(true);
  expect(calls.filter((call) => call.path === '/uploads' && call.method === 'POST')).toHaveLength(0);
});

test('contract a late OAuth response cannot redirect after leaving its workspace', async ({ page }) => {
  await mock(page);
  let release: () => void = () => undefined;
  const pending = new Promise<void>((resolve) => { release = resolve; });
  let externalRequests = 0;
  await page.route('https://**/*', (route) => { externalRequests++; return route.abort(); });
  await page.route('**/api/shopify', (route) => route.fulfill({ contentType: 'application/json', headers: { 'X-Workspace-ID': route.request().headers()['x-workspace-id'] || '' }, body: JSON.stringify({ configured: true, connection: null, syncs: [], webhooks: { total: 0, latest: null } }) }));
  await page.route('**/api/shopify/connect', async (route) => { await pending; await route.fulfill({ contentType: 'application/json', headers: { 'X-Workspace-ID': route.request().headers()['x-workspace-id'] || '' }, body: JSON.stringify({ authorization_url: 'https://merchant.myshopify.com/admin/oauth/authorize' }) }); });
  await open(page, 'connections');
  await page.getByLabel('Shop domain').fill('merchant.myshopify.com');
  await page.getByRole('button', { name: 'Connect read-only store', exact: true }).click();
  await page.locator('.core-brand:visible, .core-mobile-home:visible').click();
  const response = page.waitForResponse((item) => item.url().endsWith('/api/shopify/connect'));
  release();
  await response;
  await page.evaluate(() => new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))));
  await expect(page.getByRole('heading', { level: 1 })).toContainText('Real evidence.');
  expect(externalRequests).toBe(0);
});
