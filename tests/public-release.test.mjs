import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { URL } from 'node:url';
import ts from 'typescript';

const files = ['site.json', 'core.json', 'public-navigation.json', 'public-pages.json'];
const storageIdentifiers = new Set(['vc_demo', 'vericommerce.demo.approvals.v1']);
const prohibited = /\b(?:demo|demonstration|preview|pilot|prototype|sandbox|fictional|sample|illustrative)\b/i;

test('maintained public copy uses current capabilities and roadmap framing', () => {
  function check(value, location) {
    if (Array.isArray(value)) value.forEach((item, index) => check(item, `${location}[${index}]`));
    else if (value && typeof value === 'object') Object.entries(value).forEach(([key, item]) => check(item, `${location}.${key}`));
    else if (typeof value === 'string' && !storageIdentifiers.has(value)) assert.doesNotMatch(value, prohibited, location);
  }
  for (const file of files) check(JSON.parse(readFileSync(new URL(`../src/data/${file}`, import.meta.url))), file);
});

test('research roadmap contains milestones without invented performance values', () => {
  const catalog = JSON.parse(readFileSync(new URL('../src/data/demo.json', import.meta.url)));
  assert.equal(catalog.lab.milestones.length, 3);
  assert.equal(catalog.lab.metrics, undefined);
  assert.ok(catalog.lab.caption.includes('No comparative model-quality percentages'));
});

test('visible JSX text and accessibility labels retain professional release wording', () => {
  function walk(directory) {
    return readdirSync(directory, { withFileTypes: true }).flatMap((entry) =>
      entry.isDirectory() ? walk(join(directory, entry.name)) : [join(directory, entry.name)]);
  }
  for (const filename of walk('src').filter((name) => name.endsWith('.tsx'))) {
    const source = ts.createSourceFile(filename, readFileSync(filename, 'utf8'), ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
    function visit(node) {
      if (ts.isJsxText(node)) assert.doesNotMatch(node.text, prohibited, filename);
      if (ts.isJsxAttribute(node) && ['aria-label', 'title', 'alt', 'placeholder'].includes(node.name.getText(source))
          && node.initializer && ts.isStringLiteral(node.initializer)) {
        assert.doesNotMatch(node.initializer.text, prohibited, filename);
      }
      ts.forEachChild(node, visit);
    }
    visit(source);
  }
});
