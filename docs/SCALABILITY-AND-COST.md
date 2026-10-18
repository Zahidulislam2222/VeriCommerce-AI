# Future scale, capacity and cost

**Design target: support 1M+ simultaneously active users after staged engineering and validation, not current measured capacity.** The current deployment is one bounded persistent application; even its 500–1,000-user serving envelope has not been load-tested. Free or nearly free operation at low activity is an architectural aim; large sustained traffic requires paid capacity and verified provider quotas.

The current persistent database, durable worker and resident CPU model reuse an
existing fixed-capacity server. This is the simplest verified initial deployment;
it does not automatically scale or stop its costs when traffic falls. Public
static delivery and isolated on-demand validators can scale independently. A
future request-based service can reduce idle compute, while storage, backups and
other dependencies retain their own charges. [Cloud Run autoscaling](https://docs.cloud.google.com/run/docs/about-instance-autoscaling).

## Define the workload before sizing

Active users, open connections, requests/second and model jobs are different quantities. An active user may read cached pages without hitting the API. HTTP multiplexing means browser sessions do not map one-to-one to connections. A queued AI task may outlive the request that submitted it.

Use these definitions in every capacity report:

| Quantity | Definition for this planning model |
|---|---|
| Registered accounts | Stored identities, including inactive accounts; a storage/security quantity |
| MAU / DAU | Distinct authenticated people active in a calendar month/day; report the timezone and bot treatment |
| Simultaneously active users | People participating at the same time in the specified burst/steady interval; this model assumes six requests per minute per person |
| Open connections | Observed client/edge connections, including idle/reconnecting clients; size independently of API requests |
| Admitted work | Requests/jobs accepted within a tenant's published quota; measure rejected demand separately |

One million monthly users does not imply one million simultaneous users. State both when describing a commercial forecast. Specify active duration and request cadence rather than converting registrations directly into replicas.

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

For the 20,000 private API requests/s example, split the assumed workload into 18,000 reads and 2,000 writes. If 90% of reads can use an authorized application cache, 3,800 requests/s still reach transactional storage. An assumed 20 ms connection-hold time implies 76 concurrently busy database connections; a 60% utilization ceiling implies about 127 pool slots before maintenance/failover reserve. This is a sizing illustration, not the current database configuration. Replace it with observed transaction duration, lock waits, query plans and connection-acquisition latency. Current application connections are opened through the database boundary; a shared transaction pool and its tenant-reset behavior require implementation and isolation tests. Increasing PostgreSQL connections also increases resource allocation: [PostgreSQL connection settings](https://www.postgresql.org/docs/17/runtime-config-connection.html).

State payloads separately: an example planning profile uses 2 KiB request bodies and 10 kB average responses for interactive reads; ingestion uses the configured bounded binary/JSON envelope and a separate concurrency budget. A byte-heavy import must not consume the interactive pool. Count source parsing, vector refresh, index maintenance, audit writes and backup traffic in addition to the foreground arithmetic.

Before growth, a proposed normal test is 1,000 simultaneously active users at six
requests/minute each, or 100 requests/s, followed by a 10× five-minute spike and a
recovery interval. These tests have not run. First agree the read/write/upload
mix, admission limits, payload sizes and latency/error targets; approve any paid
load separately. Even500–1,000-user capacity is currently unmeasured. Database
connections, model CPU time, queue age, scaling speed and provider quotas must be
measured alongside web throughput.

For a separate edge-memory example, assume 1.2 million live connections and 32 KiB of state each: roughly 36.6 GiB before TLS buffers, operating-system overhead and redundancy. This does not establish that one node can hold those connections. At 100,000 requests/s and 10 kB average delivered content, sustained traffic is about 1 GB/s or 2.59 PB per 30 days. Edge-cache hits still incur delivery traffic.

## Separate three execution paths

1. **Public content:** CDN/edge-cache immutable assets and public pages; keep sensitive data out. Use content-hashed assets, compression and explicit invalidation.
2. **Interactive evidence API:** stateless app replicas, tenant-aware authorization, bounded DB connections, indexed current-evidence queries, request deadlines and per-tenant fairness. Approval/current-version checks always consult authoritative state.
3. **Asynchronous AI/ingestion:** durable queues, bounded admission, idempotency/fencing, per-class concurrency and independent worker pools. Return a job receipt, not an open HTTP connection for long inference.

Shared caches must never mix tenants or permissions. Application cache keys include tenant, authorization context, source/index revision, model/prompt version and relevant locale. Invalidate superseded/deleted evidence. Never serve an old approved draft as current because its cache entry survived.

Account/session checks and workspace selection remain authoritative. Do not share-cache `/api` responses merely because a public page is cacheable. Login, password hashing and the multi-request workspace bootstrap need a separate burst model: a million people returning within one minute means about 16,667 session starts/s before additional bootstrap calls. Bound authentication CPU, connection creation, session storage and browser retries; jitter reconnects and coalesce safe reads without replaying writes.

Queue policy should define per-tenant concurrent jobs, admitted bytes, oldest-age limits and fair service between imports, drafts and maintenance. Use durable receipts, idempotent effects, generation/attempt fencing and bounded dead-letter recovery. For a future arrival rate of 1,000 jobs/s and 600 jobs/s service for five minutes, backlog grows by 120,000 jobs. If demand then drops to 100/s while service stays at 600/s, draining that backlog takes about four minutes. Admission and retention must prevent an unbounded backlog; clients need explicit queue delay and retry guidance.

## Staged architecture

### Cloud-priority placement with a measured hybrid boundary

Prioritize suitable AWS, GCP and Azure services when account eligibility, shared allowances, quotas, dependent services and shutdown behavior have been verified. Assess a hybrid design before adding paid capacity: retain persistent or expensive CPU/model work on existing resources where that is the better cost/performance choice. This is a future placement policy; it authorizes no migration or provisioning and does not change the existing application deployment.

| Component | Current evidence / proposed placement | Reason and cost limit |
|---|---|---|
| Public assets/pages | Azure Free hosts a separate sanitized reference; future public-edge delivery can use an eligible cloud static/CDN service | Offload cacheable bytes while keeping private data out; verify delivery quotas, custom-domain/CDN features and overage behavior |
| Stateless private API | Persistent API is on existing hosting; evaluate GCP Cloud Run or an equivalent eligible request-based service for future replicas | Reduce idle compute where startup/DB access/residency permit; bound instances/concurrency and include networking, requests, logs and minimum-instance charges |
| Deterministic validation | Authenticated AWS Lambda validation has actual evidence; expand bounded event work only after its workload is measured | Small independent jobs suit short-lived compute; include invocation, IAM, queue/log/storage dependencies and shared account usage |
| Retrieval/model CPU | Resident pinned CPU retrieval remains with existing capacity; a temporary private GCP contract was exercised and removed | Avoid repeatedly shipping a model or paying for heavy cold starts; measure model memory/locking, cache locality and CPU time before moving work |
| Transactional data and durable queues | Existing PostgreSQL remains the current authority; future pool/replica/cell placement follows measured limits | Preserve write consistency and tenant isolation; managed databases, IOPS, backups, inter-region transfer and keys often retain fixed charges |
| Evidence objects/backups | Current bounded data and tested recovery remain on their existing paths; evaluate eligible cloud object storage for a reviewed future off-server tier | Durable objects can scale separately; include revision retention, retrieval/egress, encryption, lifecycle and restore-time deletion reconciliation |

Use the three clouds for independent, justified responsibilities rather than chaining them into every interactive request. Co-locate a future API cell with its write authority where latency, egress and residency require it; multi-cloud experience is not a reason to move private data repeatedly. Record each placement decision, measured envelope, owner, free-allowance scope, expiry/retained charges and export/rollback path. A change exceeding verified free coverage requires separate cost approval. The million-user stage can require paid database/compute capacity even if earlier stages fit existing resources or allowances.

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

The cell control plane assigns tenant ownership and publishes versioned routing; ordinary reads should continue with a valid local routing version if that control plane is briefly unavailable. Move a tenant with snapshot/catch-up, a fenced write handover and payload reconciliation, then retire the old writer. Evidence objects, indexes, keys, deletion records and backups move under the same residency policy. A regional cache or replica must not bypass the tenant's approved processing location.

Do not shard prematurely. First prove why indexing, pooling, batching, storage layout and replicas cannot meet the measured requirement. Assign a tenant's transactional approval/source state to one write authority. A remote read replica may be stale and cannot independently authorize publication.

## Regions, failures and consistency

Start with one well-operated primary region and independent backups. Add multiple availability zones and managed failover only after actual cost approval. For multiple regions, define residency, keys, replication lag, RPO, conflict policy and tenant routing. Prefer regional write ownership; active-active writes require stronger conflict/ordering design than “replicate the database”.

Measure regional loss, network partitions, queue replay, stale cache and model unavailability. Public content can remain available while private writes fail closed. Degraded keyword search is allowed only when truthful; queued actions must expose delay and cancellation. Multi-cloud adapters should support independent bounded workloads, not put AWS→GCP→Azure in the synchronous critical path. [AWS reliability guidance](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/welcome.html).

## Cost planning and free-tier boundaries

Current execution reuses an existing server and local CPU model; the server, storage, electricity and operator time are not inherently free. No paid provider fallback is needed for current retrieval. A zero-new-service-spend development constraint does not make future scale cost zero.

Estimate compute-hours, memory, DB/replica storage and IOPS, connection pools, model accelerators, queues, CDN/egress, object storage, backups/keys, logs/traces, DNS/TLS operations, CI/artifacts and support. Show steady load, bursts, failover headroom and retention. Cost per accepted output needs accepted outputs as its denominator.

Use a dated regional rate card and actual account allowances, then calculate each scenario explicitly:

| Cost term | Planning equation / evidence needed |
|---|---|
| Request-based compute | Billable vCPU-seconds × regional CPU rate + GiB-seconds × memory rate + request charges, after applicable shared allowances |
| Persistent data | Live data + indexes + replicas + retained revisions + backups, each multiplied by its storage/IO/operation rates |
| Delivery | Delivered regional bytes × egress/CDN rates + origin requests; cache hits still deliver bytes |
| Jobs | Accepted jobs × measured service time × resource rate, including failures, retries and idle/warm minimums |
| Observability/security | Retained log/trace volume, scans, keys, bot protection and alert delivery at the selected plan's rates |
| Resilience | Spare capacity, regional replicas, restore tests and failover traffic; do not cost only the healthy primary |

Show a low-activity month, a normal sustained month, a five-minute viral burst, a region-loss interval and the post-scale-down bill. The example 100,000 requests/s sustained for 30 days is 259.2 billion requests. At 10 kB per delivered response, it produces roughly 2.59 PB of traffic; it is not a nearly free workload. No dollar total is quoted without a dated provider/region/eligibility model. Scale-to-zero can remove some idle compute while registry images, databases, backups, reserved capacity and retained logs continue charging. Alerts notify; admission limits and bounded resource settings limit specific dimensions but do not create a universal account spending cap.

Independent cloud roles are Azure public static content, AWS deterministic manifest validation, and GCP immutable-snapshot retrieval benchmarking. The synthetic Azure reference is deployed on exact Free/Free hosting, with no paid linked services. The private AWS validator passed actual authenticated calls within verified free allowance, under an explicit $0.01 possible-charge approval. Its paid account has no enforced spending cap. A separately approved estimated $0.05 GCP experiment passed three authenticated health/retrieval/abstention checks against a three-document snapshot. Owned compute, registry and service accounts were removed before the original 30-minute deadline; 135 pre-existing resource payloads were preserved. Final charges remain unverified because billing reports lag. This smoke test does not measure held-out model quality. Verify shared account usage and billable dependencies before any future run; budget alerts are not a universal hard spend cap.

Personal cloud resources follow the shared Portfolio Hub convention with project-prefixed names and supported hub/project tags. The AWS function joins the existing regional tag-based resource group. Azure's earlier site remains in its original group, tagged in place; moving an existing resource solely for naming consistency requires separate authorization. Creating more groups or projects does not create additional free allowances.

Official programs change: [AWS Free Tier](https://aws.amazon.com/free/), [GCP free program](https://docs.cloud.google.com/free/docs/free-cloud-features), [Azure free services](https://azure.microsoft.com/en-us/pricing/free-services). Free credits expire; quotas, billing-account requirements and exclusions vary. Do not upgrade, activate billable services or remove a spending limit to complete architecture validation. Obtain explicit cost authorization and preserve a tested shutdown/export path.

## Validation and admission

Run stepped, spike and soak workloads against synthetic tenant distributions, including a hot tenant and long evidence fields. Test queue saturation, worker death, DB failover, cache loss, expired identity and regional unavailability. Monitor leakage, stale approvals and data loss—not just throughput. Compare load-generator capacity with target capacity.

Declare the verified envelope only after repeating a representative run with safety headroom and independent review. Admission should reject excess work early with retry guidance; do not silently accept unbounded jobs. A future 99% availability target is governed by [the SLO policy](OPERATIONS.md), not inferred from replica count.

| Proposed validation gate | Workload and required evidence |
|---|---|
| Baseline | 500, then 1,000 simultaneous users at the agreed six-request/minute mix; separately measure cold login, warm evidence reads, writes and imports |
| Spike | 10× admitted demand for five minutes, including reconnects and a hot tenant; observe startup rate, quota throttling and fair rejection |
| Recovery | Return to normal demand; verify bounded backlog drains, no lost accepted jobs, no duplicate effects and unchanged approval/source lineage |
| Soak | A representative business-day run plus a separately scheduled 24-hour run; monitor memory growth, disk/retention and model/cache behavior |
| Fault | Worker termination, database/cache outage, expired credentials, stale source and failed deployment; verify isolation, visible errors and recovery |
| Expansion | Increase toward 10k, 100k and 1M simultaneous-user scenarios only after the preceding measured envelope, cost approval and quota/cell readiness |

Record load-generator limits, user distribution, source/revision sizes, payloads, warm/cold state, p50/p95/p99, eligible failures, connection/queue saturation, cost and recovery time. Initial proposed acceptance uses the [SLO definitions](OPERATIONS.md), with zero cross-tenant disclosures, stale approvals or lost acknowledged durable work. Failed checks narrow the reported capacity envelope and identify the next engineering change; they do not justify silently relaxing the workload or success definition.
