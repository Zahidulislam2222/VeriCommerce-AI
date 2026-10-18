# Verified release evidence

[Website](https://vericommerce.zahidul-islam.com/) · [Evidence workspace](https://vericommerce.zahidul-islam.com/engine)

This report records observed checks through **2026-10-18**. Counts are checks/artifacts or generated test records, not customers, broad model accuracy or continuous uptime. Later source changes do not inherit a deployment claim from this report.

## Expanded application release — 2026-10-18

Current release `20261018-phase3-01` follows the integrated expansion
`20261018-phase1-01`. Final source passed140/140backend/infrastructure checks with
real PostgreSQL and pinned CPU retrieval, with zero failures, errors or skips.
Earlier frontend checks passed11/11domain and80/80localChrome cases; the preceding
expansion passed46/46live desktop/mobile cases with zero skipped, flaky or failed.
The current release changes deployment quota configuration with identical
application bytes; current real-store flows were checked separately.

Types, lint, Bandit, Gitleaks, official Semgrep audit rules, production build and
independent source review passed. A336-file public-source inventory is hash-bound;
Semgrep ran120official rules across296targets with zero findings/errors. Private
provider state remains ignored. All228server artifact hashes match; eight HTTPS
routes and four healthy constrained services passed after recovery. A real
1,048,576-byte catalog upload returned202, completed in the worker and produced a
cited answer; a1,048,577-byte upload returned413.

Actual populated off-server AES-256-GCM recovery reproduced all26table counts and
payload hashes, including249source revisions and15drafts in36workspaces.
Restricted-role, absent-context and36cross-tenant denial checks passed; the
primary database stayed unchanged. Original/encrypted/decrypted archives were
retained with a separately recorded private key. Actual rollback to the preceding
configuration release and forward recovery returned readiness200, preserved all
three persistent approved drafts and database mount identities, then passed exact
228artifact parity. Identical application bytes mean this does not prove rollback
to the older pre-account schema/runtime. No automated backup cadence is claimed.

The dedicated Shopify app was installed through the real OAuth flow with exactly
`read_products`. Four product/uninstall webhook topics are registered. Actual
catalog sync imported23parents and38variants,23sources and206passages. Exact SKU
and color constraints selected the correct child before retrieval; a cited
answer resolved the current passage. An agent inspected three current citations
in an FAQ draft; export returned409before approval, then approval/export200with
unchanged text and no publishing. Configuration and fake-provider replay tests
do not establish actual Shopify event delivery, which remains unobserved.

The AWS validator was deployed from the independently reviewed three-resource
plan. Four initial and four final-source bounded authenticated synchronous calls
returned200 and matched the local validator, with no automatic retries. The final
ZIP matches current source. Native configuration and code hashes
were fenced before each call. The owner explicitly approved possible usage up to
$0.01. Verified free allowance covered the scenario; immediate usage readings
were unchanged but may lag. This is not a provider-enforced spending cap.

The actual Azure synthetic reference is published on Static Web Apps Free/Free:
[reference site](https://brave-mushroom-04cc6610f.5.azurestaticapps.net).
Nine actual desktop/mobile checks passed, including browser search, abstention,
overflow/error checks and snapshot tamper rejection. Six served assets exactly
match local hashes. Azure consumes the seventh configuration file; its security
headers, API404 and MIME behavior were verified instead of claiming an observable
remote byte hash. No linked services, custom domains, paid CDN or repository build
integration were added; the two previously inventoried unrelated resource
payloads matched. Supported own resources have project/hub tags. The existing
Azure site stays in its earlier group; the AWS function belongs to the existing
regional Portfolio Hub resource group. No account/project migration was performed.

The frozen synthetic corpus contains 30 products, 120 unique original schematic
images and 200 questions, including 64 test questions from held-out families.
Independent agent review was performed at the owner's request; human validation
remains pending. Measured quality/latency and corpus limitations are in
[data/models/evaluation](DATA-MODELS-EVALUATION.md).

The owner separately approved an estimated$0.05one-time GCP experiment because
existing registry storage exceeded the shared free allowance. Actual IAM-protected
Cloud Run health, retrieval and abstention returned200and matched the same local
image/snapshot. The entire experiment was bounded to at most eight requests,
including failed attempts, without automatic retries. Its three public synthetic
documents establish a contract smoke test, not the64-question/four-method quality
evaluation. All owned temporary Run, repository and service accounts were removed
at00:32:35UTC before the original00:35:05deadline; native inventory confirmed all
135baseline resource payloads unchanged. Free API metadata remains enabled as
planned. Final charges remain unverified due to delayed billing reports.

The application features for phases1–5 were delivered together and followed by a
quota configuration release. This is not five separately evidenced sequential
phase deployments. The owner delegated dataset/accessibility review to an agent;
human validation and actual incremental Shopify event delivery remain distinct
original acceptance limits. Graph-versus-hybrid quality comparison and automatic
backup scheduling/retention are also unperformed plan items. No human-review or
full original-plan completion claim is made.

## Prior engineering release 0.2.0 — 2026-10-15

Release `20261015-release-01` deploys the frontend and evidence backend together on the existing server. Public source is MIT-licensed under Zahidul Islam. Application/CI source commit: `4d206d4c6de8d6fd3d9c0a53b8c90ffd071cb44e`.

| Gate | Observed result |
|---|---|
| Hosted quality/security | Both passed: [quality run](https://github.com/Zahidulislam2222/VeriCommerce-AI/actions/runs/38761724332), [security run](https://github.com/Zahidulislam2222/VeriCommerce-AI/actions/runs/38761724156) |
| Hosted application checks | 49 PostgreSQL/CPU/infrastructure checks, 11 frontend checks, 44 browser journeys; zero skipped |
| Types/lint/build/security/review | Passed for the reviewed application/CI source; independent source/infrastructure/documentation/recovery review ACCEPT |
| Production dependency advisories | Zero reported frontend production advisories; all 41 pinned Python runtime packages returned zero known advisories on 2026-10-15 |
| Initial deployment | 84 local/archive/live artifact hashes and 28 HTTPS checks passed |
| Populated restoration | 29 generated test workspaces, 206 source revisions and 13 drafts; all 11 table payload counts/hashes matched, with restricted-role/no-context/cross-tenant RLS probes |
| Actual runtime rollback/forward | Browser observed API 0.1.0 after rollback and API 0.2.0 after forward recovery, both HTTP 200; the original approved draft retained its exact SHA256 |
| Final post-recovery verification | Eight routes, four healthy constrained services, trusted TLS and 84-file parity passed; strict inventory verified exact files; all 16 observed gateway-file hashes unchanged |
| Final post-recovery live browser suite | 44/44 actual public desktop/mobile cases passed in 4.8 minutes; zero skipped, flaky or failed |

The first forward attempt stopped at strict file-set verification. Immediate read-only replay verified all 84 hashes and the exact file set including its manifest, without extras, missing files or symlinks. Retrying the unchanged reviewed operator passed. The original failure's cause is unverified; no file removal or weakened integrity gate was used to obtain recovery.

Restoration counts describe a tested snapshot, not customers or a fixed current live row count. Recovery rehearsals do not establish an automated backup cadence, RPO/RTO or rolling availability. Current feature boundaries and future targets below remain unchanged.

## Public-page release

Fourteen dedicated pages, shared responsive navigation/footer, owner-confirmed contact, accurate pricing/privacy/storage information and branded HTTP404 were deployed while preserving the prior evidence runtime.

| Gate | Observed result |
|---|---|
| Acceptance |8/8 public-site criteria |
| Domain/data |8/8 checks |
| Local browser |32/32 desktop/mobile checks |
| Live browser |44/44, zero skipped/flaky/failed |
| Final scoped visual refresh |2/2 composition checks |
| Deployment safety |15 regressions |
| Types/lint/build |TypeScript, ESLint without warnings, production build passed |
| Security/review |Gitleaks, exact-private-value audit, applicable Semgrep rules and independent ACCEPT |
| Artifact/public checks |84 local/archive/live hashes;28 HTTPS route/asset/API/private-path checks |

Actual flows included every public deep link, navigation, storage controls, accessibility, citations, durable approval, changed-source rejection, session recovery, maximum-length fields and branded404. The API/worker/database identities, start times and backend image stayed unchanged. All16 observed gateway configuration files retained hashes; the same browser's approved draft retained its prior SHA256.

No new actual database restore or runtime rollback was executed for this frontend-only release. Its scoped rollback had regression coverage and retained the prior recovery-capable release.

## Evidence-core release

Frontend criteria 8/8, backend criteria 10/10 and core-interface criteria 8/8 acceptance criteria passed. Observed checks included 24 local PostgreSQL/HTTP/ONNX integrations, 28 public browser cases, 23 deployment-safety regressions and 5 domain/configuration checks. TypeScript/Mypy, ESLint/Ruff, Bandit/Gitleaks/Semgrep, frontend/container builds and fresh independent review passed.

Target-runtime health, trusted TLS, eight public routes, 83 artifact hashes, private-port isolation and four healthy constrained containers were verified. Hardened nonroot/read-only Nginx and CPU model readiness ran on the actual target because a local Docker daemon was unavailable.

A populated dump restored into a separate database with exact table payload hashes and restricted-role/RLS probes: 15 test workspaces,106 source revisions and 7 drafts. Actual runtime rollback served previous HTML and disabled the API; forward recovery restored functionality and an approved draft's exact hash. Final parity/health checks passed again afterward.

## Interpretation and remaining gates

Answers are retrieved quotations, not complete entailment verification. Ten curated generated regression cases passed in keyword and hybrid configurations; that is neither general accuracy nor evidence of hybrid improvement. No current 1M-user capacity, measured 99% availability, automated backup-cadence/RPO/RTO, business conversion uplift or full legal/security certification is established.

The prior release lacked accounts/roles, document/image ingestion and Shopify
authorization. These are implemented in the expanded application above;
phase-specific remaining acceptance work stays visible. Shopify publishing and
fine-tuning remain future work. Runtime retrieval uses existing-server CPU
without paid model API calls.

For new releases, record candidate-specific tests, public behavior, review, parity and recovery scope after they actually run. See [deployment](DEPLOYMENT-CI.md), [operations](OPERATIONS.md) and [roadmap](BUILD-PLAN.md).
