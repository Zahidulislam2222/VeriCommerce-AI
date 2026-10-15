import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { URL } from 'node:url';
import { filterProducts, makeDraftExport, parseApprovals } from '../src/domain/demo-state.ts';

const fixture = JSON.parse(readFileSync(new URL('../src/data/demo.json', import.meta.url), 'utf8'));

test('catalog search respects both query and category and finds exact SKUs', () => {
  assert.equal(filterProducts(fixture.products, ' FN-001 ', 'Audio')[0].id, 'forma-one');
  assert.equal(filterProducts(fixture.products, 'verdant', 'Audio').length, 0);
  assert.equal(filterProducts(fixture.products, '  VERDANT  ', 'all').length, 1);
  assert.equal(filterProducts(fixture.products, '', 'all').length, fixture.products.length);
});

test('browser approval data rejects corrupt, foreign, and duplicate identifiers', () => {
  const ids = fixture.products.map((p) => p.id);
  assert.deepEqual(parseApprovals('{invalid', ids), []);
  assert.deepEqual(parseApprovals('{"approved":true}', ids), []);
  assert.deepEqual(parseApprovals('["forma-one","forma-one","unknown",123]', ids), ['forma-one']);
});

test('export preserves evidence lineage and never claims real publication', () => {
  const exported = makeDraftExport(fixture.products[0], fixture.sources, true);
  assert.equal(exported.catalogOrigin, 'generated_product_records');
  assert.equal(exported.published, false);
  assert.equal(exported.approved, true);
  assert.ok(exported.evidence.every((claim) => claim.source?.id === claim.sourceId && claim.passage));
});

test('catalog facts refer to existing sources and preserve product family separation', () => {
  const sourceIds = new Set(fixture.sources.map((source) => source.id));
  assert.equal(new Set(fixture.products.map((p) => p.id)).size, fixture.products.length);
  assert.ok(fixture.products.every((product) => product.claims.every((claim) => sourceIds.has(claim.sourceId))));
  assert.match(fixture.products.find((p) => p.id === 'verdant-serum').claims[0].passage, /dropper/);
});

test('source hygiene prevents embedded provider URLs, model IDs, and obvious credentials', () => {
  function walk(dir) { return readdirSync(dir, { withFileTypes: true }).flatMap((item) => item.isDirectory() ? walk(join(dir, item.name)) : [join(dir, item.name)]); }
  const implementation = walk('src').filter((path) => /\.(ts|tsx)$/.test(path));
  const forbidden = [/https?:\/\//, /(?:Qwen|meta-llama|mistralai)\//i, /BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY/, new RegExp('sk' + '-(?:or-v1-)?[A-Za-z0-9]{24,}')];
  for (const path of implementation) {
    const source = readFileSync(path, 'utf8');
    assert.ok(forbidden.every((pattern) => !pattern.test(source)), path);
    if (!path.endsWith('config.ts')) assert.doesNotMatch(source, /import\.meta\.env/, path);
  }
  const example = readFileSync('.env.example', 'utf8');
  assert.match(example, /VITE_HERO_VIDEO=false/);
  assert.match(example, /TEST_BASE_URL=/);
});
