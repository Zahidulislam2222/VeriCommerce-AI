# Data, models, evaluation and licenses

Current release `20261018-phase5-02` follows quota release `20261018-phase3-01`, the integrated expansion `20261018-phase1-01` and the verified 2026-10-15 evidence release. The final clean production-locked suite passed 142 backend/infrastructure checks with zero failures, errors or skips; package consistency passed with Pillow 12.3.0 matching the production hash lock. The earlier 140-check local run used a different Pillow version and is not package-identical evidence. Earlier frontend evidence includes 80 local and 46 live browser checks; current development-store API flows were verified separately. These results describe their tested source/application flows, not general model quality. Actual Azure publication and four initial plus four final-source AWS validator invocations have separate provider evidence; GCP acceptance is recorded separately. These integrated application deployments carry phases 1–5 features, without claiming five separate phase deployment receipts.

## Evidence data

The bundled catalog contains three generated products, six source documents and seven initial passages. Generated product imagery is a visual study, not photographic proof of a real product's properties. Source passages, technical attributes and image observations must remain distinct.

JSON/CSV ingestion records source metadata/content hashes, immutable revisions, passage text/page/product and draft citations. Approved exports retain lineage. Exact replay does not create a new revision; changed evidence invalidates dependent drafts. Text-bearing PDF pages can supply passages through bounded isolated parsing. Static raster inputs remain observations requiring purpose-aware review; scanned/empty PDFs report OCR required without inventing extracted text. Use only owned or explicitly permitted input. No order history, customer records or a real client relationship is implied by the starting data.

The original fixed evaluation file retains ten developer-curated generated questions. Its filename is not evidence of an independent held-out split; call it a regression set.

The candidate separately packages 30 original synthetic products,120 original schematic SVG images and 200 questions. Product-family assignments are frozen before comparison, with 64 test questions (60 answerable and 4 expected abstentions), exceeding the planned50-question minimum. Product/source metadata, expected supporting attributes, missing-evidence cases, image purpose/usage context and attribution are versioned in [the benchmark](../backend/data/benchmark.json) and [generation specification](../backend/data/benchmark-spec.json). Regeneration changes require a new integrity hash and renewed review.

An independent AI agent reviewed all 200 question labels against passages and visually reviewed all 120 corrected schematics under the owner's explicit delegation. The [review sidecar](../backend/data/benchmark-agent-review.json) identifies `reviewer_type:agent`, owner delegation and exact frozen item coverage. This is agent review, not independent human validation. Human review remains pending and is represented separately in the API/UI. Account reviewers can record per-item decisions and disagreement notes against the exact dataset hash; a changed corpus cannot inherit those decisions.

Shopify imports retain normalized provider identity and immutable source lineage. Stable child products represent variant SKU and authoritative Color options, with current-only filters before model exposure. Images/media do not establish verified technical claims. Removed/deleted/uninstalled children are tombstoned, and dependent approvals become stale. Source deletion clears uploaded original bytes but does not promise deletion of all historical extracted passages or backups.

The permitted development store's real initial sync produced 61 product records: 23 parents and 38 variants, supported by 23 sources and 206 passages. Actual parent/SKU/color filtering and a cited answer passed. A three-citation FAQ was inspected by the delegated agent, blocked from export until approval, then exported unchanged with `published:false`. A subsequent owner-approved temporary title change and restoration through Shopify Admin generated two real HMAC-verified update events, both durably applied. Parent/child records changed and restored, the earlier draft export returned 409, and a following full sync produced zero canonical product differences or duplicates. These two Admin title saves were separate from the app, which retained only `read_products` and made no product-write calls. An actual expired-token refresh retained exactly `read_products`. These connector/workflow observations do not add independent human labels to the frozen synthetic benchmark.

## Model card for the current retrieval component

| Property | Current implementation |
|---|---|
| Task | Passage embedding/ranking, not text generation |
| Base | BGE-small-en-v1.5 |
| Runtime artifact | Quantized ONNX conversion from Qdrant |
| Repository | `Qdrant/bge-small-en-v1.5-onnx-Q` |
| Frozen revision | `aa8f8b060edb00e03bfdd08813a2949946c8ba55` |
| File | `model_optimized.onnx` |
| Execution | CPU, configured bounded threads/batches |
| License identified by upstream cards | MIT |
| Fallback | Explicit keyword-only retrieval when optional cache is unavailable |

These are release facts, not hardcoded application defaults; settings own the identifiers. Check the pinned revision's license files when redistributing weights. Preserve upstream notices and verify conversion provenance. [Base model card](https://huggingface.co/BAAI/bge-small-en-v1.5), [ONNX conversion](https://huggingface.co/Qdrant/bge-small-en-v1.5-onnx-Q).

