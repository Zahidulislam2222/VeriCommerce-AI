# Infrastructure

Infrastructure supports the immutable public website and the persistent evidence runtime on existing hosting. Separate Azure static delivery, authenticated AWS validation and a temporary authenticated GCP retrieval service have recorded execution evidence. The GCP resources were removed after their bounded verification window; these independent workloads do not form the application's synchronous request path.

- [Core runtime](core/README.md): API, worker, database and same-origin web.
- [Cloud adapters and encrypted recovery](cloud/README.md): private validation, snapshot retrieval, provider boundaries and authenticated backup tooling.
- `compose.yaml`, `nginx.conf`, `site.caddy.template`: standalone static website.
- `.env.example` and deployment examples: safe configuration contracts, not active credentials or permission to allocate resources.
- [Deployment/CI](../docs/DEPLOYMENT-CI.md), [operations](../docs/OPERATIONS.md), [future scale/cost](../docs/SCALABILITY-AND-COST.md).

Do not apply templates unchanged to a shared host. Inventory existing ports, networks, ownership and capacity; render through validated environment settings; preserve unrelated services. Keep all secrets outside images and archives. Release gates require local/remote parity and real target-runtime health checks.

Current release and recovery results are in [release evidence](../docs/RELEASE-VERIFICATION.md). A future path from 500–1,000 active users to 1M+ simultaneously active users depends on measured admission, pooled persistence, independent workers and regional cells; [the capacity plan](../docs/SCALABILITY-AND-COST.md) specifies those gates. Infrastructure templates and budget alerts do not authorize provisioning or cap all provider charges.

Future placement prioritizes appropriate AWS/GCP/Azure services within verified account allowances, with a hybrid assessment before paid capacity is added. Existing hosting remains useful for persistent data and costly/heavy CPU work where measured economics justify it. The capacity plan maps each component to its proposed location, rationale and cost/retention limits; existing resources are not migrated solely to satisfy a naming or cloud convention.
