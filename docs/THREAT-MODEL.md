# Threat model

Scope: browser, public reverse proxy, API, PostgreSQL, worker, model cache, imports, approval/export and release artifacts. This is a design review of the current system, not a penetration-test certificate.

| Asset / threat | Implemented boundary | Remaining validation |
|---|---|---|
| Another workspace's evidence | Cookie-derived tenant, transaction-local context, forced RLS, scoped ID lookup | Repeat cross-tenant matrix after every schema/query change |
| Cookie theft / forged write | HttpOnly/Secure/SameSite cookie, token hashes, exact Origin and JSON writes | XSS/CSRF review, expiry/recovery and proxy trust tests |
| Injection in imported text | Typed JSON and parameterized SQL; text is data | Future parsers/model tools need separate isolation and injection tests |
| Unsupported publication | Evidence-only drafts, version checks, approval/export | Shopify publishing is absent; later credentials must sit outside model tools |
| Stale or repeated work | Immutable evidence, stale invalidation, leased attempt fencing | Cross-service side effects need outbox/reconciliation before integration |
| Exhausted CPU/database/disk | Body/rate/catalog/job bounds, thread/resource limits | Adversarial load profile, per-tenant fairness and overload telemetry |
| Compromised dependency/model | Hash locks, pinned image/model revision, controlled download | Dependency monitoring, release SBOM and reproducible rebuild checks |
| Backup exposure / loss | Protected operations and verified independent restore | Document encryption, retention, ownership and scheduled recovery success |
| Host administrator compromise | Separate containers/roles and no runtime admin DSN/socket | Host/root remains trusted; isolation cannot protect from a fully compromised host |
| Browser cache / cross-tenant reuse | Same-origin access and tenant-scoped evidence lookup | Any future response cache must key tenant/permissions/source/model versions |

Trust boundaries are crossed at the public request, cookie-to-tenant mapping, database connection, worker claim, model artifact download and release promotion. A source citation establishes lineage, not truth; malicious or incorrect source documents can still produce incorrect evidence-backed quotations.

Prompt injection is limited today because retrieved text does not execute tools. Future generative workflows must authorize tool arguments and publishing in application code, restrict egress and test hostile documents/images/tool results. Do not rely on an instruction asking a model to ignore malicious text. [OWASP prompt injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/).

Session controls follow standard cookie guidance but require actual configuration and browser checks. HttpOnly reduces script access to tokens; it does not remove XSS impact. [OWASP session management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html).

For a future merchant release, add account lifecycle/recovery, RBAC, integration-token encryption and rotation, processor agreements, deletion propagation, abuse monitoring, incident notification and independently reviewed upload handling before enabling the respective feature.
