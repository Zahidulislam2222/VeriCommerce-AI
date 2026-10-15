import { test, expect } from '@playwright/test';
import type { Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { readFile } from 'node:fs/promises';
import fixture from '../../src/data/demo.json' with { type: 'json' };

test.setTimeout(90000);
async function open(page: Page, view = 'overview') {
  await page.goto(`/engine#${view}`);
  await expect(page.locator('.core-loading')).toHaveCount(0, { timeout: 30000 });
  await expect(page.locator('.core-alert')).toHaveCount(0);
  await expect(page.locator('.core-title h1')).toBeVisible();
}
async function navigate(page: Page, label: string) {
  await page.locator('nav:visible').getByRole('button', { name: label, exact: true }).click();
}
async function ask(page: Page, question: string) {
  await page.getByRole('textbox', { name: 'What would you like to know?' }).fill(question);
  await page.getByRole('button', { name: 'Find a grounded answer', exact: true }).click();
  await expect(page.locator('.core-busy')).toHaveCount(0, { timeout: 30000 });
}

test('real evidence answers cite current passages and unsupported claims abstain', async ({ page }) => {
  await open(page, 'ask');
  await ask(page, "What is Forma One's battery life?");
  await expect(page.locator('.core-answer-text')).toContainText('40 hours');
  await page.locator('.core-answer .core-citation').first().click();
  await expect(page.getByRole('dialog')).toContainText('active noise cancellation disabled');
  await page.keyboard.press('Escape');
  await ask(page, 'Does Verdant Daily cure eczema?');
  await expect(page.locator('.core-answer')).toHaveClass(/abstained/);
  await expect(page.locator('.core-answer .core-citation')).toHaveCount(0);
});

test('durable draft approval survives reload; changing its source blocks stale export', async ({ page }) => {
  await open(page, 'drafts');
  await page.getByRole('button', { name: 'Forma One', exact: true }).click();
  await expect(page.locator('.core-draft')).toHaveCount(1, { timeout: 30000 });
  await page.getByRole('button', { name: 'Approve this draft', exact: true }).click();
  await expect(page.getByRole('dialog')).toContainText('active noise cancellation disabled');
  await page.getByRole('dialog').getByRole('button', { name: 'Approve this draft', exact: true }).click();
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await expect(page.locator('.core-draft-state')).toHaveText('approved');
  await page.reload();
  await expect(page.locator('.core-draft-state')).toHaveText('approved');
  const downloadPromise = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Export approved JSON', exact: true }).click();
  const download = await downloadPromise;
  const data = JSON.parse(await readFile((await download.path())!, 'utf8'));
  expect(JSON.stringify(data)).toContain('forma-manual');
  expect(JSON.stringify(data)).toContain('40 hours');

  await navigate(page, 'Import catalog');
  const changed = structuredClone({ products: fixture.products, sources: fixture.sources });
  changed.sources[0].version = 'browser-check-3.0';
  changed.products[0].claims[0].value = 'Up to 20 hours';
  changed.products[0].claims[0].passage = 'Battery life: up to 20 hours of playback with active noise cancellation disabled. Test revision supersedes the prior 40-hour specification.';
  await page.getByRole('textbox', { name: 'Catalog JSON', exact: true }).fill(JSON.stringify(changed));
  await page.getByRole('button', { name: 'Validate and ingest', exact: true }).click();
  await expect(page.getByRole('status').filter({ hasText: 'Ingestion completed.' })).toBeVisible({ timeout: 30000 });
  await navigate(page, 'Content studio');
  await expect(page.locator('.core-draft-state')).toContainText('Stale');
  await expect(page.getByRole('button', { name: 'Export approved JSON', exact: true })).toHaveCount(0);
  await navigate(page, 'Ask the evidence');
  await ask(page, "What is Forma One's battery life?");
  await expect(page.locator('.core-answer-text')).toContainText('up to 20 hours');
  await expect(page.locator('.core-answer-text')).toContainText('browser-check-3.0');
});

test('actual measured evaluation and every core view remain accessible on primary widths', async ({ page }, testInfo) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await open(page, 'lab');
  await page.getByRole('button', { name: 'Run measured checks', exact: true }).click();
  await expect(page.locator('.core-evaluation-summary')).toBeVisible({ timeout: 30000 });
  await expect(page.locator('.core-evaluation-cases article')).not.toHaveCount(0);
  for (const label of ['Overview', 'Ask the evidence', 'Evidence library', 'Content studio', 'Import catalog', 'Evaluation lab', 'Activity']) {
    await navigate(page, label);
    const violations = (await new AxeBuilder({ page }).analyze()).violations.filter((item) => ['critical', 'serious'].includes(item.impact || ''));
    expect(violations).toEqual([]);
    for (const width of [360, 375, 768, 1440]) {
      await page.setViewportSize({ width, height: 900 });
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `${label} @ ${width}`).toBe(true);
    }
    await page.setViewportSize(testInfo.project.use.viewport!);
  }
  await navigate(page, 'Overview');
  for (const image of await page.locator('img').all()) await expect(image).toHaveJSProperty('complete', true);
  await page.screenshot({ path: `memory/screenshots/core-${testInfo.project.name}-ready.png`, fullPage: true });
});

