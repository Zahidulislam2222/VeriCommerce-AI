# Verified release evidence

[Website](https://vericommerce.zahidul-islam.com/) · [Evidence workspace](https://vericommerce.zahidul-islam.com/engine)

This report records observed releases on **2026-10-15**. Counts are checks/artifacts or generated test records, not customers, broad model accuracy or continuous uptime. Later source changes do not inherit a deployment claim from this report.

## Engineering release 0.2.0 — latest observed results

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

Accounts/roles, Shopify authorization/publishing, document/image ingestion, fine-tuning and actual AWS/GCP/Azure deployments remain future work. The current runtime uses existing-server CPU retrieval without paid model API calls.

For new releases, record candidate-specific tests, public behavior, review, parity and recovery scope after they actually run. See [deployment](DEPLOYMENT-CI.md), [operations](OPERATIONS.md) and [roadmap](BUILD-PLAN.md).
