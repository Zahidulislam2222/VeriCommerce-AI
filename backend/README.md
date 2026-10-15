# Evidence backend

FastAPI/Pydantic, PostgreSQL and a durable worker implement temporary isolated evidence workspaces, JSON ingestion, immutable source revisions, conservative local CPU hybrid retrieval, cited quotations, draft approval/export and measured regression checks.

Read [setup](../docs/SETUP.md), [API](../docs/CORE-API.md), [configuration](../docs/CONFIGURATION.md) and [architecture](../docs/CORE-ARCHITECTURE.md). The typed settings module and safe environment example own runtime inputs. Maintained policy JSON is validated; product copy does not belong in control flow.

Runtime uses a restricted database role with forced tenant RLS. Migration requires a separate administrator connection. Use a dedicated local test database; never run the integration suite against production. Source rows and draft jobs are real persisted application records, while the starting catalog/evaluation records are generated.

Current API version 0.2.0 is configurable through `VC_API_VERSION`. No account/RBAC, upload, Shopify or training endpoints are integrated. Legacy compatibility identifiers remain stable; changing display language does not change migration hashes or session semantics.
