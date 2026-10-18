# Engineering documentation

VeriCommerce AI is developed and operated by **Zahidul Islam**. These documents describe implemented behavior, observed release evidence and clearly marked future targets. Generated product records are not customers, orders or measured business outcomes.

| Document | Purpose |
|---|---|
| [Technical overview](../my-project-view/technical-overview.md) | Comprehensive project narrative |
| [PDF overview](../my-project-view/VeriCommerce%20AI%20%E2%80%94%20Comprehensive%20Technical%20Overview.pdf) | Native Google Docs export |
| [Architecture](CORE-ARCHITECTURE.md) | Components, trust boundaries, evidence lifecycle and constraints |
| [Setup](SETUP.md) | Frontend, PostgreSQL, API, worker and checks |
| [API](CORE-API.md) | Accounts/roles, ingestion, context, content review, Shopify and evaluation contracts |
| [Configuration](CONFIGURATION.md) | Typed settings, public build inputs and protected secrets |
| [Security policy](../SECURITY.md) | Reporting and supported release policy |
| [Threat model](THREAT-MODEL.md) | Mitigations and remaining security work |
| [Privacy and legal applicability](PRIVACY-AND-LEGAL.md) | Data handling and US/EU requirements |
| [Accessibility](ACCESSIBILITY.md) | Interaction requirements, evidence and review gaps |
| [Data, models and evaluation](DATA-MODELS-EVALUATION.md) | Provenance, licenses and measurement limits |
| [Deployment and CI](DEPLOYMENT-CI.md) | Local-first releases and supply-chain gates |
| [Operations](OPERATIONS.md) | Incidents, recovery and proposed availability SLO |
| [Scalability and cost](SCALABILITY-AND-COST.md) | Future 1M+ simultaneously active-user workload, staged validation and cost arithmetic |
| [Ten-phase roadmap](BUILD-PLAN.md) | Parallel lanes, deployment and acceptance per phase |
| [Release evidence](RELEASE-VERIFICATION.md) | Observed results and their scope |
| [Public website](PUBLIC-WEBSITE.md) | Page inventory and maintained content |
| [Frontend design](FRONTEND-DESIGN.md) | Visual system, media provenance and motion |

For contributors: [contributing](../CONTRIBUTING.md), [conduct](../CODE_OF_CONDUCT.md), [change history](../CHANGELOG.md). Infrastructure: [overview](../infra/README.md), [core runtime](../infra/core/README.md), [cloud adapters](../infra/cloud/README.md).

Start with the [root overview](../README.md), then follow setup → architecture/API → operations. Current accounts, uploads and read-only store integration have release-bound evidence. The persistent application uses one existing server; cloud contracts have separate scopes. Capacity validation, a measured rolling SLO, human accessibility review and the merchant-data governance checklist remain the next operating gates.
