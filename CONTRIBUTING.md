# Contributing

VeriCommerce AI is maintained by Zahidul Islam and released under the [MIT License](LICENSE). You may use, modify and redistribute the author’s code under that license, including its notice-preservation and warranty terms. Third-party components retain their own licenses. Contributions intended for inclusion must be compatible with MIT and you must have the right to provide them.

Use [the repository](https://github.com/Zahidulislam2222/VeriCommerce-AI) for non-sensitive defects and proposed improvements. Vulnerabilities follow [private security reporting](SECURITY.md); conduct issues use the contact in [the code of conduct](CODE_OF_CONDUCT.md). Discuss substantial changes and rights to contributed material before submitting them.

## Change workflow

1. Read the relevant [engineering documents](docs/README.md), configuration boundary and current API.
2. Write acceptance criteria or reproduce the defect before changing behavior.
3. Keep one reviewable scope; preserve public API/data compatibility and unrelated work.
4. Put environment values in typed settings, maintained copy/prompts in validated data, and secrets outside source.
5. Add meaningful regression coverage for changed behavior. Do not replace actual integration checks with mocks that assert implementation details.
6. Run the required checks and real flow; document missing gates and limitations.
7. Obtain independent review; update architecture/API/examples and release notes when facts change.

## Verification

Frontend: `npm test`, `npm run typecheck`, `npm run lint`, `npm run build`, and browser tests against API/worker. Backend: real PostgreSQL/CPU tests, Ruff, Mypy and Bandit. Release scans include Gitleaks and Semgrep. See [setup](docs/SETUP.md) and [deployment](docs/DEPLOYMENT-CI.md).

Use unmistakably generated local test data and reserved hosts. Never commit credentials, real customer records, database dumps, private operator state or workstation-specific paths. Do not upload private test artifacts to CI. Dependencies must exist in the real registry and be version/license-reviewed.

Changes affecting tenant context, evidence revision, approval, jobs, model/cache, proxy trust or migrations need targeted failure/recovery tests. UI changes retain keyboard/focus, mobile overflow and live reduced-motion behavior. A hosted green badge does not replace independent review or real release validation.

## Publication and permissions

Submitting a change does not authorize deployment, spending, external-store actions or disclosure of another person's data. Keep paid API review and cloud provisioning out of routine checks. Contributions must be original or have documented permission; disclose generated material and dependencies. Maintainer acceptance does not imply endorsement of unsupported performance or compliance claims.
