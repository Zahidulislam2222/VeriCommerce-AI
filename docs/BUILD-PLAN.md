# VeriCommerce AI production engineering build plan

Delivery note (2026-10-18): the owner authorized implementation and deployment of
phases 1–5. The existing frontend and bounded evidence core remain the verified
baseline. The expanded application is live; remaining phase acceptance below stays explicit. None of these five phases is declared
complete until its original exit criteria and external acceptance gates pass.
Shopify publishing and model training belong to later phases.
See [previous release evidence](RELEASE-VERIFICATION.md).

## Phases 1–5 execution ledger

The owner resumed all five phases. Expanded local source now implements accounts,
bounded uploads, read-only connector, context comparisons and content intelligence.
Current release `20261018-phase5-02` has 228 matching artifact hashes, eight HTTPS
routes and four healthy constrained services after current populated restoration
and rollback/forward; earlier encrypted off-server recovery retains its dated snapshot scope.
It follows the integrated expansion's 46 passing live
desktop/mobile checks with unchanged application code and separately verified
real-store flows. Final hosted source passed 142 backend/infrastructure, 11 domain
and 80 browser checks; quality and security both passed. The five
phases' application features are integrated; the limits below remain explicit.

The exact exit-clause audit records 33 met and one covered by the owner's
delegated agent review, out of 34 clauses. The two temporary manual store-title
saves were separately authorized verification exceptions; the app retains
read_products and makes no product-write calls. These counts do not erase the
original deployment-sequence and operational limits below.

| Phase | Verified baseline | Required expansion and acceptance evidence | Current status |
|---|---|---|---|
| 1 | Typed API/settings, migrations, PostgreSQL RLS, isolated release, health/readiness and rollback | Accounts, persistent memberships, owner/reviewer/editor/viewer authorization, two-tenant role matrix, Azure Free shell and native cloud/account eligibility inventory | Application live; role/isolation/browser gates pass; exact Azure Free reference deployed |
| 2 | Versioned JSON ingestion, fenced durable jobs, populated restoration | CSV/PDF/image ingestion with isolated bounded parsing, deletion invalidation, revision comparison, retry/dead-letter UX, 30-product/120-image/200-question family-split corpus, encrypted off-server recovery | Real 1 MiB worker import and oversize rejection pass; encrypted off-server restoration matched all26 current tables and RLS; agent review recorded |
| 3 | Dedicated app configured; local read-only OAuth/sync/webhooks and variant mapping | Encrypted tokens, persisted HMAC receipts, replay/order/tombstones, actual permitted-store sync and deterministic AWS validator | Real read_products sync imported 23 parents/38 variants; two actual HMAC-verified update events and subsequent full sync agree. Two temporary Admin title saves were separately approved and restored; app product-write calls remain zero. Eight AWS calls match local; replay/order/delete coverage also passes |
| 4 | Four-method context inspector, exact variant constraints, snapshots and measured frozen benchmark | Actual Recall@10/nDCG/abstention/latency and authenticated GCP benchmark | Four methods measured on 64 held-out synthetic questions; keyword selected for this corpus. Three actual GCP smoke checks matched the same local snapshot; temporary resources cleaned up before deadline. Cloud smoke is not held-out quality evaluation |
| 5 | Temporal relations/impact, normalized conflicts, FAQ, guarded JSON-LD and purpose-aware image review | Full current-provenance checks and accessibility-case review | Application live; actual relationship/FAQ/image approval flows pass; owner-delegated agent review recorded; human validation pending |

Frontend, backend, AI/data and infrastructure advance together against additive
API contracts. Preserve temporary isolated workspaces separately from durable
merchant accounts. Each phase retains its own deployment and evidence record;
an integrated release may contain several candidates but does not erase a missing
phase deployment or acceptance gate. Cloud fixtures/local emulation and automated
synthetic labels do not count as actual cloud deployment or independent human
review. The owner explicitly delegated dataset/accessibility review while busy;
the recorded substitution is agent review, with human validation still pending.
Remaining original-plan limits include independent human validation and five separately recorded sequential phase
deployments. Graph-versus-hybrid quality comparison and automatic backup
scheduling/retention also remain unperformed. The owner authorized agent review instead of the human gate;
the result remains labeled agent review. Provider invoice totals remain unknown
until delayed reporting settles; this does not imply zero charges.

The deployed implementation uses psycopg with hash-verified SQL migrations rather
than adding an ORM solely for the plan. Small-catalog dense vectors are evaluated
in the application after PostgreSQL tenant/current-version filtering; pgvector is
a future measured scaling option. These choices preserve the original isolation,
reproducibility and retrieval acceptance requirements.

Prepared 2026-10-15. Exactly ten phases, each delivering an integrated deployment.
This is an implementation roadmap; acceptance targets below are proposed gates,
not results already achieved.

Build a useful Shopify catalog application around a versioned evidence system,
then demonstrate retrieval, model training, controlled agents, and operational
reliability. Use the existing shared server for the persistent application and
all three clouds for bounded, useful deployments. Keep training separate from
merchant credentials and publishing privileges.

## Delivery and cost boundaries

