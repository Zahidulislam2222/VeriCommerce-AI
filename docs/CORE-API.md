# Evidence API

API version **0.2.0**. The current release is `20261018-phase5-02`, following quota release `20261018-phase3-01`, the integrated expansion `20261018-phase1-01` and the verified 2026-10-15 evidence release. Its 228 artifact hashes, eight HTTPS checks and four healthy services passed verification. The preceding expansion passed 46 live browser checks; current development-store API flows were checked separately. These integrated releases carry phases 1–5 features; they are not five separately demonstrated phase deployments. The current deployment passed populated pre/post-migration restoration across 26 tables. An earlier authenticated encrypted recovery belongs to the dated `phase3-01` snapshot. Actual current-release rollback/forward preserved three approved drafts and persistent volumes, followed by 228-artifact parity and eight HTTPS checks. Separate Azure, AWS and GCP smoke contracts are documented with their limited scope in [release evidence](RELEASE-VERIFICATION.md).

All routes use same-origin `/api`; the machine-readable schema is `/api/openapi.json`. Interactive Swagger assets are disabled to retain the self-hosted CSP. The application supports temporary isolated browser workspaces and persistent membership-based account workspaces.

POST, PUT, PATCH and DELETE require an exact configured Origin; mutations use JSON, with bodyless DELETE also accepted. The signed Shopify webhook has its own raw-body verification boundary. Send opaque HttpOnly/Secure/SameSite cookies through `credentials:'include'`. Browser clients let the browser provide Origin. Once a workspace is selected, send `X-Workspace-ID` with its returned identifier to reject stale-tab requests with 409. Identity still comes from verified cookies and membership. Never copy a session token into source or logs. Fixed legacy metadata identifiers remain for compatibility.

## Start a workspace

From an authorized same-origin browser:

```js
const sessionResponse = await fetch('/api/session', {
  method: 'POST',
  credentials: 'include',
  headers: { 'Content-Type': 'application/json' },
  body: '{}'
});
if (!sessionResponse.ok) throw new Error('Workspace access failed');
const { tenant_id } = await sessionResponse.json();
const response = await fetch('/api/products', {
  credentials: 'include',
  headers: { 'X-Workspace-ID': tenant_id }
});
if (!response.ok) throw new Error('Product request failed');
const { products } = await response.json();
```

`POST /api/session {}` creates a seeded temporary workspace or resumes valid access. Response includes `tenant_id`, `expires_at`, store name and compatibility metadata. `GET /api/session` returns the selected workspace or an access error. The default temporary lifetime is 12 hours. Account workspaces return `demo:false` and `expires_at:null`; their data survives logout and account-session expiry.

## Accounts and permissions

| Route | Request / behavior |
|---|---|
| `GET /api/auth/me` | Authentication state, memberships, active tenant and capabilities |
| `POST /api/auth/register` | `{email,password,tenant_name?}`; creates an empty persistent workspace and session |
| `POST /api/auth/login` | `{email,password}`; creates an account session |
| `POST /api/auth/logout` | `{}`; revokes the current account session |
| `POST /api/auth/tenants` | `{name}`; creates and selects a workspace |
| `POST /api/auth/tenant/select` | `{tenant_id}`; requires current membership |
| `GET /api/auth/members` | Owner-only member list |
| `POST /api/auth/members` | Owner adds an already registered `{email,role}`; no invitation email |
| `PATCH /api/auth/members` | Owner changes `{account_id,role}`; `role:null` removes membership |

Passwords contain 12–128 characters and use salted scrypt hashes. Registration can be disabled. Email verification and automated password recovery are absent; the last owner cannot be removed or demoted.

| Role | Capabilities |
|---|---|
| owner | Read, edit, approve, manage members and Shopify connection |
| reviewer | Read and approve |
| editor | Read and edit |
| viewer | Read |

