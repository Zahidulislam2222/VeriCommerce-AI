# Verified release evidence

[Website](https://vericommerce.zahidul-islam.com/) · [Evidence workspace](https://vericommerce.zahidul-islam.com/engine)

This report records observed checks through **2026-10-18**. Counts are checks/artifacts or generated test records, not customers, broad model accuracy or continuous uptime. Later source changes do not inherit a deployment claim from this report.

## Expanded application release — 2026-10-18

Current release `20261018-phase5-02` follows the integrated expansion
`20261018-phase1-01`. Final source passed 142/142 backend/infrastructure checks in a clean locked environment with
real PostgreSQL and pinned CPU retrieval, with zero failures, errors or skips.
The 45-package production lock and direct requirements agree; clean installation
and pip compatibility checks passed. An earlier hosted installation failed on a
direct Pillow 13 pin versus locked 12.3; the correction retains the deployed 12.3
runtime and adds an actual-repository regression. Earlier 140 local checks used a
different Pillow environment and are superseded by this clean run.
Final hosted [quality](https://github.com/Zahidulislam2222/VeriCommerce-AI/actions/runs/39085575603)
and [security](https://github.com/Zahidulislam2222/VeriCommerce-AI/actions/runs/39085577739)
passed on source `f960239df0210616ebee065e86e1c975bd3d1e54`: 142 backend/infrastructure,
11 domain and 80 desktop/mobile browser checks, with zero skipped tests and zero browser retries. The backend reported two warnings. The browser workflow serves
the built production artifact; a regression guards that boundary. Earlier failed
installation/development-artifact runs remain historical failures.

Earlier frontend checks passed 11/11 domain and 80/80 local Chrome cases; the preceding
expansion passed 46/46 live desktop/mobile cases with zero skipped, flaky or failed.
The follow-up releases configured the catalog quota and aligned direct
requirements with the deployed lock. Application code and frontend assets are
unchanged; current real-store flows were checked separately.

Types, lint, Bandit, Gitleaks, official Semgrep audit rules, production build and
independent source review passed. A 336-file public-source inventory is hash-bound.
The original full Semgrep scan ran 120 official rules across 296 targets with zero
findings/errors; scoped supplements covered the dependency/workflow corrections
and final prose. Private
provider state remains ignored. All 228 server artifact hashes match; eight HTTPS
routes and four healthy constrained services passed after recovery. A real
1,048,576-byte catalog upload returned202, completed in the worker and produced a
cited answer; a 1,048,577-byte upload returned413.

Current release pre/post-migration populated restoration reproduced all 26 table
counts and payload hashes: 36 workspaces, 251 source revisions and 16 drafts, with
restricted-role, absent-context and 36 cross-tenant denial checks.

The earlier phase3 off-server AES-256-GCM snapshot separately reproduced all 26
table counts and payload hashes, including 249 source revisions and 15 drafts in
36 workspaces. That dated snapshot precedes the two webhook events and new draft.
Restricted-role, absent-context and 36 cross-tenant denial checks passed; the
primary database stayed unchanged. Original/encrypted/decrypted archives were
retained with a separately recorded private key. Actual rollback to the preceding
configuration release and forward recovery returned readiness 200, preserved all
three persistent approved drafts and database mount identities, then passed exact
228 artifact parity. Unchanged application code means this does not prove rollback
to the older pre-account schema/runtime. No automated backup cadence is claimed.

The dedicated Shopify app was installed through the real OAuth flow with exactly
`read_products`. Four product/uninstall webhook topics are registered. Actual
catalog sync imported 23 parents and 38 variants, 23 sources and 206 passages. Exact SKU
and color constraints selected the correct child before retrieval; a cited
answer resolved the current passage. An agent inspected three current citations
in an FAQ draft; export returned 409 before approval, then approval/export 200 with
unchanged text and no publishing. Following fresh owner approval, two temporary
Admin title saves generated real HMAC-verified product-update events. Parent and
child records changed and restored; the old draft correctly returned 409. A
subsequent full sync produced identical product records to the incremental state,
with 61 products/23 sources and zero duplicates. The original title was restored.
The connector retains read_products and made zero product-write calls; the two
manual verification writes are separate from app publishing. A fresh three-citation
FAQ was then reviewed, approved and exported successfully against current evidence.
After token expiry, another actual sync refreshed authorization successfully and
completed with the same read_products scope.

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

The owner separately approved an estimated $0.05 one-time GCP experiment because
existing registry storage exceeded the shared free allowance. Actual IAM-protected
Cloud Run health, retrieval and abstention returned 200 and matched the same local
image/snapshot. The entire experiment was bounded to at most eight requests,
including failed attempts, without automatic retries. Its three public synthetic
documents establish a contract smoke test, not the 64-question/four-method quality
evaluation. All owned temporary Run, repository and service accounts were removed
at 00:32:35 UTC before the original 00:35:05 deadline; native inventory confirmed all
135 baseline resource payloads unchanged. Free API metadata remains enabled as
planned. Final charges remain unverified due to delayed billing reports.

The application features for phases 1–5 were delivered together and followed by a
quota configuration release. This is not five separately evidenced sequential
phase deployments. The owner delegated dataset/accessibility review to an agent;
human validation remains an original acceptance limit. Graph-versus-hybrid quality comparison and automatic
backup scheduling/retention are also unperformed plan items. No human-review or
full original-plan completion claim is made.

The exit-clause audit records 33 met and one owner-delegated agent review out of
34, with the separately approved two manual title saves explicitly disclosed.

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
