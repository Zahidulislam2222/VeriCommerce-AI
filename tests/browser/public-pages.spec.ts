import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import data from '../../src/data/public-pages.json' with { type: 'json' };

test('every public page opens directly with unique content and accessible landmarks', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  for (const route of data.pages) {
    const response = await page.goto(route.path);
    expect(response?.status()).toBe(200);
    await expect(page.locator('main h1')).toContainText(route.title);
    await expect(page.locator('main h1')).toContainText(route.accent);
    await expect(page).toHaveTitle(/VeriCommerce AI/);
    await expect(page.locator('main')).toHaveCount(1);
    await expect(page.locator('.public-footer-groups')).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    const audit = await new AxeBuilder({ page }).analyze();
    expect(audit.violations.filter((item) => ['serious', 'critical'].includes(item.impact ?? ''))
      .map((item) => ({ id: item.id, targets: item.nodes.map((node) => node.target) })), route.path).toEqual([]);
  }
  expect(errors).toEqual([]);
});

test('pricing is honest, contact links are real and legal pages cite official sources', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/pricing');
  await expect(page.locator('.pricing-card.featured .plan-price')).toHaveText('$0');
  await page.getByRole('link', { name: 'Discuss a project', exact: true }).click();
  await expect(page).toHaveURL(/\/contact$/);
  await expect(page.locator('.contact-email')).toHaveAttribute('href', /^mailto:muhammadzahidulislam2222@gmail.com\?subject=/);
  await expect(page.locator('.contact-channels > a')).toHaveCount(3);
  await expect(page.locator('form')).toHaveCount(0);
  for (const path of ['/legal/us', '/legal/eu']) {
    await page.goto(path);
    await expect(page.locator('.page-references a').first()).toHaveAttribute('href', /^https:\/\//);
    await expect(page.locator('.legal-scope-note')).toBeVisible();
  }
});

test('cookie controls clear only browser approvals and preserve unrelated browser data', async ({ page }) => {
  await page.goto('/cookies');
  await page.evaluate(() => {
    localStorage.setItem('vericommerce.demo.approvals.v1', '["forma"]');
    localStorage.setItem('public-pages-test-preserve', 'untouched');
  });
  await page.getByRole('button', { name: 'Clear browser approvals', exact: true }).click();
  await expect(page.getByRole('status')).toContainText('Server sessions and server records were not deleted.');
  expect(await page.evaluate(() => localStorage.getItem('vericommerce.demo.approvals.v1'))).toBeNull();
  expect(await page.evaluate(() => localStorage.getItem('public-pages-test-preserve'))).toBe('untouched');
});

test('public page composition remains readable at narrow widths and is captured for review', async ({ page }, testInfo) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  for (const route of ['/pricing', '/about', '/contact', '/privacy', '/legal']) {
    await page.goto(route);
    for (const width of [320, 375, 768, 1440]) {
      await page.setViewportSize({ width, height: 900 });
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `${route} at ${width}`).toBe(true);
    }
    await page.setViewportSize(testInfo.project.name === 'mobile' ? { width: 375, height: 812 } : { width: 1440, height: 1000 });
    await page.evaluate(() => document.fonts.ready);
    await page.screenshot({ path: `memory/screenshots/public-${route.slice(1)}-${testInfo.project.name}.png`, fullPage: true });
  }
});
