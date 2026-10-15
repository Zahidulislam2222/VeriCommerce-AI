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

Roadmap comparisons are labeled planned, with no fabricated measured quality/latency chart. Current evaluation results apply only to the curated generated set. No customer logo, endorsement, store connection or external publication is implied by the visual presentation.
