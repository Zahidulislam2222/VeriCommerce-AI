# Optional synthetic cloud adapters and encrypted recovery

These isolated packages support the project's independent cloud experiments.
Azure Free hosting, the private AWS validator and a temporary authenticated GCP
contract service have actual deployment receipts. The GCP experiment was cleaned
up within its approved window. Local tests alone establish no cloud deployment.
They never connect to the merchant database,
Shopify, a paid model API, or another project's resources.

`config.json` is the typed settings boundary for adapter data, limits and backup
budgets. `snapshot.json` and its SHA256 file bind a small synthetic lexical search
fixture. This fixture is a runtime smoke test; it is not the held-out product-family
evaluation corpus or an independent quality result.

## Operations

From the repository root with application dependencies installed:

```sh
python -m infra.cloud.cli validate /path/to/synthetic.zip
python -m infra.cloud.cli benchmark /path/to/query.json
python -m infra.cloud.cli package-lambda /path/to/new-validator.zip
python -m infra.cloud.cli package-static /path/to/new-static-directory
python -m infra.cloud.cli encrypt /path/to/database.sql.gz /path/to/new.vcbackup --key-file /private/key.bin
python -m infra.cloud.cli decrypt /path/to/new.vcbackup /path/to/new-restored.sql.gz --key-file /private/key.bin
python -m infra.cloud.cli retention-plan /path/to/backups
```

The key file contains exactly 32 random binary bytes. Store it separately from
archives in an approved private location, record its actual value in ignored
`CREDENTIALS.md`, and protect it with filesystem permissions. The CLI takes its
path; it never accepts or prints key material. Each encryption uses a fresh random
nonce prefix and an authenticated chunk counter. Changing headers, chunk order,
contents, key, length or trailer fails before plaintext publication. Output is
atomic, private and refuses to overwrite. The original backup is retained.
The key must be current-user-owned with POSIX mode `0600`; use a native private
filesystem when mounted filesystem permissions cannot enforce that boundary.

Successful decryption proves authenticated archive integrity, **not database
recovery**. Restore the decrypted dump into a separate local rehearsal database,
compare table payload hashes and row counts, test restricted-role/tenant isolation,
and retain that release-bound evidence. No automatic deletion or scheduler is
enabled. Retention only proposes older archives; preserve them until a recovery
and retention policy is explicitly accepted. Local-PC copies are off-server but
do not establish continuous backup/RPO/RTO compliance.

## Cloud boundaries

`tofu/azure`, `tofu/aws` and `tofu/gcp` use exact registry-verified providers.
State and credentials stay ignored/private. Prepare an immutable reviewed artifact,
use the matching example variables and inspect a local plan. Do not apply any
bundle until account eligibility, resource ownership, provider registration,
allowances and costs have been verified for that account. Possible charges require
a conspicuous warning and fresh owner approval. Billing activation is excluded.
The separate GCP bootstrap makes its prerequisite API/resource changes explicit;
review it separately from the image-pinned service plan. A missing prerequisite is a gate.

Future project resources share the verified Portfolio Hub account/project/
subscription and supported hub/project tags. Names retain the owning project
prefix. Azure defaults to the existing `portfolio-hub` resource group; the earlier
deployed project group is retained without migration. The displayed GCP project
name must be resolved to its actual ID. These defaults authorize no provisioning.

- Azure: the existing shared hub resource group; only Static Web Apps **Free/Free**.
  Group creation is disabled by default. Explicit `create_resource_group=true`
  creates only the explicitly named group metadata and that Free static site;
  otherwise supply the existing hub group. Legacy owned `vericommerce-` groups
  remain accepted for recovery without moving existing sites. Review the exact
  plan before applying either path.
  No linked Functions, App Service, database, custom domain, logging service or
  build pipeline. Deploy only `static/` plus the reviewed public snapshot. Provider
  automatic resource registration is disabled. Free bandwidth overage is
  unavailable; exhausting the quota stops serving. Subscription-level charges
  from existing resources are separate.
- AWS: one deterministic Lambda ZIP validator, one minimal service trust role,
  and an invocation grant to one configured exact trusted IAM user or role. No function URL,
  API Gateway, event source, VPC/NAT, model, storage or log-write permission.
  Three-second/128MiB/default one-concurrency limits bound resource use; they do not
  guarantee zero charges on a paid account. Invoke `infra.cloud.validator.handler`
  from a ZIP containing its package, settings and configuration only.
  Reserved concurrency may be unsupported on small accounts. An explicit
  `allow_unreserved_low_quota=true` exception requires freshly observed account
  concurrency at most10; the default remains reserved1. That exception removes
  the per-function concurrency cap, so only an explicitly bounded sequential
  synchronous harness is authorized. Never add public URLs/triggers or broaden
  the named IAM principal. Shared account free allowances must be checked first.
