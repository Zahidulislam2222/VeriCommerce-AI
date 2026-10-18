# Evidence backend

FastAPI/Pydantic, PostgreSQL and a durable worker implement persistent account workspaces, four membership roles, bounded catalog/document ingestion, immutable source revisions, current-evidence retrieval, cited quotations and reviewed content. Cookie-bound temporary workspaces have a separate expiry and cleanup lifecycle.

Read [setup](../docs/SETUP.md), [API](../docs/CORE-API.md), [configuration](../docs/CONFIGURATION.md) and [architecture](../docs/CORE-ARCHITECTURE.md). The typed settings module and safe environment example own runtime inputs. Maintained policy JSON is validated; product copy does not belong in control flow.

Runtime uses a restricted database role with forced tenant RLS. Migration requires a separate administrator connection. Use a dedicated local test database; never run the integration suite against production. Source rows and draft jobs are real persisted application records, while the starting catalog/evaluation records are generated.

Current API version 0.2.0 is configurable through `VC_API_VERSION`. Accounts, CSV/JSON/PDF/static-image uploads, keyword/dense/hybrid/rerank context inspection, read-only Shopify, relationships, description/FAQ drafts, image-purpose review and guarded Product/ProductGroup JSON-LD are integrated. Model training and Shopify publishing remain on the [roadmap](../docs/BUILD-PLAN.md).

The connector permits only `read_products`; a product catalog import does not grant access to customers or orders. Product/source retirement fences current retrieval and approvals while retaining historical provenance. [Privacy and retention](../docs/PRIVACY-AND-LEGAL.md) describe the storage boundaries.

Run the full suite with the [repository-root invocation and explicit data-path rebasing](../docs/SETUP.md#full-repository-test-suite), a dedicated test database and prewarmed model cache. The copied backend settings example uses backend-relative paths; changing the working directory without rebasing them is incorrect. Setup also describes the destructive test fixture and production-artifact browser checks. Current evidence and remaining operational gates are in [release verification](../docs/RELEASE-VERIFICATION.md); the future capacity model is in [scalability and cost](../docs/SCALABILITY-AND-COST.md).