Execution amendment (2026-10-18): after separate conspicuous warnings, the owner
approved possible AWS charges up to $0.01 and an estimated $0.05 one-time GCP
experiment with cleanup within30minutes. Retained GCP image exposure was disclosed
as up to $0.025/month if cleanup fails. These approvals are scoped exceptions to
the original zero-spend plan below, not provider-enforced hard caps or permission
for other paid services. Current native targets and supported project tags follow
the shared Portfolio Hub convention; existing resources are retained in place.

The cash budget for new services is **USD $0**. The existing server and Internet
connection are existing resources, not free infrastructure. This plan assumes
their current allocation can be reused without an upgrade; verify that first.
A permanently available, highly available production service across three clouds
cannot be promised at this budget. Deliver production engineering practices and
a measured initial release, with explicit capacity and availability limits.

Do not purchase a domain, upgrade a cloud plan, activate paid inference, rent a
GPU, add a paid backup service, or create a billable fallback. Every external
service must have an owner, allowed SKU, verified eligibility, remaining allowance,
expiry date if applicable, associated costs, and a tested shutdown procedure.
Unknown eligibility means **blocked for cloud deployment**, not assumed free.

Reading cloud inventory and preparing infrastructure plans is allowed by this
roadmap. Account signups requiring payment information, billing activation, and
potentially billable execution still require the global money warning and fresh
explicit authorization. This document is not that authorization.

If a provider cannot be used without paid exposure, continue local development
and keep its actual deployment milestone pending. Local emulation does not count
as AWS, GCP, or Azure deployment. Do not create replacement accounts to evade
eligibility limits. Export artifacts before trials expire; the server remains
the primary runtime.

## Infrastructure allocation

| Location | Planned responsibility | Cost and availability boundary |
|---|---|---|
| Existing shared VPS | Private merchant UI, API, PostgreSQL, evidence files, durable workers, small inference where feasible, monitoring | No new server purchase. Verify current spare CPU/RAM/disk, ownership, backup destination and existing tenant health before allocating. |
| Azure Static Web Apps Free | Sanitized interactive reference UI and evaluation reports | Actual Azure deployment, with synthetic fixtures only. No merchant credentials or private data in the static bundle. Free plan has no SLA and is positioned for personal projects. |
| AWS Lambda Event Function | Deterministic evidence-manifest and draft/schema validation worker | Authenticated invocation, tiny payloads, no public unauthenticated endpoint, no model serving. Prefer an eligible non-billable Free plan; otherwise leave deployment pending unless zero-charge use can be established. |
| GCP Cloud Run | Disposable CPU retrieval benchmark service against an immutable sanitized snapshot | Request-based, minimum instances zero, low concurrency and maximum instances, authenticated access, no production database dependency. Eligible non-billable trial is preferred; never auto-upgrade it. |
| Local PC and permitted free notebook runtime | Dataset labeling, training, vision batches, experiments, release builds, encrypted off-server backups | Inspect actual hardware first. Free notebook availability is opportunistic; no paid compute fallback. Do not use notebook runtimes as production servers. |
| Hugging Face Hub | Permitted datasets, adapters, dataset/model cards and reproducibility artifacts | Use verified free allowances. Keep private merchant data off public repositories; upload only after permissions and artifact review. |

