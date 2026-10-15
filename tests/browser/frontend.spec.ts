import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { readFile } from 'node:fs/promises';

test('landing, evidence, FAQ and research navigation work', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto('/');
  await expect(page.getByRole('heading', { level: 1 })).toContainText('Real evidence.');
  await page.getByRole('button', { name: 'Connect', exact: true }).click();
  await page.getByRole('button', { name: /Finish Chalk/ }).click();
  await expect(page.locator('.passage-card')).toContainText('Do not describe the full product as plastic-free.');
  await page.getByRole('button', { name: 'What can I do with VeriCommerce AI?' }).click();
  await expect(page.locator('#faq-0')).toContainText('records work on the server');
  await page.getByRole('button', { name: 'Explore the research roadmap' }).click();
  await expect(page).toHaveURL(/\/workspace#lab$/);
  await expect(page.getByRole('heading', { level: 1 })).toContainText('A place to question');
  await expect(page.locator('.research-milestone')).toHaveCount(3);
  await expect(page.locator('.chart-row')).toHaveCount(0);
  expect(errors).toEqual([]);
});

test('catalog search, filters, empty state and home navigation work', async ({ page }) => {
  await page.goto('/workspace#catalog');
  await expect(page.locator('.catalog-card')).toHaveCount(3);
  await page.getByRole('searchbox', { name: 'Search products' }).fill('verdant');
  await expect(page.locator('.catalog-card')).toHaveCount(1);
  await page.getByRole('button', { name: 'Audio', exact: true }).click();
  await expect(page.getByText('No products match that search.')).toBeVisible();
  await page.getByRole('button', { name: 'Clear search', exact: true }).click();
  await expect(page.locator('.catalog-card')).toHaveCount(3);
  await page.getByRole('button', { name: 'Back to the platform', exact: true }).last().click();
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole('heading', { level: 1 })).toBeFocused();
});

test('evidence inspection returns to review, approval persists, export is honest', async ({ page }) => {
  await page.goto('/workspace#drafts');
  await page.getByRole('button', { name: 'Review draft', exact: true }).first().click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await page.getByRole('button', { name: /Battery life Up to 40 hours/ }).click();
  await expect(page.getByRole('dialog')).toContainText('active noise cancellation disabled');
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).toBeVisible();
  await expect(page.getByRole('dialog')).toContainText('A quieter kind of everyday.');
  await page.getByRole('button', { name: /Battery life Up to 40 hours/ }).click();
  await page.getByRole('button', { name: 'Return to the draft', exact: true }).click();
  await expect(page.getByRole('dialog')).toContainText('A quieter kind of everyday.');
  await page.getByRole('button', { name: 'Approve draft', exact: true }).click();
  await expect(page.getByRole('status')).toContainText('Nothing was published.');
  await expect(page.locator('.draft-status').first()).toHaveText('Approved in this browser');
  await page.reload();
  await expect(page.locator('.draft-status').first()).toHaveText('Approved in this browser');
  const downloadPromise = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Export draft', exact: true }).first().click();
  const download = await downloadPromise;
  const path = await download.path();
  const data = JSON.parse(await readFile(path!, 'utf8'));
  expect(data.catalogOrigin).toBe('generated_product_records');
  expect(data.published).toBe(false);
  expect(data.evidence[0].source.id).toBe('forma-manual');
});

test('native dialog traps keyboard focus and restores the trigger', async ({ page }) => {
  await page.goto('/workspace#catalog');
  const card = page.locator('.catalog-card').first();
  await card.click();
  await expect(page.getByRole('button', { name: 'Close dialog', exact: true })).toBeFocused();
  for (let i = 0; i < 9; i++) {
    await page.keyboard.press('Tab');
    expect(await page.evaluate(() => document.querySelector('dialog')?.contains(document.activeElement))).toBe(true);
  }
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await expect(card).toBeFocused();
});

test('reduced motion is static and all primary widths avoid overflow', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'no-preference' });
  await page.goto('/');
  await expect(page.locator('video')).toHaveCount(1);
  await expect(page.locator('html')).toHaveClass(/lenis/);
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await expect(page.locator('video')).toHaveCount(0);
  await expect(page.locator('html')).not.toHaveClass(/lenis/);
  for (const width of [360, 375, 768, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  }
  await page.goto('/workspace#evidence');
  for (const width of [360, 375, 768, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  }
});

test('landing and workspace have no serious or critical accessibility violations', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  for (const route of ['/', '/workspace#catalog', '/workspace#drafts', '/workspace#lab']) {
    await page.goto(route);
    const results = await new AxeBuilder({ page }).analyze();
    const blockers = results.violations.filter((item) => ['critical', 'serious'].includes(item.impact ?? ''));
    expect(blockers.map((item) => ({ id: item.id, impact: item.impact, nodes: item.nodes.map((node) => ({ target: node.target, summary: node.failureSummary })) }))).toEqual([]);
  }
});

test('captures a complete responsive design for visual review', async ({ page }, testInfo) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/');
  await page.evaluate(() => document.fonts.ready);
  for (const image of await page.locator('img').all()) {
    await image.scrollIntoViewIfNeeded();
    await expect.poll(() => image.evaluate((node: HTMLImageElement) => node.complete && node.naturalWidth > 0)).toBe(true);
  }
  await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'instant' }));
  await page.screenshot({ path: `memory/screenshots/landing-${testInfo.project.name}-ready.png`, fullPage: true });
  await page.goto('/workspace');
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({ path: `memory/screenshots/workspace-${testInfo.project.name}-ready.png`, fullPage: true });
});

test('hero film plays, pauses, and stops offscreen while smooth scrolling is enabled', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'no-preference' });
  await page.goto('/');
  const video = page.locator('video');
  await expect(page.locator('html')).toHaveClass(/lenis/);
  await expect.poll(() => video.evaluate((node: HTMLVideoElement) => node.readyState)).toBeGreaterThanOrEqual(2);
  await expect.poll(() => video.evaluate((node: HTMLVideoElement) => node.paused)).toBe(false);
  await page.getByRole('button', { name: 'Pause hero motion', exact: true }).click();
  await expect.poll(() => video.evaluate((node: HTMLVideoElement) => node.paused)).toBe(true);
  await page.getByRole('button', { name: 'Play hero motion', exact: true }).click();
  await expect.poll(() => video.evaluate((node: HTMLVideoElement) => node.paused)).toBe(false);
  await page.locator('#process').scrollIntoViewIfNeeded();
  await expect.poll(() => video.evaluate((node: HTMLVideoElement) => node.paused)).toBe(true);
});
