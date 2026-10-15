# Defect log

Record each defect found after a completion claim. Never remove historical rows.

| Date | What escaped | Gate that should have caught it | Gate added or improved? |
|---|---|---|---|
| 2026-10-15 | Delivered frontend lacked the dedicated pricing, about, contact and legal pages the owner expected from a professional website. | Frontend acceptance criteria covered the homepage/workspace but omitted the full public information architecture. | Added fourteen explicit public-page criteria, navigation-link coverage, direct-route/404 checks and desktop/mobile accessibility tests. |
| 2026-10-15 | Generated live snapshots entered source lint after deployment and produced minified-bundle errors. | A post-deployment lint run after recovery snapshots were created. | Added the generated `_live_server/` tree to artifact ignores; authored source remains checked. Rerun passed. |
| 2026-10-15 | First hosted browser run omitted the hero-media feature flag and failed four motion checks. | CI environment parity against the actual browser acceptance contract. | Explicit media flag and a workflow regression; motion assertions retained. Corrected hosted result recorded in release verification. |