test('expired access cookie recovers a new isolated server workspace on refresh', async ({ page, context }) => {
  await open(page, 'drafts');
  await page.getByRole('button', { name: 'Forma One', exact: true }).click();
  await expect(page.locator('.core-draft')).toHaveCount(1, { timeout: 30000 });
  await context.clearCookies();
  await page.getByRole('button', { name: 'Refresh data', exact: true }).click();
  await expect(page.locator('.core-draft')).toHaveCount(0, { timeout: 30000 });
  await expect(page.locator('.core-alert')).toHaveCount(0);
  await expect(page.getByText('Your collection is ready.', { exact: false })).toBeVisible();
});

test('source conflict during an open approval is visible inside the modal', async ({ page }) => {
  await open(page, 'drafts');
  await page.getByRole('button', { name: 'Forma One', exact: true }).click();
  await expect(page.locator('.core-draft')).toHaveCount(1, { timeout: 30000 });
  await page.getByRole('button', { name: 'Approve this draft', exact: true }).click();
  const changed = structuredClone({ products: fixture.products, sources: fixture.sources });
  changed.sources[0].version = 'concurrent-check-3.0';
  changed.products[0].claims[0].passage += ' Concurrent test revision.';
  const queued = await page.request.post('/api/ingestions', { data: changed, headers: { Origin: new URL(page.url()).origin } });
  expect(queued.status()).toBe(202);
  const { job } = await queued.json();
  await expect.poll(async () => (await (await page.request.get(`/api/jobs/${job.id}`)).json()).job.status, { timeout: 30000 }).toBe('succeeded');
  await page.getByRole('dialog').getByRole('button', { name: 'Approve this draft', exact: true }).click();
  await expect(page.getByRole('dialog').getByRole('alert')).toBeVisible();
  await expect(page.getByRole('dialog').getByRole('button', { name: 'Approve this draft', exact: true })).toBeDisabled();
  await page.keyboard.press('Escape');
  await expect(page.locator('.core-draft-state')).toContainText('Stale');
});

test('contract-valid long catalog fields wrap instead of overflowing or clipping', async ({ page }) => {
  await open(page, 'import');
  const changed = structuredClone({ products: fixture.products, sources: fixture.sources });
  for (const source of changed.sources) { source.name = 'S'.repeat(200); source.version = 'V'.repeat(200); }
  for (const product of changed.products) { product.name = 'P'.repeat(200); product.description = 'D'.repeat(4000); }
  await page.getByRole('textbox', { name: 'Catalog JSON', exact: true }).fill(JSON.stringify(changed));
  await page.getByRole('button', { name: 'Validate and ingest', exact: true }).click();
  await expect(page.getByRole('status').filter({ hasText: 'Ingestion completed.' })).toBeVisible({ timeout: 30000 });
  for (const label of ['Overview', 'Evidence library']) {
    await navigate(page, label);
    for (const width of [360, 375, 768, 1440]) {
      await page.setViewportSize({ width, height: 900 });
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `${label} long fields @ ${width}`).toBe(true);
    }
  }
});
