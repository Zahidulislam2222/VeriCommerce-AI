# Infrastructure

Infrastructure templates support an immutable static website and the evidence-core runtime. The current application uses an existing server; no AWS/GCP/Azure deployment is claimed.

- [Core runtime](core/README.md): API, worker, database and same-origin web.
- `compose.yaml`, `nginx.conf`, `site.caddy.template`: standalone static website.
- `.env.example` and deployment examples: safe configuration contracts, not active credentials or permission to allocate resources.
- [Deployment/CI](../docs/DEPLOYMENT-CI.md), [operations](../docs/OPERATIONS.md), [future scale/cost](../docs/SCALABILITY-AND-COST.md).

Do not apply templates unchanged to a shared host. Inventory existing ports, networks, ownership and capacity; render through validated environment settings; preserve unrelated services. Keep all secrets outside images and archives. Release gates require local/remote parity and real target-runtime health checks.
