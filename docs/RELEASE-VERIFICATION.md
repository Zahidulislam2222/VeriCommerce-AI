# Verified release evidence

[Website](https://vericommerce.zahidul-islam.com/) · [Evidence workspace](https://vericommerce.zahidul-islam.com/engine)

This report records observed releases on **2026-10-15**. Counts are checks/artifacts or generated test records, not customers, broad model accuracy or continuous uptime. Later source changes do not inherit a deployment claim from this report.

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
