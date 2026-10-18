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
python -m uvicorn vericommerce_core.main:app --host 127.0.0.1 --port 8081 --no-access-log
```

In a second terminal with the same runtime settings:

```sh
python -m vericommerce_core.worker
```

The local port above matches the safe example proxy. Change both through environment/start configuration when reserving another port. The worker executes queued ingestion/upload/drafting, recovers leases and cleans expired temporary workspaces. Account workspaces persist separately. Check `/api/healthz` and `/api/readyz`, then open `/engine`. Keep OAuth callback query strings out of proxy/error logs; the provided deployment uses sanitized site logging.

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

The full browser suite needs API/worker and uses isolated generated data. Do not run capacity tests against the public origin. In a separate terminal, after building, serve the artifact using the same command as [the quality workflow](../.github/workflows/ci.yml):

```sh
npm run preview -- --host 127.0.0.1 --port 5178 --strictPort
```

Set `DEV_API_TARGET` before that server starts, and set `TEST_BASE_URL` to its exact allowed origin. The port above matches the safe test example; change the origin/allowlist together if it is occupied. Vite inherits the API proxy for the production artifact server. Keep the API and worker alive for the entire suite. Development React StrictMode replays effects, so development request counts are not the production acceptance environment. `npm run dev` remains the interactive development command.

Development tools are in `backend/requirements-dev.txt`; install them in the development environment, then from `backend/`:

```sh
python -m ruff check vericommerce_core
python -m mypy vericommerce_core
python -m pytest
python -m bandit -r vericommerce_core
```

Backend integration tests require protected `VC_TEST_ADMIN_DATABASE_URL` and `VC_TEST_DATABASE_URL` values pointing to a dedicated database with the `_test` suffix. The fixture drops/recreates its public schema; never use a valuable database. The CPU integration case also requires an explicitly prewarmed `VC_TEST_EMBEDDING_CACHE_DIR`. Install `.github/ci-requirements.txt` for the safe JUnit helper when running `tests/infra/` too. Inspect the tests first. Missing database, model, Chrome or security tools are missing gates, not passes. Follow [deployment](DEPLOYMENT-CI.md) for security scans and independent review.

### Full repository test suite

The copied `backend/.env.example` uses paths relative to `backend/`. Infrastructure adapter tests also resolve repository-relative files. Run the complete suite from the repository root with all eight maintained backend-data paths rebased; neither an unmodified root invocation nor moving the full suite into `backend/` supplies both sets of paths correctly.

With the development environment activated and the protected test database/cache settings configured, run from the repository root in a POSIX shell:

```sh
export VC_SEED_PATH="$PWD/backend/data/demo.json"
export VC_POLICY_PATH="$PWD/backend/data/policy.json"
export VC_EVALUATION_PATH="$PWD/backend/data/heldout.json"
export VC_MIGRATIONS_PATH="$PWD/backend/migrations"
export VC_INTELLIGENCE_POLICY_PATH="$PWD/backend/data/intelligence.json"
export VC_BENCHMARK_PATH="$PWD/backend/data/benchmark.json"
export VC_BENCHMARK_AGENT_REVIEW_PATH="$PWD/backend/data/benchmark-agent-review.json"
export VC_SHOPIFY_QUERY_PATH="$PWD/backend/data/shopify_graphql.json"
python -m pytest -q tests/backend tests/infra
```

These exports override the copied relative data paths for that shell. A protected test settings file can instead contain the same eight absolute paths. Keep the database URLs and model-cache location private and point them to the dedicated test environment. The shorter backend-directory commands above cover that component, not all infrastructure tests. Install the reviewed production hash lock and development tools together; a passing suite in a different installed dependency environment is not package-identical release evidence.
