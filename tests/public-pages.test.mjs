import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { URL } from 'node:url';

const data = JSON.parse(readFileSync(new URL('../src/data/public-pages.json', import.meta.url)));
const nginx = readFileSync(new URL('../infra/core/nginx.conf', import.meta.url), 'utf8');

test('fourteen unique public routes have complete maintained content and exact server locations', () => {
  assert.equal(data.pages.length, 14);
  assert.equal(new Set(data.pages.map((page) => page.path)).size, 14);
  for (const page of data.pages) {
    assert.ok(page.title && page.accent && page.description && page.sections.length);
    assert.ok(nginx.includes(`location = ${page.path} {`), page.path);
    assert.equal(new Set(page.sections.map((section) => section.id)).size, page.sections.length);
    assert.ok(page.sections.every((section) => section.body?.length || section.items?.length));
    for (const reference of page.references ?? []) {
      const url = new URL(reference.href);
      assert.equal(url.protocol, 'https:');
      assert.ok(['commission.europa.eu', 'www.ftc.gov', 'oag.ca.gov', 'www.w3.org'].includes(url.hostname));
    }
  }
});

test('contact uses owner-confirmed public details and pricing does not invent paid checkout', () => {
  assert.equal(data.contact.email, 'muhammadzahidulislam2222@gmail.com');
  assert.equal(data.contact.operator, 'Zahidul Islam');
  assert.equal(data.pages.find((page) => page.path === '/pricing').plans[0].price, '$0');
  assert.ok(!JSON.stringify(data).match(/SOC.?2 certified|100% secure|GDPR certified|Stripe|street address/i));
});