Temporary workspaces retain read/edit/draft-approval capabilities. Image, relationship and benchmark review approvals require an identified account as well as approval permission. Protected mutations recheck membership inside the tenant transaction.

Bind each group of protected requests to the selected workspace, require the verified response scope and clear old private UI state when identity/scope changes. A workspace-change409 has structured `detail.code:workspace_changed`; other409 responses can describe stale evidence. Reload identity/current evidence before making another decision. Do not automatically replay an approval, upload, connector request or another mutation after a timeout or scope change; first reconcile its actual outcome.

## Reading contracts

| Route | Response |
|---|---|
| `GET /api/overview` | Product/source/passage/draft/approved/queued counts and retrieval status |
| `GET /api/products` | `{products:[...]}` |
| `GET /api/sources` | `{sources:[...]}` |
| `GET /api/drafts` | `{drafts:[...]}` |
| `GET /api/jobs/{id}` | `{job:{...}}` |
| `GET /api/jobs` | `{jobs:[...]}` |
| `GET /api/graph?product_id=...` | `{nodes,edges,impact}` |
| `GET /api/audit` | `{events:[{id,action,entity_id,created_at}]}` |
| `GET /api/evaluations` | `{evaluations:[...]}`, newest first |

Products retain `id,name,category,subtitle,image,alt,sku,color,description` and current `claims`, with optional `parent_product_id` for variant association. Claims include `label,value,sourceId,passage,page,passage_id,source_version`. Source records include `id,name,type,version,date,revision_id,content_hash,passage_count`. Retired products and deleted sources are excluded from current evidence.

Jobs/drafts/passages/revisions use UUID IDs; product/source IDs are catalog strings. A valid ID belonging to another workspace returns404. Empty lists are valid.

## Search and answers

`POST /api/search` and `POST /api/answers` accept:

```json
{"query":"What is Forma One's battery life?","product_id":"forma-one","limit":5}
```

`product_id` and `limit` are optional. The typed configuration owns default/maximum result counts. Search returns `{method,results,retrieval}`; method is `lexical` or `hybrid_rrf`. Each result is a citation plus score.

Citation fields: `passage_id,product_id,product_name,source_id,source_name,source_version,revision_id,page,text`.

Answers return `{answer,abstained,method,citations,retrieval}`. Method is `extractive_source_quotes` or `unsupported_abstention`. Text quotes retrieved passages with source labels; it is not an open-ended language-model completion. No relevant evidence means abstention. A relevant quote may not answer every part of a question.

Retrieval metadata reports method, model/revision and fallback status. Cached CPU embeddings rank lexical candidates; dense similarity alone cannot authorize an answer. Missing optional cache yields explicit lexical fallback. Exact recognized SKU entities restrict eligible products before embedding, including child variants selected through their parent.

`POST /api/context` accepts `{query,method,product_id?,sku?,color?,category?,budget_chars?}`. Methods are `keyword`, `dense`, `hybrid`, and deterministic `rerank`; unavailable model-dependent methods return `available:false`. Exact constraints apply before model exposure. The response contains ranked results and a context trace: selected/excluded passage IDs, budget/usage, eligible products, authority, snapshot hash, request constraints and cache key. This inspector is distinct from the legacy answer route.

`POST /api/snapshot {"product_id":"forma-one"}` returns a versioned hash and exact current citations; an empty object snapshots all current workspace evidence. `GET /api/capabilities` reports upload limits/formats, retrieval methods/context budget and frozen benchmark metadata.

## Ingestion and durable work

`POST /api/ingestions` takes `{products:[...],sources:[...]}`. Source fields are `id,name,version,type,date`; product claims contain `label,value,sourceId,passage,page`. A source replacement supplies all its current passages through product claims. Unknown references and duplicate IDs fail validation. Supplied records are updated; absence is not deletion.

Exact replay is idempotent. Changed source content creates an immutable revision and invalidates dependent drafts. Product metadata changes also invalidate that product's drafts.

