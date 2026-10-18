# Deployment, CI and release engineering

The public deployment uses immutable frontend artifacts and a separately controlled API/worker/database runtime. Existing infrastructure is reused. This document is an operating contract, not authorization to provision resources or access another environment.

## Local-first release sequence

1. Inventory the owned application and shared resources using native tools. Compare the active artifact/source manifest with the local baseline; reconcile newer remote changes before editing.
2. Write acceptance criteria; implement locally with one configuration owner and reviewed data. Exclude private credentials, operator state, backups and project records.
3. Run unit/domain, real PostgreSQL/CPU integration, types, lint, secret/security scans, production build and actual browser journeys. A missing gate remains missing.
4. Obtain fresh independent review against criteria. Verify dependency registry/source, lock hashes, image digests and model revision.
5. Prepare a unique immutable release ID, exact allowed file set, SHA256 manifest and archive; restore the archive locally and verify every hash.
6. Preflight actual target ports/networks/disk/UIDs/cache/temp paths, active pointer and protected backups. Validate pinned containers under real read-only/nonroot constraints.
7. Start the candidate, migrate only through its separate credential path, warm the exact model where authorized, check readiness and exercise the actual flow before promotion.
8. Switch only the owned gateway route. Verify trusted TLS, public routes/private-path blocking, all artifact hashes, persistent content and unchanged unrelated services.
9. Retain the previous compatible release and recovery evidence. Record criteria/gates/behavior/review; do not infer success from upload completion.

No source edit is made directly on the live server. A frontend-only release must preserve the frozen backend/image and database when backend changes are excluded. Do not accidentally package unverified working files.

## Container and network boundaries

Core Compose runs static Nginx, API, worker and PostgreSQL. Only web publishes a loopback port behind the existing TLS gateway; database is private. Nonroot users, read-only roots, dropped capabilities, resource bounds, health checks, tmpfs and owned persistent volumes constrain execution.

Dynamic IPAM excludes the reserved trusted proxy address. Redirect all enabled Nginx temporary directories to writable tmpfs. API trusts forwarded addresses only from the dedicated proxy. Do not infer a real client IP from an arbitrary forwarded header.

Runtime secrets mount outside images/archive; migration gets a separate admin DSN. Model cache persists, normal startup forbids downloads, and empty-cache preparation configures all downloader cache roots. Public examples need environment-specific rendering and do not contain real credentials.

## CI quality contract

Automated CI should reproduce frontend domain/type/lint/build checks, backend tests against a real dedicated PostgreSQL service, CPU model readiness, security scans and browser journeys against API/worker. Tests must fail rather than silently skip a required integration dependency. Store only sanitized short-lived reports; never upload settings, database dumps or credentials.

Hosted workflow configuration and a green hosted run are different evidence. Local gates have been observed; a remote hosted run must be linked after publication before claiming CI executed there. Inspect `.github/workflows/` for the current implementation and triggers.

| Configured workflow/job | Scope |
|---|---|
| `quality` / `application` | Real PostgreSQL and CPU-model checks, backend/infrastructure tests, frontend types/lint/domain/build, lock/license checks and Chrome journeys against API/worker |
| `security` / `secret-and-code` | Full-history Gitleaks, Bandit and official Semgrep security-audit rules |

Both target standard Ubuntu24.04 runners with read-only repository contents permission, public-repository guards, and push-to-main/pull-request/manual triggers. There is no deployment, paid API, cache upload or artifact upload step. The quality job explicitly sets `VITE_HERO_VIDEO=true` for full media/reduced-motion tests instead of assuming a developer’s ignored local `.env` exists. Action references and scanner inputs are pinned in the workflows. A hosted success claim still requires an actual run URL and matching commit.

The browser job serves the already-built production artifact and retains the configured same-origin API proxy. This matters for request-count contracts: development React StrictMode intentionally replays initial effects, while the deployed production runtime does not. An isolated comparison reproduced the four earlier development-only count failures and passed the same unchanged cases with production serving. Keep StrictMode, exact security assertions and no-skip/no-retry gates; test the artifact that will be released. [React StrictMode](https://react.dev/reference/react/StrictMode), [Vite production serving and proxy configuration](https://vite.dev/config/preview-options.html#preview-proxy).

Use minimal repository permissions, pinned verified actions/dependencies, separate untrusted pull-request checks from privileged deployment, and no production secrets in forked jobs. Protect release environments and prefer short-lived workload identity when introducing cloud automation. Never interpolate untrusted PR text into shell code. GitHub recommends least privilege and protecting against untrusted-code execution: [secure workflow use](https://docs.github.com/en/actions/reference/security/secure-use).

CI must not deploy or incur paid model usage merely because tests passed. Hosted minutes, artifacts, storage, image registry and cloud builds have independent allowances. Do not enable a paid AI reviewer by default.

## Rollback and data compatibility

Frontend rollback changes only the scoped web artifact/pointer after drift checks. Core image rollback preserves database/cache volumes and requires compatible schema. Never delete volumes, prune shared networks or force an old schema onto newer data to make rollback appear successful.

For corrupted/incompatible data, preserve the primary and restore independently; compare schema, all-table payload hashes, runtime grants and RLS. Reapply deletion records before exposure. Record what was actually restored versus what was only tested in regressions. See [operations](OPERATIONS.md).

Public release reports contain sanitized counts and outcomes. Deployment access, server paths, private addresses, secrets and full incident narrative remain private.
