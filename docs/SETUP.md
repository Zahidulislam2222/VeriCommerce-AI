# Local setup and verification

Use a clean local checkout and a dedicated development database. Never point migration, test or load-generation commands at a shared production database. Keep credentials out of examples, command arguments and reports.

## Prerequisites

Use Node.js supported by the pinned Vite dependency, npm, CPython 3.12 on Linux x86_64 for the supplied backend hash lock, and PostgreSQL 17. Dependency locks and the runtime image are authoritative for a release. Other Python versions/platforms require a separately resolved and verified lock; do not assume the supplied wheel hashes are portable. Docker/Compose are optional for local source execution and required for container deployment. Browser checks use installed Chrome through Playwright. [Vite requirements](https://vite.dev/guide/), [FastAPI execution](https://fastapi.tiangolo.com/deployment/manually/).

## Frontend

```sh
npm ci
cp .env.example .env
npm run dev
```

Only public flags belong in `VITE_` variables. `DEV_API_TARGET` selects the development proxy; the browser requests same-origin `/api`. Put the actual Vite origin in the backend allowlist. `TEST_BASE_URL` independently selects the browser-test origin. The local browser workspace works without the API; `/engine` needs API and worker.

## PostgreSQL and protected settings

Create a dedicated empty database through your PostgreSQL administrator tool. Migration creates/configures the restricted runtime role from its DSN and applies hash-verified SQL migrations. It refuses the same administrator/runtime role and does not create the database itself.

Copy `backend/.env.example` to an ignored protected settings file. Populate `VC_DATABASE_URL` and `VC_MIGRATION_DATABASE_URL` privately; never paste them into shell history. Set `VC_SETTINGS_FILE` through your process environment. Deployment uses separate runtime and migration secret files.

For local HTTP only, set `VC_COOKIE_SECURE=false` in protected settings. Keep it true for HTTPS deployment. Set `VC_ALLOWED_ORIGINS` to the exact local frontend origin; do not use wildcard origins.

## API and worker

From `backend/`, create/activate a virtual environment, then:

```sh
python -m pip install --require-hashes -r requirements.lock
python -m vericommerce_core.migrate
python -m uvicorn vericommerce_core.main:app --host 127.0.0.1 --port 8081
```

In a second terminal with the same runtime settings:

```sh
python -m vericommerce_core.worker
```

The local port above matches the safe example proxy. Change both through environment/start configuration when reserving another port. The worker executes queued ingestion/drafting, recovers leases and cleans expired workspaces. Check `/api/healthz` and `/api/readyz`, then open `/engine`.

## Optional CPU embeddings

Keyword retrieval works without a model. For hybrid retrieval, configure the reviewed model/repository/revision/file from `backend/.env.example`, a writable cache and enabled embeddings. For explicitly authorized initial download only, enable `VC_EMBEDDING_DOWNLOAD_ALLOWED` and run:

```sh
python -m vericommerce_core.warmup
```

Disable download allowance afterward. Normal startup uses the exact cached revision. In read-only containers, put `HF_HOME` and `HF_XET_CACHE` under owned writable cache directories. A warm cache does not prove empty-cache downloading works. This public model needs no provider key.

## Verification

Full media and reduced-motion browser checks require the existing hero MP4 and `VITE_HERO_VIDEO=true` in the frontend test environment before Vite starts. The copied safe example defaults to false; enable the flag for the full suite. Do not assume a private local `.env` exists in clean CI.

From repository root:

```sh
npm test
npm run typecheck
npm run lint
npm run build
npm run test:browser
```

The full browser suite needs API/worker and uses isolated generated data. Do not run capacity tests against the public origin. Development tools are in `backend/requirements-dev.txt`; install them in the development environment, then from `backend/`:

```sh
python -m ruff check vericommerce_core
python -m mypy vericommerce_core
python -m pytest
python -m bandit -r vericommerce_core
```

Backend integration tests require protected `VC_TEST_ADMIN_DATABASE_URL` and `VC_TEST_DATABASE_URL` values pointing to a dedicated database with the `_test` suffix. The fixture drops/recreates its public schema; never use a valuable database. The CPU integration case also requires an explicitly prewarmed `VC_TEST_EMBEDDING_CACHE_DIR`. Inspect `tests/backend/` first. Missing database, model, Chrome or security tools are missing gates, not passes. Follow [deployment](DEPLOYMENT-CI.md) for security scans and independent review.
