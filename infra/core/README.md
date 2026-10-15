# Evidence core runtime

This Compose application separates static web, FastAPI API, durable worker and PostgreSQL. Local CPU inference requires no paid model API. The existing public gateway owns TLS; only Nginx publishes a loopback host port.

## Contracts

- PostgreSQL and embedding cache have dedicated persistent volumes.
- Runtime API/worker receive only the restricted DB secret. Migration receives a separate administrator secret; PostgreSQL reads its password through a file mount.
- Migration/model preparation are explicit operations. Runtime startup cannot replace the model by downloading another revision.
- Services use nonroot UIDs, read-only roots, dropped capabilities, resource/health bounds and limited writable volumes/tmpfs.
- Dynamic allocation excludes the reserved proxy address; proxy trust is restricted to owned network endpoints.
- Nginx preserves `/api/`, serves exact public application routes and returns a branded HTTP404 for unknown paths. Private source paths remain unavailable.

`deployment.example.json` and `.env.example` describe nonsecret rendering inputs. Do not add actual access values. Validate the resulting configuration and pinned image under the target UID, filesystem and mounts.

## Release and recovery

Prepare whitelisted source/build artifacts, checksum manifest and archive locally. Verify archive restoration and active drift, reserve resource ownership, preserve image/data backups, then gate promotion on real readiness and browser behavior. Require local/archive/live hash parity afterward.

A frontend-only release preserves the accepted backend/image and data. Runtime rollback preserves volumes; it cannot reverse an incompatible SQL migration. Restore into a separate database and verify grants, all-table payload hashes and RLS before any data promotion. Empty-schema validation does not prove populated recovery.

Future cloud deployments must pass actual eligibility/cost checks and remain independent from the synchronous evidence path. Full procedures: [deployment](../../docs/DEPLOYMENT-CI.md), [operations](../../docs/OPERATIONS.md).

References: [Compose services](https://docs.docker.com/reference/compose-file/services/), [FastAPI containers](https://fastapi.tiangolo.com/deployment/docker/), [PostgreSQL restore](https://www.postgresql.org/docs/17/app-pgrestore.html), [Nginx proxy](https://nginx.org/en/docs/http/ngx_http_proxy_module.html), [Caddy proxy](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy).