`POST /api/drafts {"product_id":"forma-one","kind":"faq"}` queues evidence-template drafting. `kind` is `description` or `faq`, defaulting to description. Current contradictions and curated critical claims block drafting. Ingestion and drafting return HTTP202:

```json
{"job":{"id":"UUID","kind":"ingest","status":"queued","attempts":0,
"created_at":"ISO8601","result":null,"error":null}}
```

Poll `GET /api/jobs/{id}` until `succeeded` or `failed`, then refresh reading endpoints. Intermediate states are `queued` and `running`. Draft success result is `{draft_id}`; ingestion result contains `products_upserted,sources_changed,sources_unchanged,stale_drafts`. Workers use bounded leases/retries, source-generation fencing and fair tenant scanning. `POST /api/jobs/{id}/retry {}` accepts only failed jobs within their original attempt budget; it cannot replay successful/running jobs or restore deleted uploads.

## Uploads, revisions and deletion

`POST /api/uploads` accepts `{product_id?,source_id,filename,media_type,content_base64,version}` and returns an upload identifier, duplicate flag and durable job. JSON/CSV catalogs can initialize an empty workspace. PDF and static PNG/JPEG/WebP inputs require an existing active product. `GET /api/uploads` lists records; `GET /api/uploads/{id}/content` serves only successfully validated raster bytes under private/no-store headers.

CSV column names/order come from `/api/capabilities`. The default binary limit is 1 MiB; storage, page, pixel, extracted-text, parser-memory, result-size and runtime limits are separately configured. The actual live path accepted a 1 MiB upload, completed worker processing and returned a cited answer;1 MiB plus one byte returned 413. Archives/HTML, active/encrypted PDFs, MIME mismatches and animated images are rejected. Parsing runs in a disposable resource-limited process using bounded JSON IPC. Scanned/empty PDFs and images report OCR/observation requirements; no OCR or visual technical-attribute extraction is claimed.

`GET /api/sources/{id}/versions` returns immutable revision metadata and passages. `GET /api/sources/{id}/impact` returns revision IDs, affected relationships/products/drafts and a snapshot hash. `DELETE /api/sources/{id}` excludes current evidence, invalidates dependent drafts/relations/image approvals and clears associated uploaded original bytes. Historical extracted passages, citations and backups can remain. Manual imports cannot overwrite connector-owned identifiers or assign their provider-owned parent association.

## Approval and export

A draft has `id,product_id,product_name,text,method,status,created_at,approved_at,citations`. States are `draft`, `approved` and `stale`; method is `extractive_evidence_template`.

`POST /api/drafts/{id}/approve {}` returns `{draft}` only while referenced sources/product state remain current. Treat a 409 conflict as a need to reload and generate/review again; never retry approval blindly.

`GET /api/drafts/{id}/export` downloads JSON containing compatibility metadata and the approved draft. The draft includes product ID/name and citations; the envelope does not contain a full product object. Unapproved/stale exports return409. Export does not mutate any external store. This API does not accept freeform edited draft text.

## Graph and measured evaluation

Graph nodes have `id,type,label,status?`; edges have `source,target,relation`; impact has `stale_drafts,current_source_revisions`. Relations are `has_evidence,documented_by,derived_from,supersedes`.

`POST /api/evaluations {}` runs the maintained ten-case generated regression set and persists actual results: `id,created_at,dataset_version,method,total,passed,retrieval_recall_at_k,abstention_accuracy,cases,retrieval`. Each case reports query, expected source/abstention and actual retrieved IDs/abstention/pass result. This set is not an independent general-quality benchmark.

The additive review API exposes `GET /api/intelligence/{product_id}` for normalized contradictions, blocked claims, temporal relations, image reviews, current drafts and deterministic Product/ProductGroup JSON-LD with field provenance. `POST /api/relations {subject_id,predicate,object_id,revision_id}` proposes `compatible_with`, `documented_by`, `has_variant` or `supported_by`; `POST /api/relations/{id}/approve {}` checks current supporting evidence before approval.