AWS currently documents a new-customer Free plan lasting up to six months or
credit exhaustion; existing/prior customers are ineligible. Lambda Event
Functions list a monthly free allowance of one million requests and 400,000
GB-seconds, but associated services and account state still matter. Recheck the
actual account before provisioning. [AWS Free Tier](https://aws.amazon.com/free/free-tier-faqs/),
[Lambda pricing](https://aws.amazon.com/lambda/pricing/).

GCP requires a billing account for its free tier. Its eligible trial offers
$300 credit for 90 days without usage billing before a paid upgrade; paid-account
overages are chargeable. Request-based Cloud Run lists 180,000 vCPU-seconds,
360,000 GiB-seconds and two million requests monthly using its stated pricing
basis. Registry storage, builds, logging, networking and other services have
separate limits. Budgets configured for alerts do not hard-cap spending; supported
spend-cap features must be checked service by service, not assumed.
[GCP free program](https://docs.cloud.google.com/free/docs/free-cloud-features),
[Cloud Run pricing](https://cloud.google.com/run/pricing),
[GCP budget behavior](https://docs.cloud.google.com/billing/docs/how-to/budgets).

Azure documents Free Static Web Apps with 100 GB included monthly bandwidth,
250 MB per environment and three unpublished environments; bandwidth overage is
unavailable on that plan. Its Free plan has no SLA. Azure subscription spending
limits depend on subscription type; preserve any existing limit and never remove
it to make deployment succeed. GitHub build/storage allowances are separate.
[Azure plans](https://learn.microsoft.com/en-us/azure/static-web-apps/plans),
[Azure quotas](https://learn.microsoft.com/en-us/azure/static-web-apps/quotas),
[Azure spending limits](https://learn.microsoft.com/en-us/azure/cost-management-billing/manage/spending-limit).

The cloud roles above are deliberately independent. No request must traverse
three clouds to publish a product, and no cloud trial holds the only copy of data.
The Azure reference uses synthetic fixtures; the private VPS UI uses the authenticated
API. AWS and GCP jobs are invoked from a trusted harness with short-lived identity
where supported. No cloud credentials enter a browser bundle.

## Initial implementation choices

| Boundary | Initial choice | Reason and later decision gate |
|---|---|---|
| Frontend | React, TypeScript, Vite, accessible components and a generated API client | One static build supports VPS and Azure; fixtures allow UI development alongside API work. |
| API | Python, FastAPI, Pydantic, psycopg and hash-verified SQL migrations | Typed contracts, validation and explicit database migrations. |
| Persistence and search | PostgreSQL, native text search, typed graph tables; pgvector after measurement | One durable store reduces operating cost; add dedicated graph/search services only after a benchmark justifies them. |
| Work queue | PostgreSQL job table with leases, retries, dead-letter state and transactional outbox | Avoid another persistent service initially; verify a maintained library or implement a narrowly tested queue boundary. |
| Evidence files | Private persistent filesystem behind a storage adapter | Hash/version uploads; never expose files directly. Add object storage only when its operational need and free allowance are verified. |
| AI execution | Configured local CPU models first; optional free notebook batches | Benchmark hardware and quality before choosing model size. No paid provider fallback. |
| Workflow | LangGraph where checkpointing adds value; explicit application authorization | The workflow engine never owns publishing authority. Persist checkpoints in the application store. |
| Training | Datasets, Transformers, Sentence Transformers, PEFT, TRL, Accelerate | Real model adaptation and representation-learning experiments in a separate environment. |
| Operations | Docker Compose, existing HTTPS gateway, OpenTofu for cloud plans, bounded OpenTelemetry/local metrics | Reuse the server's conventions; no Kubernetes cluster, managed database or paid observability requirement. |

pgvector supports vector search inside PostgreSQL; LangGraph provides persistence
for resumable workflows. These capabilities support the proposed boundaries,
not automatic correctness. [pgvector](https://github.com/pgvector/pgvector),
[LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence).

Pin supported dependency versions, image digests, model revisions and licenses
at implementation time. The model IDs supplied in the brief are benchmark
candidates, not hardcoded runtime defaults. Separate runtime dependencies from
GPU/training dependencies; the Cloud Run image must not contain model-training
libraries or large model weights.

## How parallel work and deployment operate

Each phase starts **frontend, backend, AI/data, infrastructure, and QA/security
work together**, using a frozen OpenAPI/schema contract and fixtures. Each lane
owns separate files or a small branch. Integrate a working vertical slice early,
then merge small reviewed changes regularly. One engineer can interleave these
tracks; genuine simultaneous execution requires available collaborators or
explicitly authorized agents. Parallel work does not remove dependencies.

The phase order protects data and publishing boundaries. UI mocks, test design,
infrastructure plans and documentation can proceed while a dependent endpoint
is built; actual dependent execution waits for its contract and security gates.
Do not build ten phases independently and attempt integration at the end.

Every phase deploys a versioned local candidate and a VPS staging release once
the server allocation gate passes. Cloud deployments occur in the phases named
below and can be short-lived. If infrastructure access blocks remote deployment,
record the phase as locally verified with remote acceptance pending.

Before every remote change: inventory the intended resources using native
discovery; snapshot and compare live files against local; reconcile drift; build
locally; run gates; deploy immutable artifacts; exercise real flows; verify local
and remote manifest/image hashes; retain the preceding release. For the shared
VPS, reserve a unique slug and unused loopback port and change only this project's
gateway import. Never replace shared configuration or disturb another tenant.

Use the existing platform inventories: AWS Resource Explorer
(`aws resource-explorer-2 search --query-string '*'`), GCP Cloud Asset Inventory
(`gcloud asset search-all-resources`) and Azure Resource Graph
(`az graph query -q 'Resources'`), then cross-check billing/usage. Confirm inventory
scope and permissions; record unavailable coverage rather than guessing resources
or enabling extra services to make discovery work.

Every phase's release evidence records criteria passed/total; tests, types, lint,
Bandit/gitleaks/Semgrep and build results; behavioral checks; review verdict;
commit/tree and image/model/data revisions; provider/SKU/region where applicable;
deployment and rollback evidence; limitations and observed resource use.
An unimplemented or missing gate stays visible. Nontrivial code needs a reviewer
who did not write it, using a separate session unless delegation is authorized.

## Phase 1 Foundation and first deployment

**Outcome:** a secure, deployable shell and an enforceable project boundary.
Depends on the prepared repository and owner access to existing infrastructure.

| Parallel lane | Work in this phase |
|---|---|
| Frontend | Dashboard shell, login/logout, tenant switch, job/status views, accessible navigation, explicit empty/error/loading states and API fixtures. |
| Backend | Health/readiness/version endpoints, typed settings, OpenAPI, database migrations, authentication and four roles: owner, reviewer, editor, viewer. Tenant identity comes from verified membership, never a request body alone. |
| AI and data | Define evidence, claim, source-version, evaluation and publication schemas; select generated data and licensing rules; inspect PC/server hardware and feasible model classes. |
| Infrastructure | Live shared-server inventory and reservation; isolated Compose network/volumes; local staging profile; resource caps; service/SKU cost ledger; read-only AWS/GCP/Azure account and allowance discovery. |
| QA and security | Threat model, authorization matrix, CI structure, dependency/license checks, secret/configuration regression checks, two-tenant fixtures and first recovery test. |

**Deployment:** local stack and first isolated VPS staging shell; deploy the
sanitized shell to Azure Static Web Apps Free when the account gate passes.
Build on the PC; reuse the existing domain/gateway rather than buying anything.
Prepare AWS/GCP OpenTofu plans, with no automatic apply. Use local CI until a
remote is authorized; do not expose private project records to public CI.

**Exit criteria:** both tenants and all four roles pass their allow/deny matrix;
unauthenticated private endpoints deny access; no secret appears in the static
bundle; migration from an empty database succeeds; container recreation preserves
test data; server neighbors remain healthy; local/live release hashes match.
Record actual Azure deployment or mark that objective pending.

**Rollback:** remove only the new release/site or restore its previous version;
keep volumes and other projects intact. Export and restore the initial database
to an isolated instance before accepting valuable data.

## Phase 2 Evidence ingestion and evaluation foundations

**Outcome:** traceable product facts and a locked benchmark before AI tuning.
Depends on Phase 1 identity, storage and contracts.

| Parallel lane | Work in this phase |
|---|---|
| Frontend | Catalog upload, source viewer with page/passage links, import progress, failed-item retry and version comparison. |
| Backend | CSV/JSON imports; bounded PDF/image uploads; document parsing; immutable source versions; normalized units/variants; content hashes; deduplication; leases, retries and dead-letter jobs. |
| AI and data | Create 30 generated products, approximately 120 permitted images and 200 reviewed questions; label support, contradictions and abstention; split by product family/source before tuning; preserve at least 50 held-out questions. |
| Infrastructure | Evidence volume limits, application-consistent database dumps, encrypted off-server copies to the PC, retention and restore automation; no cloud object-store assumption. |
| QA and security | Malformed files, archive/decompression bombs, MIME spoofing, oversized uploads, malicious PDF/HTML, parser timeouts, worker crash recovery and provenance completeness checks. |

**Deployment:** VPS ingestion API, worker and source viewer; Azure reference gets only
sanitized fixtures. Package a reproducible initial dataset and evaluation runner
locally; no upload of merchant data to a model service.

**Exit criteria:** all 30 products have source/version hashes and attributable
facts; a second identical import creates no duplicate logical facts; changed and
deleted sources invalidate dependent records; an interrupted import resumes;
benchmark labels and splits are frozen; off-server restore reproduces counts and
hashes. Images remain unverified observations until reviewed; OCR is conditional
on actual scanned inputs.

**Rollback:** switch back to the prior API/worker and preserve compatible schema;
rebuild derived indexes from retained authoritative sources. Restore a database
only through the tested migration/restore procedure, never by copying a live DB directory.

## Phase 3 Shopify integration and AWS validation deployment

**Outcome:** a read-only Shopify integration with replay-safe synchronization.
Depends on evidence and durable jobs from Phase 2.

| Parallel lane | Work in this phase |
|---|---|
| Frontend | Store connection, scope visibility, sync history, credential-reconnect status, webhook health, disconnect/export/delete controls. |
| Backend | Verified installation/OAuth state, shop identity, least scopes, encrypted token storage, refresh/expiry handling where applicable, uninstall cleanup, pinned API version, GraphQL pagination and throttling. Validate webhook HMAC against raw bytes; persist receipt before acknowledging. |
| AI and data | Map Shopify products/variants/media into evidence; preserve merchant edits and field ownership; implement a pure manifest/schema validator shared by local execution and AWS. |
| Infrastructure | Deploy that validator as an authenticated AWS Lambda Event Function using a minimal ZIP; restrict invocation identity, timeout, concurrency, payload and retained logs; avoid API Gateway, provisioned concurrency, NAT gateways and model inference. |
| QA and security | Invalid signatures, duplicates, out-of-order events, deleted products, expired/revoked credentials, uninstall, throttling, retry storms and API version contract tests. |

**Deployment:** read-only connector on VPS against a permitted Shopify dev store;
actual AWS validator invocation from a trusted harness against a synthetic evidence
manifest. The primary pipeline retains a local validator, so AWS expiration cannot
stop merchant work. No cross-cloud production database traffic is needed.
Shopify dev stores are for development, and webhook delivery requires verification
and duplicate-safe handling. [Shopify dev stores](https://shopify.dev/docs/apps/build/stores/development-stores),
[delivery verification](https://shopify.dev/docs/apps/build/webhooks/verify-deliveries).

**Exit criteria:** initial sync and incremental change agree; replaying the same
event 100 times produces one logical processing effect; an older event cannot
resurrect a deleted record; 429/retry conditions recover within configured bounds;
invalid credentials/signatures fail closed; local and AWS validator verdicts match
the fixture suite. No product write occurs in this phase.

**Rollback:** disable this app's subscriptions/worker or restore the preceding
connector; keep receipt history; remove only the scoped Lambda resources after
exporting deployment evidence. Verify remaining usage/resources with native inventory.

## Phase 4 Retrieval and context with a GCP deployment

**Outcome:** source-grounded search with measured baselines and context traces.
Depends on Phase 2 evidence and Phase 3 catalog mappings.

| Parallel lane | Work in this phase |
|---|---|
| Frontend | Search and product comparison, filters, citations, no-answer state, freshness indicator and an authorized context inspector. |
| Backend | Tenant/variant/version filters before model exposure; keyword and vector retrieval, hybrid fusion, configured reranking, snapshot API, cache keys and deterministic constraint checks. |
| AI and data | Compare keyword, dense, hybrid and reranked approaches; query intent/entity extraction; context selection by authority, freshness and budget; version prompts/schemas and distinguish evidence from conversation summaries. |
| Infrastructure | Deploy a small authenticated CPU retrieval benchmark container on GCP Cloud Run using a sanitized immutable index snapshot; keep request-based billing and minimum instances zero. Store no credentials or mutable merchant data in the image. |
| QA and security | Exact SKU, semantic, contradictory, missing-evidence, cross-tenant and stale-cache cases; measure Recall@10, nDCG@10, abstention and latency against the frozen split. |

**Deployment:** full retrieval/context path on VPS; actual Cloud Run benchmark
invoked by the trusted test harness. The cloud snapshot backend may differ from
PostgreSQL but must implement the same retrieval contract; compare results on
the same snapshot and disclose differences. Build locally. Proposed image plus
retained registry storage cap: 300 MiB, subject to actual provider accounting.
Registry free allowance is separately documented as 0.5 GB; reject oversized
artifacts rather than silently pay. [GCP free limits](https://docs.cloud.google.com/free/docs/free-cloud-features).

**Exit criteria:** zero unauthorized evidence in the isolation suite; every
answer citation resolves to the exact source version; proposed Recall@10 target
at least 0.85 on labeled answerable questions; critical SKU/variant constraints
pass all fixtures. Select a method only after paired quality/latency comparisons.
If the target fails, improve data/retrieval and keep the phase gate open.

**Rollback:** reactivate the previous retrieval/index version; invalidate affected
caches by version; remove the disposable cloud revision/registry resources only
after preserving artifacts and usage evidence off-cloud.

## Phase 5 Knowledge graph and multimodal content review

**Outcome:** explainable draft creation with graph-based impact analysis.
Depends on source-grounded retrieval and stable context contracts.

| Parallel lane | Work in this phase |
|---|---|
| Frontend | Evidence relationship viewer, affected-content list, claim-level draft diffs, image observations versus verified attributes, and keyboard-accessible review. |
| Backend | Typed graph tables with temporal validity; candidate versus approved relationships; change-impact traversal; draft versioning; deterministic Product JSON-LD; provenance for every factual field. |
| AI and data | Entity resolution, contradiction detection, FAQ and description drafts, purpose-aware alt text and optional batch vision captions; compare graph-backed retrieval with ordinary hybrid retrieval. |
| Infrastructure | Deploy graph queries and drafting worker on VPS; serialize CPU inference; run larger vision batches on the PC/free notebook only when permitted and available; enforce payload/time/memory caps. |
| QA and security | Deliberately misleading images, superseded manuals, conflicting measurements, absent certifications, medical/safety claims, decorative/functional images and structured-data consistency checks. |

**Deployment:** VPS review workflow and refreshed Azure synthetic reference. Prices,
inventory and shipping come from current authoritative inputs, never image
inference or model memory. Alt text depends on image purpose; detailed technical
copy belongs in visible content. Product structured data is generated in code
and checked against visible product content. [W3C images](https://www.w3.org/WAI/tutorials/images/),
[Google product structured data](https://developers.google.com/search/docs/appearance/structured-data/product).

**Exit criteria:** changing a manual identifies every seeded dependent draft;
deleted evidence cannot support a new draft; every proposed factual claim has a
supporting passage or is explicitly rejected; all critical unsupported technical
claims are blocked in the curated suite; functional/decorative alt cases pass
human review; JSON-LD matches fixture prices, currency, availability and variants.
Graph summaries remain experimental unless they improve measured questions.

**Rollback:** disable the candidate model/template/graph traversal by configuration;
restore the previous release; retain old drafts and provenance. No Shopify writes
have occurred yet, so catalog rollback is unnecessary at this stage.

## Phase 6 Resumable approval and guarded Shopify publishing

**Outcome:** the first complete commercial workflow, proven on isolated data.
Depends on draft quality, permissions and durable job state.

| Parallel lane | Work in this phase |
|---|---|
| Frontend | Review/approve/reject exact diffs, approval expiry, execution status, cancellation, write receipts and conflict-aware reversal. |
| Backend | Bounded audit→retrieve→draft→validate→approve→publish→verify workflow; typed tools; durable checkpoints/outbox; approvals bound to tenant, actor, draft hash, source versions, target fields and expiry. Separate the publisher's credential path from model tools. |
| AI and data | Source-supported tools and isolated environment MCP interface; fixed action/retry limits; single-workflow baseline; abstain on unsupported or unsafe changes. |
| Infrastructure | Deploy write-capable worker only to the private VPS profile; use a separate dev-store credential/scope; authentication at every boundary; include telemetry and a publishing kill switch. |
| QA and security | Unauthorized publish, stale/forged/replayed approvals, changed catalog after review, worker death after remote write, partial mutation, timeout with unknown outcome and post-write readback failures. |

**Deployment:** VPS end-to-end workflow against a Shopify dev store only. Demonstrate
approved FAQ/description/alt/schema-related updates according to each supported
Shopify field or theme mechanism. Theme unpublished does not isolate product-data writes.

**Exit criteria:** an approved draft publishes and readback matches; rejection,
expiry, changed evidence and missing authorization all prevent writes; crash and
retry create no duplicate logical publication. For an ambiguous remote timeout,
reconcile the current field state before retrying. Verify API-specific idempotency
instead of assuming it exists. Human approval is mandatory for consequential writes.

**Rollback:** store per-field before/after values and ownership. Reversal proceeds
only if the current value still matches this operation's output; concurrent merchant
edits trigger manual reconciliation. Where Shopify cannot provide an atomic
compare-and-swap for the chosen mutation, document the remaining race and use
detect-and-reconcile or manual export for unsafe operations. Never promise
distributed exactly-once execution or blindly overwrite merchant changes.

## Phase 7 Real supervised and retrieval-model training

**Outcome:** reproducible training artifacts with honest base-versus-adapted results.
Depends on the locked evaluation split and reviewed workflows; models do not train
on prices/inventory as factual memory.

| Parallel lane | Work in this phase |
|---|---|
| Frontend | Annotation review, disagreement queue, dataset versions, experiment results, model-card viewer and candidate/base comparison. |
| Backend | Permission-aware dataset export; deterministic split manifests; model/prompt/data registry; signed or hash-verified artifacts; offline evaluation and explicit promotion states. |
| AI and data | Build an initial 500–1,500 reviewed/synthetic-labeled extraction, tool-choice and abstention examples as capacity permits; train one LoRA SFT adapter and one embedding/reranking experiment with hard negatives. Record seeds, exact revisions and license terms. |
| Infrastructure | Isolated training environment on available local/free notebook hardware; frequent checkpoints; download artifacts off ephemeral runtimes; deploy only a candidate that fits the measured CPU serving envelope. |
| QA and security | Family/source leakage, duplicate labels, PII and licensing checks, reproducible evaluation, artifact integrity, base/adapted regressions and deletion requests affecting training lineage. |

**Deployment:** isolated candidate inference route on VPS or the measured local
test runtime, plus VPS experiment dashboard; refresh Azure with sanitized results.
The accepted production route stays on the current verified model unless the
candidate passes promotion. No training job runs on the shared server by default.
PEFT supports adapter training and TRL supports SFT; free Colab hardware and limits
are not guaranteed. [PEFT](https://huggingface.co/docs/peft/en/index),
[TRL SFT](https://huggingface.co/docs/trl/en/sft_trainer),
[Colab limits](https://research.google.com/colaboratory/faq.html).

**Exit criteria:** real training completes and produces an adapter/checkpoint,
training configuration, dataset/model cards and held-out report; the retrieval
model receives the same baseline comparison. No critical safety regression is
accepted. A model may fail to improve and remain unpromoted; that is a valid
experiment result. If free hardware cannot complete the required runs, the model
engineering milestone remains pending, not replaced by an unexecuted notebook.

**Rollback:** route back to the pinned base/current model; retain candidate artifacts
and findings. Quarantine invalid datasets/adapters and remove them from promotion;
do not delete the evidence of what was tested.
Deleting a training row does not erase it from learned weights. For affected
merchant data, quarantine and retrain/discard the adapter according to its consent
and retention policy; do not claim unlearning without evidence.

## Phase 8 Recommendations and bounded post-training research

**Outcome:** measurable ranking and agent experiments without live-store learning.
Depends on Phase 7 artifacts, held-out evaluation and the isolated environment workflow.

| Parallel lane | Work in this phase |
|---|---|
| Frontend | Explainable product comparisons, constraint-aware recommendations, experiment explorer and simulator trace viewer. |
| Backend | Content-based ranking API with explicit constraints/diversity; isolated environment tools and task simulator; optional read-only MCP client surface; no live-store tokens in simulation. |
| AI and data | Compare a simple ranker with a learned ranker; run one small preference-optimization or permitted distillation experiment; compare single versus bounded multi-agent workflow using the same task/action budget. |
| Infrastructure | Isolated experiment jobs on verified free hardware; deploy simulator/ranker on VPS; time-bounded CPU runs and per-job stop limits; refresh disposable cloud validators/benchmarks only where useful. |
| QA and security | Reward exploitation, fabricated citations, unintended tool calls, constraint failures, cold start, training-set contamination and quality/latency/resource comparisons. |

**Deployment:** VPS recommendation and simulator features, with sanitized Azure
results. Keep experimental model variants off the publishing path. evaluate
GRPO only after supervised baselines, with verifiable rewards and adequate free
hardware. A tiny educational run must be labeled as such; it establishes no
large-model or merchant performance claim.

**Exit criteria:** compare relevance, constraint satisfaction, diversity and catalog
coverage against a simple baseline; complete one actually executed preference or
distillation experiment and record gains/regressions; report whether multi-agent
coordination is worth its overhead. Demonstrate the simulator rejects all seeded
unauthorized publish attempts. Never infer conversion uplift from synthetic events.

**Rollback:** disable experimental routing and revert the ranker/configuration;
retain simulator traces. GRPO, graph neural networks, voice, distributed training
and low-level GPU optimization remain separately gated extensions when hardware
or suitable data is missing; they do not block the merchant application release.

## Phase 9 Operational hardening and deployment rehearsal

**Outcome:** demonstrated failure recovery and a defensible capacity envelope.
Depends on a working publishing flow and stable model selection.

| Parallel lane | Work in this phase |
|---|---|
| Frontend | Operator health, queue lag and freshness dashboards; clear degraded/offline states; cancellation and support/export flows; complete accessibility review. |
| Backend | Rate/body/time limits, retention/deletion, audit export, recovery reconciliation, safe database expand/contract migrations, configuration validation and model-routing fallback to abstention. |
| AI and data | Injection and data-poisoning regression set; confidence/abstention analysis; serving benchmarks for caching, batching, quantization and model size; validate any LLM judge against human labels. |
| Infrastructure | Bounded local metrics/logs/traces, encrypted backup schedule, off-server restore, scoped canary/release switch, kill switches, image provenance/SBOM and cloud resource cleanup. |
| QA and security | Real HTTP/UI tests, cross-tenant attack matrix, SSRF and upload/parser probes, worker restart, queue backlog, disk pressure, dependency outage, expired credentials, source deletion and migration rollback. |

**Deployment:** VPS staging canary first, then the application release only after gates;
rehearse AWS/GCP expiry or removal without breaking the primary flow. Do not
restart the shared host or load-test unrelated applications. Run high-load tests
locally; bounded VPS probes require confirmed headroom. Cloud stress tests are
excluded under the zero-new-spend constraint.

**Exit criteria:** proposed initial release RPO at most 24 hours and RTO at most 4 hours are
met in an actual isolated restore, including evidence files and protected runtime
settings; all seeded tenant/approval/injection critical cases pass; no unresolved
high/critical security defect; zero critical/serious automated accessibility
findings plus manual keyboard checks. Record sample sizes and limitations.
The PC backup destination must actually be available on schedule. Missed or
unrestorable backups raise an alert and can block new valuable writes according
to the configured policy; a backup script alone does not establish the RPO.

Proposed non-model API target: p95 below 1 second at five concurrent users on the
measured initial release workload; queue acknowledgement below 2 seconds. Benchmark model
completion separately, including cold/warm cases, and publish the measured timeout
and queue capacity. Do not claim an uptime SLA from a short test. These targets
must be reviewed against Phase 1 capacity, not silently weakened after failure.

**Rollback:** revert application/model release through a compatible schema;
restore data only when required and verified; replay deletion tombstones after
restore so erased data is not resurrected. Record and test failed-migration and
unknown-write recovery; preserve other server tenants throughout.

## Phase 10 Release evidence and operational handover

**Outcome:** a repeatable release, a useful walkthrough and an honest case study.
Depends on all mandatory previous gates and a separate final review.

| Parallel lane | Work in this phase |
|---|---|
| Frontend | Final merchant walkthrough, onboarding/help, accessible reference dataset, release notes and performance/error feedback. |
| Backend | Tagged/versioned release candidate, migration and API compatibility report, operator CLI, export/import and documented integration boundaries. |
| AI and data | Freeze benchmark, model and dataset versions; publish permitted model/dataset cards and reproducibility instructions; document regressions and unresolved research questions. |
| Infrastructure | Rebuild from a clean checkout; deploy VPS initial release and Azure reference; reproduce AWS validation and GCP retrieval deployments when eligible; export records, verify usage and remove temporary resources. |
| QA and security | Independent release review, full gate suite, end-to-end failure walkthrough, clean restore/redeploy and public-artifact/privacy inspection. |

**Deployment:** final versioned VPS initial release; Azure synthetic walkthrough; real
AWS/GCP acceptance runs with resource/revision/invocation evidence. Historical
evidence from earlier phases remains valid when trials have expired; demonstrate
local reproducibility and state that those cloud endpoints are retired. Do not
reopen paid accounts to make a reference look live.

**Exit criteria:** a new reviewer can reproduce ingestion→search→draft→approval→
publish→verification→reversal on isolated data; a stale manual and malicious
document produce the expected blocks; interrupted work resumes correctly;
backup restoration and local/live hashes pass. The three-cloud objective requires
an actual deployment record for AWS, GCP and Azure; unresolved eligibility is
reported as an incomplete objective. Real-store launch is a separate authorized
step with permitted merchant data and scoped credentials.

**Rollback:** retain the preceding VPS release, compatible database recovery,
model route and UI bundle. Transfer deployment/backup ownership, verification
commands, incident runbooks and the resource inventory. No completion claim
without criteria counts, gate results, behavioral proof and review verdict.

## Requirements added to close gaps

| Gap | Required treatment | Phases |
|---|---|---|
| Identity and credential lifecycle | Membership-bound tenant context, role matrix, safe sessions/CSRF/CORS, encrypted integration tokens, reconnect/revoke/uninstall flows, rotation and least privilege. | 1, 3, 6, 9 |
| Data permissions and deletion | Document permitted use, image/model licenses, review-data consent, retention, export/delete, descendant index/cache/graph invalidation and backup tombstones. Minimize customer/order data. Implement applicable Shopify compliance webhooks before public-app distribution. | 2, 3, 7, 9 |
| Ingestion and publishing races | Durable receipt/outbox, event ordering, versioned facts, field ownership, stale-approval invalidation, unknown-outcome reconciliation and conflict-aware rollback. | 2, 3, 5, 6 |
| Model and dataset supply chain | Pin revisions/digests; prefer safe tensor formats; disallow unreviewed remote model code; license audit, artifact integrity, lineage, train/test isolation and deletion impact on adapters. | 1, 7, 9 |
| Untrusted external content | Parser isolated environment/resource bounds, network egress/SSRF controls, prompt-injection tests, tool authorization in code and no model access to publishing credentials. | 2, 4, 6, 9 |
| Multilingual commerce and accessibility | Currency/unit/locale-aware fixtures, variant constraints, purposeful alt text, screen-reader/keyboard flows and human checks. Translation preserves evidence authority. | 2, 4, 5, 9 |
| Recovery and migrations | Off-server encrypted consistent backups, tested restore, compatible schema rollouts, retained release manifests and shared-host isolation. | 1, 2, 6, 9, 10 |
| Cost and provider expiry | Native inventory plus billing cross-check; all dependent service SKUs; bounded runs; no upgrades; export before expiry; local operation after cloud retirement. | Every phase |
| Evaluation credibility | Versioned held-out products/questions, annotation disagreement, human-calibrated judges, negative cases, confidence intervals where meaningful and paired comparisons. | 2 onward |
| Deployment authorization | Distinguish staging/dev-store releases from merchant publishing; protect CI deployments, use short-lived identity where feasible and never trust forked code with secrets. | 1 onward |

Shopify public-app distribution has mandatory privacy webhook requirements;
implement the applicable compliance path rather than declaring legal compliance
from a catalog-only design. OWASP documents indirect prompt injection, which
supports testing hostile content beyond chat input. [Shopify compliance](https://shopify.dev/docs/apps/build/compliance/privacy-law-compliance),
[OWASP prompt injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/).

## Release artifacts and scope discipline

The planned repository will separate frontend, backend, infrastructure, maintained
data/templates, model lab, and tracked automated tests. Personal rerunnable scripts
remain in the existing ignored manual-test folder. Provider URLs/model IDs/timeouts,
token/step limits, retention, resource budgets and feature flags have one typed
configuration owner; prompts and business content are validated versioned data.

Each phase produces a release manifest, acceptance report, evaluation changes,
sanitized walkthrough and rollback instructions. Keep secret recovery values,
infrastructure access, incident narrative and project memory private. Derive any
public case study from the private dossier and scrub confidential details.

Use a bounded CI matrix and short artifact retention. GitHub Actions/storage can
be chargeable depending on repository/runner/account settings; verify allowances
and spending controls before enabling hosted workflows. Heavy evaluation runs
locally. [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions).
Hugging Face free storage is limited and public storage is best-effort; review
actual allowances before uploads. [Hub storage](https://huggingface.co/docs/hub/en/storage-limits).

Do not promise guaranteed AI-search placement, real-world recommendation uplift,
production GPU performance or high availability. Record measured behavior and
its dataset/hardware limitations. A single shared server is one failure domain.
Cached data and fake outputs must be visibly labeled in the reference.

Later extensions include advertising-analysis drafts from permitted exports,
voice, graph neural networks, community-summary GraphRAG, GRPO, distributed
training, GPU kernels and a tiny educational transformer. Each needs a separate
baseline, resource/permission check and result. Google/Meta campaign activation,
live payments and autonomous merchant actions are outside this roadmap's
zero-new-spend initial release.

The first commercially complete proof arrives in Phase 6. Phases 7–8 add actual
model engineering; Phases 9–10 establish the operational evidence and handover.
Complete work is measured by passed gates and deployed behavior, not the number
of frameworks included.

## Future scale and availability targets

The [scale and cost design](SCALABILITY-AND-COST.md) targets 1M+ **simultaneously active users**, with an explicit six-request/minute workload, public/private mix, database connection and worker-backlog arithmetic, viral bursts, staged cells and regional validation. Start with the separately measured 500–1,000-user envelope before increasing demand. A registered-user or monthly-user count is not a concurrency result.

The [operations policy](OPERATIONS.md) proposes 99% availability over rolling 30 days, separate latency/job/freshness indicators, error-budget actions and RPO≤24h/RTO≤4h. Measurement activates only after telemetry, alert ownership and workload acceptance. These targets do not remove any phase-specific deployment or evidence gate. [Data governance](PRIVACY-AND-LEGAL.md) adds retention, rights, vendor/region and applicable US/EU decisions before new data or regional replicas are introduced; [the threat model](THREAT-MODEL.md) tracks isolation, administrator access and abuse controls as capacity grows.
