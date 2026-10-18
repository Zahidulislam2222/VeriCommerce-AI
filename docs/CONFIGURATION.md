# Configuration and secret boundaries

Operational values have one owner. Maintained content is data, credentials are protected secrets, and API/schema syntax is a compatibility contract.

Current release `20261018-phase5-02` follows quota release `20261018-phase3-01`, the integrated expansion `20261018-phase1-01` and the verified 2026-10-15 evidence release, still reporting API version 0.2.0. Its 228 artifact hashes match and four services passed verification. Dedicated Shopify OAuth installation with read-only scope and initial sync of 61 products, 23 sources and 206 passages have been verified. Azure Free publication and four initial plus four final-source AWS validator invocations have separate evidence; the final AWS ZIP and republished Azure assets match current source. The GCP IAM-authenticated three-document smoke passed three cases and its temporary resources were removed before the approved deadline. These provider runs validate separate sanitized contracts; configuration validation alone does not establish general quality or zero final charges. Two actual HMAC-verified Shopify update events were separately observed and reconciled exactly with full sync after an owner-approved Admin title change and restoration; the app retained only `read_products` and made no product-write calls.

| Boundary | Owner | Treatment |
|---|---|---|
| Browser behavior | `src/config.ts`, root `.env.example` | Validated public flags; never secrets |
| Website/content | `src/data/` | Versioned JSON with route/source validation |
| API/worker | `backend/vericommerce_core/settings.py` | Pydantic `VC_` environment settings |
| Backend names/examples | `backend/.env.example` | Safe examples, not production values |
| Orchestration | `infra/core/compose.yaml`, example environment/config | Typed release rendering owns environment values |
| Dataset/policy | `backend/data/` | Reviewed versioned inputs |
| Optional cloud/backup adapters | `infra/cloud/settings.py`, `infra/cloud/config.json` | Typed synthetic runtime and resource/backup budgets; separate from application settings |
| Cloud deployment | `infra/cloud/tofu/` | Provider-validated examples/plans; never implicit billing/API activation |
| Protocol | API paths, HTTP semantics, SQL schema | Compatibility review before changes |

`VC_SETTINGS_FILE` selects a protected dotenv file. API/worker receive only the restricted database DSN. Administrator credentials go only to migration. Private recovery material, local environment files and operator state stay out of public artifacts/history. Direct dependency pins must match the production hash lock. The final clean locked environment passed 142 backend/infrastructure checks and package consistency with Pillow 12.3.0; an earlier direct-pin mismatch was corrected without changing the version already running on the server.

## Setting groups

| Group | Principal settings |
|---|---|
| API metadata | `VC_API_VERSION`; validated maintained policy owns the OpenAPI title, service label and retrieval/draft copy; protocol errors remain in code |
| Persistence/origin | `VC_DATABASE_URL`, `VC_MIGRATION_DATABASE_URL`, `VC_ALLOWED_ORIGINS` |
| Access | Cookie name/security, `VC_SESSION_TTL_SECONDS`, `VC_MAX_ACTIVE_SESSIONS` |
| Accounts | Registration flag; separate account cookie/session lifetime, authentication attempts, account/member/workspace/session quotas |
| Password hashing | Scrypt N/r/p/memory; bounded parallelism and queue timeout |
| Abuse/input | `VC_MAX_BODY_BYTES`, `VC_REQUESTS_PER_MINUTE`, `VC_SESSION_CREATIONS_PER_HOUR` |
| Workspace quotas | Maximum products, sources, passages, revisions, drafts, jobs, audit events and evaluations |
| Retrieval | Search count/maximum, lexical score floor, reciprocal-rank-fusion constant, dense similarity floor |
| Context/review | `VC_CONTEXT_MAX_CHARS`, `VC_CONTEXT_MAX_PASSAGES`, `VC_MAX_RELATIONS` |
| Upload/parser | Binary/storage/page/pixel limits, parser time/memory/text/result bounds |
| Database bounds | Connection timeout and statement timeout |
| Worker | Poll interval, lease, attempts, retry interval, tenant batch and heartbeat |
| Model/cache | Enable/download flags; model/repository/revision/file/cache/thread/batch |
| Maintained inputs | Seed, policy, evaluation and migration paths |
| Intelligence/benchmark | Validated intelligence policy, frozen benchmark and delegated agent-review data paths |
| Shopify identity/secrets | Enable flag, client ID/secret, encryption key, exact callback/return URLs, allowed origin and state cookie |
| Shopify transport | Pinned stable API quarter, exact `read_products` scope, time/page/retry/response/webhook/receipt/sync bounds and maintained GraphQL queries |
| Local bind | `VC_API_HOST`, `VC_API_PORT` and explicit server start configuration |

Complete setting names/defaults stay in [the backend example](../backend/.env.example) and typed settings rather than being duplicated here. Regression coverage requires an exact setting-name match. Validation requires an immutable model revision, bounded limits, default search count within its maximum, scrypt power-of-two N, and worker tenant batch coverage at least equal to allowed temporary workspaces. Fair scanning separately covers persistent workspaces. Quotas are admission rules, not throughput measurements.

Core deployment configuration explicitly supplies `environment.MAX_PRODUCTS`;
Compose forwards it as `VC_MAX_PRODUCTS` to the API and worker through the shared
application environment. Shopify parent products and their imported variants each
count toward that quota. Choose a bounded value from measured catalog size and
capacity, then create a new immutable release; editing an active release's environment
is not a configuration rollout. Source and passage quotas remain independent.

Default binary uploads are1 MiB, distinct from the ordinary JSON request cap. Upload admission allows bounded base64/JSON overhead; reverse-proxy limits must also cover that envelope. Raising one limit does not raise storage, parser memory/text/result or page/pixel budgets. Accepted formats/CSV columns and technical-claim/unit/context policy are maintained in validated intelligence data. Static raster validation does not enable OCR or vision inference.

Shopify is disabled by default. Enabling it requires credentials, a valid encryption key and configured HTTPS callback/return origins. Validation permits only `read_products`, the verified shop-domain transport template, a stable pinned API quarter and the exact callback route. Credential values stay in protected settings; they never enter static bundles, examples or image/release environment metadata. Callback state, token refresh and webhook receipt limits remain bounded. Real OAuth and an actual expired-token refresh were separately verified with exactly `read_products`; rotated access/refresh credentials were preserved in protected private recovery storage. Settings validation alone does not establish those transport results.

Temporary session expiry enables worker cleanup; account-session expiry does not erase persistent workspace data. Product/source tombstones are schema state, not configuration toggles. Benchmark review policy separates owner-delegated agent review from human attestations; changing a review sidecar cannot change the frozen corpus hash.

Optional cloud adapters use their own typed JSON owner because they package independently without merchant/database settings. Read [their configuration and cost boundaries](../infra/cloud/README.md) before planning deployment. A local provider validation or successful backup encryption is not a cloud deployment or a populated application restore.

Deployment reserves a loopback port and nonoverlapping network from actual inventory. Its dynamic pool excludes the fixed trusted proxy address. Cache and Nginx temporary paths must be writable under the actual nonroot UIDs/read-only filesystem. Examples do not authorize shared-service mutation.

Every configuration change updates its example, validation, regression coverage and release evidence. Audit public artifacts for credentials, private addresses, workstation paths and unintended environment output.
