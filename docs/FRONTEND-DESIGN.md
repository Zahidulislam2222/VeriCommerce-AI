# Frontend design and interaction

The visual direction is an editorial product studio: warm ivory, oxblood, sculptural imagery, generous space and a visible relationship between products and evidence. Cormorant Garamond supplies display/italic typography; DM Sans supplies interface text. Fonts are self-hosted.

The homepage, fourteen public pages and evidence interfaces share visual tokens and maintained JSON content. Public navigation exposes real destinations, active-page state and a mobile disclosure. Footer groups cover Product, Company, Resources and Legal. Dedicated engineering behavior is described in [architecture](CORE-ARCHITECTURE.md).

## Motion and accessibility

Motion handles reveals/feedback; Lenis handles optional smooth wheel scrolling. Reduced-motion preference is subscribed live. A preference change removes the hero film and destroys smoothing; explicit pause, offscreen and document-hidden states also stop playback. Interaction does not depend on animation.

Dialogs retain focus cycling, Escape and trigger restoration; source inspection returns to the draft review context. Long valid imported text wraps at narrow widths. Public route headings receive programmatic focus without an oversized noninteractive outline, while link/button focus indicators remain visible.

[Motion installation](https://motion.dev/docs/react-installation), [Lenis](https://lenis.dev/), [accessibility requirements](ACCESSIBILITY.md).

## Media provenance

Three product studies were generated with the built-in image tool: ivory headphones, olive-glass serum and silver lamp. The catalog is generated; imagery does not prove real technical attributes. WebP derivatives are rendered; source PNGs remain available for revision.

The five-second silent hero film is a local FFmpeg animation of the generated headphone image. It is not a Seedance-generated film. No paid video result is used. Font/software notices are included in the [third-party notice file](../public/THIRD-PARTY-NOTICES.txt).

## Two data surfaces

The browser workspace supports local collection filtering, source inspection, review/approval and JSON export in browser storage. The `/engine` interface uses server-persisted evidence, real asynchronous jobs, version checks and measured regression results. UI copy distinguishes local storage from server records; clearing local approvals does not erase server data.

The public research roadmap describes future model work. The engine's measured comparison displays actual available methods and frozen-corpus results with separate agent/human review states. Those numbers apply to that synthetic set. Product studies are generated visual assets; actual permitted-store connection and workflow evidence are recorded separately in [release verification](RELEASE-VERIFICATION.md).

## Workspace transitions and honest state

Changing identity/workspace clears prior private data, answers and dialogs before loading the new scope. Expected-workspace headers and response identity checks reject late responses; product/source request generations prevent a delayed result appearing under a different selection. Readiness, errors, unavailable methods, configured-but-disconnected stores and blocked structured data remain explicit UI states. A closed approval dialog does not itself mean the refreshed approval state has arrived.

Copy and labels live in maintained JSON; route/limit/protocol ownership is centralized in typed configuration. A maintained-copy regression discovers all JSON data files so new panels do not silently escape language checks. Responsive gates include narrow layouts, maximum schema-valid text, native controls and long evidence identifiers.
