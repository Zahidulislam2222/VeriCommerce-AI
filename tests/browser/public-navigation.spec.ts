import { test, expect } from '@playwright/test';
import navigation from '../../src/data/public-navigation.json' with { type: 'json' };

test('public header and grouped footer expose real named destinations', async ({ page }) => {
  await page.goto('/');
  const header = page.locator('.public-header');
  for (const item of navigation.primary) {
    await expect(header.locator('a').filter({ hasText: new RegExp(`^${item.label}$`) }).first()).toHaveAttribute('href', item.href);
  }
  const footer = page.getByRole('navigation', { name: navigation.footerLabel });
  for (const group of navigation.groups) {
    for (const link of group.links) await expect(footer.getByRole('link', { name: link.label, exact: true })).toHaveAttribute('href', link.href);
  }
  await expect(page.locator('.public-footer')).toContainText('Zahidul Islam');
  expect(await footer.locator('a[href^="#"]').count()).toBe(0);
});

test('mobile menu has native keyboard access, Escape and restored focus', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto('/');
  const toggle = page.locator('.public-menu-toggle');
  await expect(toggle).toHaveAccessibleName(navigation.openMenu);
  await toggle.focus();
  await page.keyboard.press('Enter');
  await expect(toggle).toHaveAttribute('aria-expanded', 'true');
  const menu = page.getByRole('navigation', { name: navigation.mobileLabel });
  await expect(menu).toBeVisible();
  await page.keyboard.press('Tab');
  await expect(menu.getByRole('link', { name: 'Platform', exact: true })).toBeFocused();
  await page.keyboard.press('Escape');
  await expect(menu).toBeHidden();
  await expect(toggle).toBeFocused();
  await expect(toggle).toHaveAttribute('aria-expanded', 'false');
});

test('route navigation marks the active page and supports direct loading', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto('/pricing');
  await expect(page.locator('.public-desktop-nav').getByRole('link', { name: 'Pricing', exact: true })).toHaveAttribute('aria-current', 'page');
  await page.locator('.public-desktop-nav').getByRole('link', { name: 'About', exact: true }).click();
  await expect(page).toHaveURL(/\/about$/);
  await expect(page.locator('.public-desktop-nav').getByRole('link', { name: 'About', exact: true })).toHaveAttribute('aria-current', 'page');
  await page.reload();
  await expect(page.locator('main h1')).toBeVisible();
});

test('header and footer preserve responsive landing geometry and reduced motion', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/');
  for (const width of [320, 375, 768, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `public navigation at ${width}`).toBe(true);
  }
  await expect(page.locator('video')).toHaveCount(0);
  await expect(page.locator('.public-footer-groups')).toBeVisible();
});
