# Future scale, capacity and cost

**Design target: support 1M+ simultaneously active users after staged engineering and validation. This is not current measured capacity.** The current server has bounded workspaces and no large-scale load result. A million-user service cannot be promised on free tiers or one small host.

## Define the workload before sizing

Active users, open connections, requests/second and model jobs are different quantities. An active user may read cached pages without hitting the API. HTTP multiplexing means browser sessions do not map one-to-one to connections. A queued AI task may outlive the request that submitted it.

Measure geographic mix, active/idle ratio, device reconnects, request distribution, payloads, evidence size, write percentage, model CPU/GPU service time, cold starts and acceptable queue delay. State every assumption. The following is a planning example only:

| Assumption | Derived load |
|---|---|
| 1,000,000 active users × 6 requests/minute | 100,000 total requests/s |
| 80% public assets/pages; 99% edge hit rate for that public traffic | 800 public origin requests/s |
| 20% private API traffic, never shared-edge cached | 20,000 API requests/s; 20,800 combined origin requests/s |
| 90% API reads; 90% tenant-aware application read-cache hit | 1,800 uncached reads/s plus 2,000 writes/s |
| Average 3 database operations per uncached request | About 11,400 DB operations/s, before background work |
| 0.001 future model jobs/user/second | 1,000 jobs/s |
| Assumed 0.25 CPU-seconds/job, 60% utilization ceiling | At least 417 CPU cores for that workload, before redundancy |
| Assumed 2-second end-to-end job latency | About 2,000 jobs in the system by L = arrival rate × latency |

These are derived from stated planning assumptions, not benchmark results. Real inference may be much slower; measured model service time must replace 0.25 seconds. Current draft jobs are extractive templates, so future generative jobs require an independent capacity model.

For a separate edge-memory example, assume 1.2 million live connections and 32 KiB of state each: roughly 36.6 GiB before TLS buffers, operating-system overhead and redundancy. This does not establish that one node can hold those connections. At 100,000 requests/s and 10 kB average delivered content, sustained traffic is about 1 GB/s or 2.59 PB per 30 days. Edge-cache hits still incur delivery traffic.

## Separate three execution paths

1. **Public content:** CDN/edge-cache immutable assets and public pages; keep sensitive data out. Use content-hashed assets, compression and explicit invalidation.
2. **Interactive evidence API:** stateless app replicas, tenant-aware authorization, bounded DB connections, indexed current-evidence queries, request deadlines and per-tenant fairness. Approval/current-version checks always consult authoritative state.
3. **Asynchronous AI/ingestion:** durable queues, bounded admission, idempotency/fencing, per-class concurrency and independent worker pools. Return a job receipt, not an open HTTP connection for long inference.

Shared caches must never mix tenants or permissions. Application cache keys include tenant, authorization context, source/index revision, model/prompt version and relevant locale. Invalidate superseded/deleted evidence. Never serve an old approved draft as current because its cache entry survived.

## Staged architecture

| Stage | Engineering gate before expanding |
|---|---|
| Measure existing release | Representative isolated load; p50/p95/p99 latency, CPU/memory/disk, DB connections, queue age and recovery |
| Separate bottlenecks | Public edge delivery; API/worker resource isolation; bounded pooling; index/SQL profiling; overload/backpressure |
| Multiple application replicas | Externalized session state, job claims tested under contention, compatible rolling migrations and controlled routing |
| Dedicated data/search tier | PostgreSQL replicas where consistency permits, partition/index maintenance, evaluated vector index and evidence-object storage |
| Tenant cells | Deterministic tenant-to-cell routing; independent DB/queues/workers and quotas; contain noisy neighbors/failures |
| Regional cells | Residency-aware routing, cross-region recovery, explicit write ownership and tested failover |
| 1M+ validation | Representative sustained/spike/soak/failure tests, contractual capacity/cost review and measured SLO window |

A cell contains a bounded group of tenants with independent persistence and worker capacity. Avoid a global synchronous dependency for every request. Rebalance tenant placement with versioned routing and migration reconciliation; prevent dual writers during moves. Preserve cross-tenant access controls within every cell. Azure documents deployment stamps as a scale/isolation pattern; this is a proposed application of that pattern: [deployment stamps](https://learn.microsoft.com/en-us/azure/architecture/patterns/deployment-stamp).

Do not shard prematurely. First prove why indexing, pooling, batching, storage layout and replicas cannot meet the measured requirement. Assign a tenant's transactional approval/source state to one write authority. A remote read replica may be stale and cannot independently authorize publication.

## Regions, failures and consistency

Start with one well-operated primary region and independent backups. Add multiple availability zones and managed failover only after actual cost approval. For multiple regions, define residency, keys, replication lag, RPO, conflict policy and tenant routing. Prefer regional write ownership; active-active writes require stronger conflict/ordering design than “replicate the database”.

Measure regional loss, network partitions, queue replay, stale cache and model unavailability. Public content can remain available while private writes fail closed. Degraded keyword search is allowed only when truthful; queued actions must expose delay and cancellation. Multi-cloud adapters should support independent bounded workloads, not put AWS→GCP→Azure in the synchronous critical path. [AWS reliability guidance](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/welcome.html).

## Cost planning and free-tier boundaries

Current execution reuses an existing server and local CPU model; the server, storage, electricity and operator time are not inherently free. No paid provider fallback is needed for current retrieval. A zero-new-service-spend development constraint does not make future scale cost zero.

Estimate compute-hours, memory, DB/replica storage and IOPS, connection pools, model accelerators, queues, CDN/egress, object storage, backups/keys, logs/traces, DNS/TLS operations, CI/artifacts and support. Show steady load, bursts, failover headroom and retention. Cost per accepted output needs accepted outputs as its denominator.

Proposed independent cloud roles remain Azure public static content, AWS deterministic manifest validation, and GCP immutable-snapshot retrieval benchmarking. None is claimed deployed. Verify native inventory, account eligibility, billing status, regional SKUs, allowance expiry and associated build/log/network costs before execution. Budget alerts are not a universal hard spend cap.

Official programs change: [AWS Free Tier](https://aws.amazon.com/free/), [GCP free program](https://docs.cloud.google.com/free/docs/free-cloud-features), [Azure free services](https://azure.microsoft.com/en-us/pricing/free-services). Free credits expire; quotas, billing-account requirements and exclusions vary. Do not upgrade, activate billable services or remove a spending limit to complete architecture validation. Obtain explicit cost authorization and preserve a tested shutdown/export path.

## Validation and admission

Run stepped, spike and soak workloads against synthetic tenant distributions, including a hot tenant and long evidence fields. Test queue saturation, worker death, DB failover, cache loss, expired identity and regional unavailability. Monitor leakage, stale approvals and data loss—not just throughput. Compare load-generator capacity with target capacity.

Declare the verified envelope only after repeating a representative run with safety headroom and independent review. Admission should reject excess work early with retry guidance; do not silently accept unbounded jobs. A future 99% availability target is governed by [the SLO policy](OPERATIONS.md), not inferred from replica count.
