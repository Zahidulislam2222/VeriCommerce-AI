# Data, models, evaluation and licenses

## Evidence data

The bundled catalog contains three generated products, six source documents and seven initial passages. Generated product imagery is a visual study, not photographic proof of a real product's properties. Source passages, technical attributes and image observations must remain distinct.

JSON ingestion records source metadata/content hashes, immutable revisions, passage text/page/product and draft citations. Approved exports retain lineage. Exact replay does not create a new revision; changed evidence invalidates dependent drafts. Use only owned or explicitly permitted input. No order history, customer records or a real client relationship is implied by the starting data.

The fixed evaluation file contains ten developer-curated generated questions. Its filename is not evidence of an independent held-out split. Current reports should call it a regression set; a future benchmark needs a frozen split, provenance, annotation instructions and leakage review.

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

No model fine-tuning, preference optimization, reinforcement learning or learned recommendation experiment is claimed in the current release. Answers quote sources; drafts use a deterministic evidence template.

## What the current evaluations establish

Both local keyword and hybrid configurations passed the ten curated cases. That is a small regression result, not population accuracy, a statistically credible comparison or evidence that hybrid ranking improves relevance. The UI runs real checks against current workspace data; imports can change the score.

Report dataset revision, model revision, method, query count, answerable/unanswerable composition, retrieved source IDs and failures. Retrieval recall and abstention accuracy have different denominators. Neither measures whether a quote fully answers a complex question or whether an imported fact is true.

Future evaluation separates product families/source documents before prompt tuning or training; labels synthetic examples; reviews hard negatives, contradiction and freshness cases; measures confidence intervals where the sample permits; and reports paired quality, p50/p95 latency, memory and cost. Accepted output rate and manual review effort need actual user studies, not fabricated conversion events.

## Media and software attribution

The product PNGs were generated with the built-in image tool. Rendered WebPs are derivatives; the silent hero film is an FFmpeg animation of the headphone image. It is not a Seedance-generated film. No paid video output was used.

Cormorant Garamond and DM Sans are self-hosted with SIL Open Font License notices. The published [third-party notices](../public/THIRD-PARTY-NOTICES.txt) include full license texts for 14 installed production packages. Refresh that inventory when dependencies change. Third-party/model/font rights remain separate from the repository's own license and generated-media usage conditions.

## Repository rights

The author’s [repository license](../LICENSE) reserves rights and permits source inspection without a general open-source reuse grant. GitHub platform viewing/forking rights and applicable-law exceptions remain unaffected. Request written permission for other uses that require it. This does not relicense independently licensed software, fonts or model weights.
