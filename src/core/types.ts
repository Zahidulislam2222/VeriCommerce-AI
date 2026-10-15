export type CoreView = 'overview' | 'ask' | 'evidence' | 'drafts' | 'import' | 'lab' | 'activity';
export interface Evidence {
  passage_id: string; product_id: string; product_name: string; source_id: string;
  source_name: string; source_version: string; page: string; text: string; score?: number;
}
export interface CoreProduct {
  id: string; name: string; category: string; sku: string; description: string;
  image?: string; passage_count?: number;
  claims: { label: string; value: string; sourceId: string; passage: string; page: string; passage_id: string; source_version: string }[];
}
export interface CoreSource {
  id: string; name: string; version: string; type: string; content_hash?: string;
  passage_count?: number; passages?: Evidence[];
}
export interface CoreDraft {
  id: string; product_id: string; product_name: string; text: string; status: 'draft' | 'approved' | 'stale';
  citations: Evidence[]; created_at: string; approved_at: string | null;
}
export interface Overview {
  products: number; sources: number; passages: number; drafts: number;
  approved_drafts: number; queued_jobs: number;
  retrieval: { status: string; method: string; model: string | null; revision: string | null; reason?: string };
}
export interface Answer { answer: string; abstained: boolean; method: string; citations: Evidence[] }
export interface Job { id: string; status: string; kind: string; result?: Record<string, unknown>; error?: string | null }
export interface AuditEvent { id: string; action: string; created_at: string; entity_id: string }
export interface Evaluation {
  cases: { id: string; query: string; expected_source_id: string | null; passed: boolean; expected_abstain: boolean; actual_abstain: boolean; retrieved_source_ids: string[] }[];
  total: number; passed: number; retrieval_recall_at_k: number; abstention_accuracy: number;
  method: string; created_at: string; dataset_version: string;
}
