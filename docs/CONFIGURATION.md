# Configuration and secret boundaries

Operational values have one owner. Maintained content is data, credentials are protected secrets, and API/schema syntax is a compatibility contract.

| Boundary | Owner | Treatment |
|---|---|---|
| Browser behavior | `src/config.ts`, root `.env.example` | Validated public flags; never secrets |
| Website/content | `src/data/` | Versioned JSON with route/source validation |
| API/worker | `backend/vericommerce_core/settings.py` | Pydantic `VC_` environment settings |
| Backend names/examples | `backend/.env.example` | Safe examples, not production values |
| Orchestration | `infra/core/compose.yaml`, example environment/config | Typed release rendering owns environment values |
| Dataset/policy | `backend/data/` | Reviewed versioned inputs |
| Protocol | API paths, HTTP semantics, SQL schema | Compatibility review before changes |

`VC_SETTINGS_FILE` selects a protected dotenv file. API/worker receive only the restricted database DSN. Administrator credentials go only to migration. Private recovery material, local environment files and operator state stay out of public artifacts/history.

## Setting groups

| Group | Principal settings |
|---|---|
| API metadata | `VC_API_VERSION`; validated maintained policy owns the OpenAPI title, service label and retrieval/draft copy; protocol errors remain in code |
| Persistence/origin | `VC_DATABASE_URL`, `VC_MIGRATION_DATABASE_URL`, `VC_ALLOWED_ORIGINS` |
| Access | Cookie name/security, `VC_SESSION_TTL_SECONDS`, `VC_MAX_ACTIVE_SESSIONS` |
| Abuse/input | `VC_MAX_BODY_BYTES`, `VC_REQUESTS_PER_MINUTE`, `VC_SESSION_CREATIONS_PER_HOUR` |
| Workspace quotas | Maximum products, sources, passages, revisions, drafts, jobs, audit events and evaluations |
| Retrieval | Search count/maximum, lexical score floor, reciprocal-rank-fusion constant, dense similarity floor |
| Database bounds | Connection timeout and statement timeout |
| Worker | Poll interval, lease, attempts, retry interval, tenant batch and heartbeat |
| Model/cache | Enable/download flags; model/repository/revision/file/cache/thread/batch |
| Maintained inputs | Seed, policy, evaluation and migration paths |
| Local bind | `VC_API_HOST`, `VC_API_PORT` and explicit server start configuration |

Complete setting names/defaults stay in the backend example rather than being duplicated here. Validation requires an immutable model revision, bounded limits, default search count within its maximum, and worker tenant coverage at least equal to allowed active workspaces. Quotas are admission rules, not throughput measurements.

Deployment reserves a loopback port and nonoverlapping network from actual inventory. Its dynamic pool excludes the fixed trusted proxy address. Cache and Nginx temporary paths must be writable under the actual nonroot UIDs/read-only filesystem. Examples do not authorize shared-service mutation.

Every configuration change updates its example, validation, regression coverage and release evidence. Audit public artifacts for credentials, private addresses, workstation paths and unintended environment output.
