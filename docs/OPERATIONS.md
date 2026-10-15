# Operations, recovery and availability

This document separates existing recovery evidence from proposed operating targets. The current deployment uses one existing server and has no measured rolling availability history, verified automated backup cadence, contractual SLA or staffed 24/7 on-call commitment.

## Observed operational evidence

The evidence-core release was restored into a separate database with exact table payload hashes and restricted-role/tenant-isolation probes: 15 test workspaces, 106 source revisions and 7 drafts. Those counts are test records, not customers. Actual application rollback served the previous frontend and disabled the API; forward recovery restored it and preserved a previously approved draft's exact content hash.

The subsequent public-page release preserved the existing API/worker/database identities and backend image. Its new frontend rollback path passed 15 safety regressions, but no additional actual database restoration or runtime rollback was performed for that frontend-only change. A successful rehearsal proves recoverability for the tested state; it does not establish scheduled recovery-point or recovery-time performance.

## Proposed 99% availability SLO

**Status: future target, not observed uptime or a customer SLA.** Start measurement only after instrumentation, coverage and alert delivery have been validated.

| SLI | Definition | Proposed target |
|---|---|---|
| Interactive availability | Good eligible requests / all eligible requests, over rolling 30 days | At least 99% |
| Interactive latency | Eligible non-model requests completed within 1 second / eligible requests | At least 95%, after workload validation |
| Job acceptance | Valid requests durably acknowledged within 2 seconds / eligible submissions | At least 99%, measured separately |
| Job outcome | Accepted jobs reaching a usable terminal result within the agreed class deadline / accepted jobs | Define per workload after CPU benchmarks; failures/cancellations reported separately |

Eligible interactive traffic is well-formed in-scope product/evidence/search/draft-read/approval traffic from admitted workspaces. Good responses have the expected success schema, no server failure and complete within the proposed 5-second interactive deadline. This deadline still requires implementation, cancellation and workload validation before SLO measurement starts. Invalid input, expired credentials and genuinely over-quota clients are counted separately. Capacity-driven rejection or unexpected429 for an otherwise admitted eligible request is a bad event; excluding overload would hide failure. Missing telemetry is reported as unknown coverage and cannot be silently called success.

Measure website delivery and working API separately; a healthy static page must not hide unavailable evidence functionality. Readiness probes supplement, not replace, real user-journey signals. Valid abstention is a successful transport/business response; unsupported factual content is a separate correctness failure.

The request error budget is **1% of eligible requests** in the rolling window. At one million eligible requests that permits 10,000 bad events. A time-based equivalent at continuously observed full outage is 432 minutes in 30 days (7 hours 12 minutes); it is not interchangeable with a traffic-weighted request budget. A 4-hour full outage would consume about 56% of that time-equivalent allowance.

Proposed actions: record budget consumption daily; pause nonessential releases when the window is exhausted; permit recovery/security fixes; investigate sustained burn above 1× and page the operator for a validated fast-burn alert. Choose multiwindow thresholds from actual traffic and incident simulations to avoid paging on one sparse request. Publish window, numerator, denominator, coverage and burn—not a bare uptime percentage. Google distinguishes SLIs, SLOs and contractual SLAs: [SRE definitions](https://sre.google/sre-book/service-level-objectives/), [SLO implementation](https://sre.google/workbook/implementing-slos/).

## Proposed backup and restoration policy

Future targets are **RPO≤24 hours** and **RTO≤4 hours**. RPO is maximum acceptable data loss relative to the incident; RTO runs from incident declaration through validated service recovery. Neither target is established by the current one-time restore evidence.

Before valuable durable data is accepted, assign an operator and confirm the backup destination is available. Schedule consistent PostgreSQL dumps, model/release manifests and required protected configuration; separately handle future evidence objects. Encrypt off-server copies with independently recoverable keys, define retention/deletion/legal-hold rules, restrict access and alert on missed/unrestorable copies. These are required additions, not verified present controls.

Restore procedure:

1. Preserve the primary database and incident evidence; select a known compatible release and verified backup.
2. Verify archive hashes, completeness and protected permissions before restore.
3. Restore into a separate empty database with an appropriately privileged maintenance role.
4. Restore grants and restricted role settings; compare all-table payload hashes, counts and schema migration hashes.
5. Test forced RLS with two tenants and absent tenant context; exercise a source, draft, approval and export.
6. Reapply deletion tombstones before exposure when deletion support exists; record backup-age loss.
7. Promote only after readiness, real HTTP/UI and source-version checks pass. Record start/end times, observed RPO/RTO and failures.

A database dump alone excludes evidence files, secrets and models unless explicitly covered. Restoring a newer schema with an older image can fail; use expand/contract migrations or a separately reviewed data recovery plan. Never claim image rollback reverses migrations. [PostgreSQL backup methods](https://www.postgresql.org/docs/17/backup.html).

## Incident response

The initial operator is Zahidul Islam; report through the [security policy](../SECURITY.md) or contact page. No guaranteed response time is offered. Proposed severity1: isolation breach, data corruption, suspected credential theft or complete critical-path outage; severity2: sustained degraded retrieval/queue/approval; severity3: limited noncritical defect.

Declare and timestamp the incident, freeze risky changes, scope impact, preserve sanitized evidence, and contain the narrow affected service. For corrupted or stale data, block new approvals before attempting recovery. Revoke/rotate affected credentials through the protected operator path; a deployment rollback is not credential rotation. Do not restart shared services or delete unrelated containers.

Use a compatible immutable release rollback for application regressions; use independent restore only when data recovery is required. Validate health, readiness, tenant isolation, citations, approval version fences, persistent draft content, public TLS and artifact parity before closing. Record impact, timeline, root cause, fix, evidence and a prevention gate. For personal-data incidents, assess jurisdiction-specific notification duties with appropriate legal support.

## Monitoring and routine maintenance

Required future telemetry: route success/latency, readiness, queue age/attempts/fencing conflicts, worker heartbeat, expiry cleanup, database connections/locks/disk, model/fallback status, backup freshness/restore success and artifact drift. Never label raw query text, source text, credentials or cookie tokens as metrics. Bound log/trace retention and cardinality.

Review security updates and pinned revisions, rotate credentials, verify disk headroom, rehearse recovery after schema/role changes, and check exports before workspace expiry. Load and failure tests belong on isolated owned environments; public or shared-host stress testing needs separately verified headroom and authorization.