`POST /api/image-reviews {upload_id,purpose,observation,alt,function?}` records visual observations separately from verified attributes. Decorative images require empty alt; informative/functional images require alt; functional images also require an action/destination. `POST /api/image-reviews/{id}/approve {}` rechecks the current image and records the reviewer. These controls support review; they do not establish accessibility certification.

`GET /api/benchmark-dataset` returns the frozen synthetic catalog/questions/images with separate review states. `POST /api/benchmark-reviews {dataset_hash,question_ids,image_ids,decision,notes}` records exact item decisions (`approved` or `needs_changes`). `POST /api/benchmarks {}` runs the64-question test split across available methods; `GET /api/benchmarks` returns persisted reports. See [evaluation limitations](DATA-MODELS-EVALUATION.md).

## Read-only Shopify connector

These routes require an owner account and explicit provider configuration. Real OAuth installation with exactly `read_products` and a successful development-store sync were verified: 23 parent products and 38 variants became 61 current product records, with 23 sources and 206 passages. Actual parent/SKU/color constraints selected the intended child evidence and returned a cited answer. Two subsequently received real `products/update` events passed HMAC verification and were durably applied. An explicitly approved temporary title change and restoration through Shopify Admin updated and restored parent/child records; a following full sync matched every canonical product record, with no duplicates.

In the observed store flow, a three-citation FAQ returned 409 for export before approval, then approval and export returned 200 with unchanged draft text and `published:false`. The owner-delegated agent inspected and approved this test draft; no independent human validation or application publishing is claimed. The separate webhook test made two owner-approved title saves through Shopify Admin, restored the original title, and made zero application product-write calls. A draft based on the earlier revision then returned 409 on export.

| Route | Behavior |
|---|---|
| `GET /api/shopify` | Configuration/connection/scopes, sync history and receipt health |
| `POST /api/shopify/connect` | `{shop}` using its exact Shopify domain; returns authorization URL |
| `GET /api/shopify/callback` | Signed, expiring, single-use OAuth state and verified shop identity |
| `POST /api/shopify/sync` | `{}`; bounded paginated read-only catalog import |
| `GET /api/shopify/export` | Imported normalized records; never credentials |
| `POST /api/shopify/disconnect` | `{}`; removes locally stored tokens and stops local connection use |
| `DELETE /api/shopify/data` | Retires imported current evidence; historical records may remain |
| `POST /api/shopify/webhook` | Raw-body HMAC, durable duplicate-safe receipts and ordered updates/deletes/uninstall |

Only `read_products` is permitted. Tokens are encrypted and bound to workspace/shop, with expiry/refresh handling. An actual expired-token refresh retained exactly `read_products`; rotated credentials were saved in protected private recovery storage. Stable child products carry variant SKU and authoritative Color options; removed variants are retired. Disconnect is a local credential action, not a claim that remote installation/scopes were revoked. No product mutations or publishing routes exist.

## Errors and operational endpoints

Errors use `{"detail":...}`; FastAPI validation details may be structured. Handle401 (expired/missing access),403 (origin/permission),404 (missing/scoped entity),409 (stale/workspace conflict),413 (body limit),415 (media),422 (schema),429 (rate/quota) and 503/504 (unavailable/bounded provider timeout) explicitly. Inspect returned details rather than assuming every429 is temporary per-second throttling. Do not display raw server tracebacks.

`GET /api/healthz` reports process liveness; `GET /api/version` reports configured API metadata. `GET /api/readyz` checks database, restricted runtime role/RLS and truthful retrieval status. Keyword fallback can be ready. Readiness alone does not prove all browser journeys work.

Local module: `vericommerce_core.main:app`; commands/configuration are in [setup](SETUP.md) and [configuration](CONFIGURATION.md). The OpenAPI schema and behavioral tests are authoritative if a prose example becomes stale.