No model fine-tuning, preference optimization, reinforcement learning or learned recommendation experiment is claimed. Answers quote sources; description/FAQ drafts use deterministic evidence templates. The candidate reranker is deterministic label/text coverage, not a learned cross-encoder. Product/ProductGroup JSON-LD is generated in code with current provenance, and absent/conflicting authoritative offer fields block output.

## What the current evaluations establish

Both local keyword and hybrid configurations passed the ten curated cases. That is a small regression result, not population accuracy, a statistically credible comparison or evidence that hybrid ranking improves relevance. The UI runs real checks against current workspace data; imports can change the score.

Report dataset revision, model revision, method, query count, answerable/unanswerable composition, retrieved source IDs and failures. Retrieval recall and abstention accuracy have different denominators. Neither measures whether a quote fully answers a complex question or whether an imported fact is true.

Future evaluation separates product families/source documents before prompt tuning or training; labels synthetic examples; reviews hard negatives, contradiction and freshness cases; measures confidence intervals where the sample permits; and reports paired quality, p50/p95 latency, memory and cost. Accepted output rate and manual review effort need actual user studies, not fabricated conversion events.

## Candidate frozen-corpus comparison

The local candidate exercised the actual pinned ONNX CPU encoder and measured all four methods on the same64-question synthetic test split. Each method achieved Recall@10 and nDCG@10 of 1.0 on 60 answerable questions. Keyword, hybrid and deterministic rerank had abstention accuracy1.0 across all 64 questions; dense-only had0.9375. Keyword had the lowest measured p95 latency in that local run and is selected for this corpus only. No general hybrid improvement, merchant accuracy, human validation or cloud benchmark result follows from these numbers.

The benchmark API persists per-case retrieved/relevant IDs, expected abstention, elapsed time, dataset hash/version, method availability and separate review states. Recall averages answerable-question retrieval coverage; nDCG measures rank-discounted relevance; abstention accuracy includes answerable and unanswerable cases. Warm/cold cache state, hardware contention and sample size affect latency. Dense, hybrid and rerank are explicitly unavailable if the encoder is absent; unavailable results are not reported as successful keyword substitution.

These questions are simple synthetic attribute lookups, often with product identity supplied. Perfect scores can reflect the corpus design and do not establish difficult multilingual, ambiguous or real catalog performance. No statistically supported broad gain, graph-backed retrieval gain, confidence interval or independently calibrated judge is claimed. Product-family separation does not substitute for human label review or external-domain evaluation. Expanded real-world data, harder negatives and paired latency/memory runs remain appropriate before changing the method recommendation.

The optional GCP lexical adapter uses a much smaller immutable sanitized three-document smoke fixture. Three actual IAM-authenticated Cloud Run cases passed health, retrieval and abstention contracts and matched the local image. The temporary service, image repository and service account were removed before the approved deadline; 135 baseline resource payloads were unchanged. Initial failures remain in the operational evidence, and final billing is unverified. This smoke is separate from the 64-question held-out evaluation. The authenticated AWS validator passed four initial and four final-source invocations, with all verdicts matching local execution and final ZIP/native parity verified. It verifies deterministic manifest/quotation consistency, not semantic truth or publishing authorization. The actual Azure Free reference serves sanitized smoke data and passed nine browser checks; its final republish matched six served asset hashes and verified the consumed platform configuration; it is not this held-out model benchmark. See [cloud boundaries](../infra/cloud/README.md).

## Media and software attribution

The product PNGs were generated with the built-in image tool. Rendered WebPs are derivatives; the silent hero film is an FFmpeg animation of the headphone image. It is not a Seedance-generated film. No paid video output was used.

The120 benchmark SVGs are original programmatic schematics with attribution/usage context in the frozen dataset. They depict generated fixtures rather than photographed merchant inventory. They do not replace actual-upload raster parser tests or independent accessibility assessment.

Cormorant Garamond and DM Sans are self-hosted with SIL Open Font License notices. The published [third-party notices](../public/THIRD-PARTY-NOTICES.txt) include full license texts for 14 installed production packages. Refresh that inventory when dependencies change. Third-party/model/font rights remain separate from the repository's own license and generated-media usage conditions.

## Repository rights

The author’s code and associated documentation use the [MIT License](../LICENSE), copyright 2026 Zahidul Islam. MIT permits reuse, modification and redistribution subject to preserving its copyright/permission notice and disclaimer. This does not relicense independently licensed software, fonts, model weights or media; preserve their respective terms and provenance.
