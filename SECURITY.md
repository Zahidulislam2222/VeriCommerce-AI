# Security policy

VeriCommerce AI is maintained by **Zahidul Islam**. Report suspected vulnerabilities privately to [muhammadzahidulislam2222@gmail.com](mailto:muhammadzahidulislam2222@gmail.com) with the subject “VeriCommerce AI security report”.

Include the affected route/version, minimal reproduction, impact and a safe redacted example. Do not include passwords, cookies, tokens, private product data or another user's records in the first message. If sensitive evidence is necessary, request an appropriate transfer method. No response-time guarantee or bug-bounty payment is offered.

## Supported release

Security fixes target the current maintained release. Older immutable artifacts are recovery records, not separately supported product branches. A report is assessed for reproducibility, severity and affected versions before disclosure. Coordinated disclosure timing is agreed case by case; no fixed remediation deadline has been measured.

## Implemented controls

- Opaque cookie access, stored token hashes, expiry and exact-origin JSON write checks.
- Persistent scrypt account identities, separate account sessions and owner/reviewer/editor/viewer memberships, with expected-workspace request binding and write-time permission rechecks.
- Tenant context plus forced PostgreSQL RLS and restricted runtime credentials.
- Typed input, body/rate/storage bounds and parameterized database operations.
- Immutable source revisions, stale-draft rejection, explicit approval and fenced job attempts.
- Bounded isolated document parsing; current-only variant retrieval; HMAC-verified connector receipts and encrypted tenant/shop-bound tokens with only `read_products` permission.
- Pinned dependencies/images/model revision, nonroot/read-only containers and protected secret mounts.
- Self-hosted browser assets, restrictive CSP and local/live artifact verification.

The [threat model](docs/THREAT-MODEL.md) describes scope and residual risks. Passing Gitleaks, Bandit, Semgrep and automated tests is evidence of those checks, not a guarantee that no vulnerability exists.

## Safe research

Use your own temporary workspace and generated records. Do not extract another workspace's data, exhaust public resources, scan unrelated infrastructure, persist access, trigger external-store actions or publish exploit details before coordination. Capacity/denial-of-service testing requires a separately agreed isolated environment.

Persistent account workspaces and expiring temporary access have different lifecycles. Login does not provide email verification, password recovery or administrator MFA. Use permitted non-sensitive product inputs; do not store customer records, credentials or regulated data. Formal security certification, independent penetration testing, complete at-rest encryption verification and a staffed round-the-clock response team are not established by this release.

Growing the service requires a tested auth/abuse policy, key rotation, data-retention and rights procedures, dependency monitoring, recovery ownership and tenant isolation across caches, workers and regional cells. [Operations](docs/OPERATIONS.md), [data governance](docs/PRIVACY-AND-LEGAL.md) and [capacity planning](docs/SCALABILITY-AND-COST.md) track those gates. A provider certificate or security scanner does not establish application compliance.
