export interface Claim { label: string; value: string; sourceId: string; passage: string; page: string }
export interface Product { id: string; name: string; category: string; subtitle: string; image: string; alt: string; sku: string; status: string; color: string; description: string; claims: Claim[]; draft: string }
export interface Source { id: string; name: string; version: string; type: string; date: string }
export type WorkspaceView = 'overview' | 'catalog' | 'evidence' | 'drafts' | 'lab';
