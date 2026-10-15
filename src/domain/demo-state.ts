import type { Product, Source } from '../types';

export function filterProducts(products: Product[], query: string, category: string): Product[] {
  const normalized = query.trim().toLocaleLowerCase();
  return products.filter((product) =>
    (category === 'all' || product.category === category) &&
    `${product.name} ${product.category} ${product.sku}`.toLocaleLowerCase().includes(normalized),
  );
}

export function parseApprovals(raw: string | null, allowedIds: string[]): string[] {
  if (!raw) return [];
  try {
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return [...new Set(parsed.filter((value): value is string =>
      typeof value === 'string' && allowedIds.includes(value),
    ))];
  } catch { return []; }
}

export function makeDraftExport(product: Product, sources: Source[], approved: boolean) {
  return {
    catalogOrigin: 'generated_product_records',
    published: false,
    product: { id: product.id, name: product.name, sku: product.sku },
    draft: product.draft,
    approvalScope: 'browser_only',
    approved,
    evidence: product.claims.map((claim) => ({ ...claim, source: sources.find((source) => source.id === claim.sourceId) })),
  };
}
