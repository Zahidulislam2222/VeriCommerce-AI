import site from './data/site.json';
import fixture from './data/demo.json';
import type { Product, Source } from './types';

export const content = site;
export const products: Product[] = fixture.products;
export const sources: Source[] = fixture.sources;
export const demo = fixture;

const sourceIds = new Set(sources.map((source) => source.id));
if (new Set(products.map((product) => product.id)).size !== products.length ||
    products.some((product) => !product.name || !product.draft || !product.image.startsWith('/images/') ||
      product.claims.some((claim) => !sourceIds.has(claim.sourceId) || !claim.passage))) {
  throw new Error('Demo data must have unique products, local images, and complete source lineage.');
}
