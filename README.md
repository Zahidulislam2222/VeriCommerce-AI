# VeriCommerce AI

**Evidence-grounded commerce intelligence, by Zahidul Islam.**

VeriCommerce AI connects product information to the sources that support it. It ingests structured catalogs, preserves source revisions, searches current evidence, returns cited quotations, and prepares drafts for explicit approval and provenance-preserving export.

[Website](https://vericommerce.zahidul-islam.com/) · [Evidence workspace](https://vericommerce.zahidul-islam.com/engine) · [Repository](https://github.com/Zahidulislam2222/VeriCommerce-AI) · [Documentation](docs/README.md) · [Release evidence](docs/RELEASE-VERIFICATION.md)

## Current release

The expanded application is live as `20261018-phase3-01`. Its final source passed
140 backend/infrastructure checks. The preceding expansion passed 80 local and
46 live browser checks; current store flows were verified separately. Remaining
phase acceptance limits are recorded in the release report.

The application combines an editorial React interface with FastAPI, PostgreSQL tenant isolation, durable fenced workers and pinned ONNX CPU retrieval. Dedicated product, company, documentation, accessibility, security and US/EU information pages use self-hosted fonts and media.

| Available now | Boundary |
|---|---|
| Accounts and persistent workspaces with four roles | Temporary workspaces remain separate; email verification and password recovery are absent |
| CSV/JSON, text PDF and static raster ingestion | Isolated bounded parsing; scanned PDFs require OCR; image observations do not establish specifications |
| Immutable revisions and temporal relationships | Changed/deleted evidence invalidates dependent approvals; retained history is excluded from current retrieval |
| Keyword, dense, hybrid and deterministic rerank comparison | Exact SKU/color constraints apply before embedding; unavailable methods are reported |
| Answers with revision/page citations | Quotations; relevance does not establish complete question entailment |
| Persisted jobs, description/FAQ drafts, approval and JSON export | Export does not write to Shopify; retry stays within the original attempt budget |
| Read-only Shopify connector | Actual `read_products` installation and sync verified: 23 parent products and 38 variants; no store writes |
| Product/ProductGroup JSON-LD and image-purpose review | Missing offer evidence blocks output; critical claims require separate verification |
| Frozen synthetic retrieval comparison | 30 products, 120 original schematics, 200 questions, 64 held-out test cases; agent review is not human validation |
| Responsive navigation, dialogs and reduced motion | Automated and keyboard checks; no independent certification |

Temporary access uses an isolated cookie-bound workspace with a configured 12-hour lifetime. Account login sessions expire separately from persistent workspace data. There is no password recovery. Use generated or explicitly permitted non-sensitive catalog material; do not submit customer records or credentials. Shopify publishing and model training remain later-phase work. Azure Free hosting, an authenticated AWS validator and a temporary authenticated GCP retrieval contract were deployed and exercised. The GCP resources were removed after verification within the approved experiment window.

## Run and contribute

```sh
npm ci
npm run dev
```

The frontend runs independently. Follow [setup](docs/SETUP.md) for PostgreSQL/API/worker execution and [configuration](docs/CONFIGURATION.md) for its configuration boundaries. Paid model APIs are not required.

Read [contributing](CONTRIBUTING.md), [security reporting](SECURITY.md) and [conduct](CODE_OF_CONDUCT.md). Third-party licenses are in [the published notice file](public/THIRD-PARTY-NOTICES.txt).

## Evidence and future targets

Current release `20261018-phase3-01` has 228 matching deployment artifacts, four healthy constrained services and eight verified HTTPS routes. Types, lint, build, security scans and independent source review passed. A real 1 MiB catalog upload completed through the worker and produced a cited answer; one additional byte was rejected. An encrypted off-server backup restored all 26 current database tables with exact payload hashes and tenant-access checks. Earlier hosted CI and browser results retain their original release scope. [Release evidence](docs/RELEASE-VERIFICATION.md) records each release and its limits.

The earlier verified public-page release passed 44 live desktop/mobile browser checks, 8 domain checks, type/lint/build/security gates and independent review. Its 84 artifact hashes matched; the existing backend remained unchanged. The release report states recovery scope and limitations.

The [ten-phase roadmap](docs/BUILD-PLAN.md) expands this foundation. A future 99% availability objective and architecture for 1M+ active users are engineering targets, not current uptime or capacity measurements. Assumptions, validation and cost boundaries are in [operations](docs/OPERATIONS.md) and [scalability](docs/SCALABILITY-AND-COST.md).

Contact: [muhammadzahidulislam2222@gmail.com](mailto:muhammadzahidulislam2222@gmail.com).

License: [MIT](LICENSE), copyright 2026 Zahidul Islam. Preserve the license/copyright notice when reusing the author’s code. Third-party software, fonts, models and media retain their own terms.
