# VeriCommerce AI

**Evidence-grounded commerce intelligence, by Zahidul Islam.**

VeriCommerce AI connects product information to the sources that support it. It ingests structured catalogs, preserves source revisions, searches current evidence, returns cited quotations, and prepares drafts for explicit approval and provenance-preserving export.

[Website](https://vericommerce.zahidul-islam.com/) · [Evidence workspace](https://vericommerce.zahidul-islam.com/engine) · [Repository](https://github.com/Zahidulislam2222/VeriCommerce-AI) · [Documentation](docs/README.md) · [Release evidence](docs/RELEASE-VERIFICATION.md)

## Current release

The application combines an editorial React interface with FastAPI, PostgreSQL tenant isolation, durable fenced workers and pinned ONNX CPU retrieval. Dedicated product, company, documentation, accessibility, security and US/EU information pages use self-hosted fonts and media.

| Available now | Boundary |
|---|---|
| Incremental JSON catalog ingestion | Bounded catalog; omitted items are not deleted |
| Immutable revisions and provenance graph | Changed sources or product metadata invalidate dependent drafts |
| Keyword search and local CPU hybrid ranking | Lexical fallback is reported when the model is unavailable |
| Answers with revision/page citations | Quotations; relevance does not establish complete question entailment |
| Persisted jobs, draft approval and JSON export | Export does not write to Shopify |
| Measured retrieval/abstention checks | Ten curated generated cases; no general accuracy claim |
| Responsive navigation, dialogs and reduced motion | Automated and keyboard checks; no independent certification |

Access uses temporary, cookie-bound isolated workspaces with a configured 12-hour lifetime. There is no account recovery or team membership in this release. Export useful work before expiry. Use generated or explicitly permitted non-sensitive catalog material; do not submit customer records or credentials. Shopify authorization/publishing, document/image ingestion, training and AWS/GCP/Azure deployments are separately gated roadmap work.

## Run and contribute

```sh
npm ci
npm run dev
```

The frontend runs independently. Follow [setup](docs/SETUP.md) for PostgreSQL/API/worker execution and [configuration](docs/CONFIGURATION.md) for its configuration boundaries. Paid model APIs are not required.

Read [contributing](CONTRIBUTING.md), [security reporting](SECURITY.md) and [conduct](CODE_OF_CONDUCT.md). Third-party licenses are in [the published notice file](public/THIRD-PARTY-NOTICES.txt).

## Evidence and future targets

The verified public-page release passed 44 live desktop/mobile browser checks, 8 domain checks, type/lint/build/security gates and independent review. Its 84 artifact hashes matched; the existing backend remained unchanged. The release report states recovery scope and limitations.

The [ten-phase roadmap](docs/BUILD-PLAN.md) expands this foundation. A future 99% availability objective and architecture for 1M+ active users are engineering targets, not current uptime or capacity measurements. Assumptions, validation and cost boundaries are in [operations](docs/OPERATIONS.md) and [scalability](docs/SCALABILITY-AND-COST.md).

Contact: [muhammadzahidulislam2222@gmail.com](mailto:muhammadzahidulislam2222@gmail.com).

License: [MIT](LICENSE), copyright 2026 Zahidul Islam. Preserve the license/copyright notice when reusing the author’s code. Third-party software, fonts, models and media retain their own terms.