- GCP: verified Cloud Run prerequisites and explicit service accounts, a
  prebuilt digest-pinned immutable CPU image, request-based billing, minimum zero,
  maximum one, one concurrent request and a five-second timeout. Only the named
  IAM invoker service account receives `roles/run.invoker`; no `allUsers` binding.
  The image serves `infra.cloud.benchmark:app` with a configured ASGI server.
  Registry, build, logging, networking and account state are separate cost gates.
  Normal service deletion protection remains enabled. An explicit experiment
  cleanup switch permits removal of only the reviewed temporary owned service.
  Existing public IAM bindings must be absent before deployment; this additive
  bundle cannot remove unrelated policies. Image access credentials never enter
  the service's synthetic request/response contract.

Build the GCP candidate from the repository root with `infra/cloud/Dockerfile`
and an explicitly reviewed digest-pinned `PYTHON_IMAGE` build argument. Its tiny
hashed runtime includes only Uvicorn/Click/h11; no model, database driver,
merchant credentials or backup key enters the image. The configured Cloud Run
command selects the ASGI module and container port; access logs are disabled.
Use that image's verified digest as the infrastructure input. Actual container
build, registry publication and Cloud Run rollout are separate gates.

Lambda requires exactly `manifest.json` and `draft.json`; packages are never
extracted. The manifest declares `schema_version`, `classification` and
`draft_sha256`. The draft has `product_id`, `body` and bounded `evidence`; each
evidence item has `source_id`, `quote`, `sha256`. The body must exactly equal its
cited quotations. This checks deterministic consistency, not semantic truth or
authorization to publish. Inputs must be permitted synthetic data; heuristic
private-content rejection is an extra boundary, not a general DLP guarantee.

Cloud Run exposes GET `/health` and POST `/benchmark` with JSON
`{"query":"graphite headphones","limit":3}`. Its identity boundary is Cloud Run
IAM. The adapter is intentionally not mounted in the public merchant API.

## Current account gates

Actual Azure Free hosting passed nine desktop/mobile checks and six served asset
hashes; its consumed configuration was checked through effective behavior. The
AWS private validator passed four sequential authenticated calls matching local
verdicts. The owner approved possible AWS charges up to $0.01 and an estimated
$0.05 GCP experiment with cleanup; neither is a provider-enforced hard cap. The
GCP experiment passed three actual health/retrieval/abstention checks matching the
local image on the same three-document snapshot. Its owned Run service, repository
and service accounts were removed before the original30-minute deadline; all135
baseline resource payloads stayed identical. This is a synthetic contract smoke
test, separate from the local64-question/four-method quality evaluation. Final
billed cost is unverified because reporting lags. Native identity/inventory results, account eligibility,
spending protection and allowance evidence are private.
Credits on a paid account do not provide a spending cap. A disabled API stays
disabled until its prerequisite change is verified and authorized; an unavailable
inventory is recorded as incomplete. Azure's isolated Free static SKU has no bandwidth overage, but that
does not cap unrelated account-wide spending. Actual provider deployment remains
a separate acceptance gate.

Official references: [AWS Free Tier metadata](https://docs.aws.amazon.com/us_en/awsaccountbilling/latest/aboutv2/tracking-free-tier-usage.html),
[AWS Resource Explorer scope](https://docs.aws.amazon.com/resource-explorer/latest/userguide/using-search.html),
[Azure Free quotas](https://learn.microsoft.com/en-us/azure/static-web-apps/quotas),
[Azure provider registration](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs),
[Cloud Run pricing](https://cloud.google.com/run/pricing),
[Cloud Run authentication](https://cloud.google.com/run/docs/authenticating/service-to-service),
[AES-GCM nonce requirements](https://cryptography.io/en/stable/hazmat/primitives/aead/).

For the complete application, see [architecture](../../docs/CORE-ARCHITECTURE.md), [release evidence](../../docs/RELEASE-VERIFICATION.md) and [capacity/cost planning](../../docs/SCALABILITY-AND-COST.md). These small independent contracts do not establish million-user serving capacity. Scaling or replicating them requires a new workload, allowance, dependency-cost and residency assessment; retained storage and logs can continue charging after compute scales down.

Future architecture gives suitable AWS/GCP/Azure services priority within verified shared allowances, while assessing a hybrid boundary before paid expansion. Keep heavy model execution or persistent workloads on existing capacity when that is the measured economical choice. A cloud placement record must identify the component, location, reason, dependencies, quota/cost limits and removal/export procedure. The current separate contracts are evidence for their own workloads; they do not authorize a production-data migration or a new provider deployment.
