# Evidence API

API version **0.2.0**. All routes use same-origin `/api`; the machine-readable schema is `/api/openapi.json`. Interactive Swagger assets are disabled to retain the self-hosted CSP. The API provides temporary isolated browser workspaces, not persistent account authentication.

POST requires an exact configured Origin and JSON content. After creation, send the opaque HttpOnly/Secure/SameSite cookie through `credentials:'include'`. Browser clients let the browser provide Origin. Never copy a session token into source or logs. Fixed legacy metadata identifiers remain for compatibility; they do not change the current product's capability boundary.

## Start a workspace

From an authorized same-origin browser:

```js
await fetch('/api/session', {
  method: 'POST',
  credentials: 'include',
  headers: { 'Content-Type': 'application/json' },
  body: '{}'
});
const response = await fetch('/api/products', { credentials: 'include' });
if (!response.ok) throw new Error('Product request failed');
const { products } = await response.json();
```

`POST /api/session {}` creates a seeded workspace or resumes a valid cookie. Response includes `tenant_id`, `expires_at`, store name and compatibility metadata. `GET /api/session` returns the current session or401. Configured lifetime is12 hours. No login, password recovery, membership, upload or Shopify routes are part of this release.

## Reading contracts

| Route | Response |
|---|---|
| `GET /api/overview` | Product/source/passage/draft/approved/queued counts and retrieval status |
| `GET /api/products` | `{products:[...]}` |
| `GET /api/sources` | `{sources:[...]}` |
| `GET /api/drafts` | `{drafts:[...]}` |
| `GET /api/jobs/{id}` | `{job:{...}}` |
| `GET /api/graph?product_id=...` | `{nodes,edges,impact}` |
| `GET /api/audit` | `{events:[{id,action,entity_id,created_at}]}` |
| `GET /api/evaluations` | `{evaluations:[...]}`, newest first |

Products retain `id,name,category,subtitle,image,alt,sku,color,description` and current `claims`. Claims include `label,value,sourceId,passage,page,passage_id,source_version`. Source records include `id,name,type,version,date,revision_id,content_hash,passage_count`.

Jobs/drafts/passages/revisions use UUID IDs; product/source IDs are catalog strings. A valid ID belonging to another workspace returns404. Empty lists are valid.

## Search and answers

`POST /api/search` and `POST /api/answers` accept:

```json
{"query":"What is Forma One's battery life?","product_id":"forma-one","limit":5}
```

`product_id` and `limit` are optional. The typed configuration owns default/maximum result counts. Search returns `{method,results,retrieval}`; method is `lexical` or `hybrid_rrf`. Each result is a citation plus score.

Citation fields: `passage_id,product_id,product_name,source_id,source_name,source_version,revision_id,page,text`.

Answers return `{answer,abstained,method,citations,retrieval}`. Method is `extractive_source_quotes` or `unsupported_abstention`. Text quotes retrieved passages with source labels; it is not an open-ended language-model completion. No relevant evidence means abstention. A relevant quote may not answer every part of a question.

Retrieval metadata reports method, model/revision and fallback status. Cached CPU embeddings rank lexical candidates; dense similarity alone cannot authorize evidence. Missing optional cache yields explicit lexical fallback.

## Ingestion and durable work

`POST /api/ingestions` takes `{products:[...],sources:[...]}`. Source fields are `id,name,version,type,date`; product claims contain `label,value,sourceId,passage,page`. A source replacement supplies all its current passages through product claims. Unknown references and duplicate IDs fail validation. Supplied records are updated; absence is not deletion.

Exact replay is idempotent. Changed source content creates an immutable revision and invalidates dependent drafts. Product metadata changes also invalidate that product's drafts.

`POST /api/drafts {"product_id":"forma-one"}` queues evidence-template drafting. Ingestion and drafting return HTTP202:

```json
{"job":{"id":"UUID","kind":"ingest","status":"queued","attempts":0,
"created_at":"ISO8601","result":null,"error":null}}
```

Poll `GET /api/jobs/{id}` until `succeeded` or `failed`, then refresh reading endpoints. Intermediate states are `queued` and `running`. Draft success result is `{draft_id}`; ingestion result contains `products_upserted,sources_changed,sources_unchanged,stale_drafts`. Workers use bounded leases/retries with attempt fencing. No user-triggered retry endpoint is currently exposed.

## Approval and export

A draft has `id,product_id,product_name,text,method,status,created_at,approved_at,citations`. States are `draft`, `approved` and `stale`; method is `extractive_evidence_template`.

`POST /api/drafts/{id}/approve {}` returns `{draft}` only while referenced sources/product state remain current. Treat a409 conflict as a need to reload and generate/review again; never retry approval blindly.

`GET /api/drafts/{id}/export` downloads JSON containing compatibility metadata and the approved draft. The draft includes product ID/name and citations; the envelope does not contain a full product object. Unapproved/stale exports return409. Export does not mutate any external store. This API does not accept freeform edited draft text.

## Graph and measured evaluation

Graph nodes have `id,type,label,status?`; edges have `source,target,relation`; impact has `stale_drafts,current_source_revisions`. Relations are `has_evidence,documented_by,derived_from,supersedes`.

`POST /api/evaluations {}` runs the maintained ten-case generated regression set and persists actual results: `id,created_at,dataset_version,method,total,passed,retrieval_recall_at_k,abstention_accuracy,cases,retrieval`. Each case reports query, expected source/abstention and actual retrieved IDs/abstention/pass result. This set is not an independent general-quality benchmark.

## Errors and operational endpoints

Errors use `{"detail":...}`; FastAPI validation details may be structured. Handle401 (expired/missing access),403 (origin),404 (missing/scoped entity),409 (stale/conflict),413 (body limit),422 (schema) and429 (rate/quota) explicitly; inspect the returned detail rather than assuming every429 is temporary per-second throttling. Do not display raw server tracebacks.

`GET /api/healthz` reports process liveness. `GET /api/readyz` checks database, restricted runtime role/RLS and truthful retrieval status. Keyword fallback can be ready. Readiness alone does not prove all browser journeys work.

Local module: `vericommerce_core.main:app`; commands/configuration are in [setup](SETUP.md) and [configuration](CONFIGURATION.md). The OpenAPI schema and behavioral tests are authoritative if a prose example becomes stale.
