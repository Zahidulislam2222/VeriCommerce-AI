import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { URL } from 'node:url';

test('public navigation points to maintained pages or existing application/media routes', async () => {
  const navigation = JSON.parse(await readFile(new URL('../src/data/public-navigation.json', import.meta.url), 'utf8'));
  const pages = JSON.parse(await readFile(new URL('../src/data/public-pages.json', import.meta.url), 'utf8'));
  const allowed = new Set([...pages.pages.map((page) => page.path), '/engine', '/workspace', '/THIRD-PARTY-NOTICES.txt']);
  assert.deepEqual(navigation.groups.map((group) => group.label), ['Product', 'Company', 'Resources', 'Legal']);
  for (const link of [...navigation.primary, ...navigation.groups.flatMap((group) => group.links)]) {
    assert.ok(link.label.trim());
    assert.ok(allowed.has(link.href), `Unimplemented public navigation destination: ${link.href}`);
    assert.ok(!link.href.includes('#'));
  }
  assert.ok(allowed.has(navigation.workspacePath));
});
