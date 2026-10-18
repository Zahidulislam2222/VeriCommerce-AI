import { useState } from 'react';
import { appConfig } from '../config';
import copy from '../data/phase-workspace.json';
import { post, request } from './api';
import type { CoreProduct } from './types';
import type { AccountState, Benchmark, BenchmarkDataset, ContextResult, PlatformCapabilities } from './phase-types';
import { JsonRecord } from './PhaseShared';

function metric(value: number | null, digits: number) { return typeof value === 'number' ? value.toFixed(digits) : '—'; }

type Run = (action: () => Promise<void>) => void;
function CorpusImage({ image, name }: { image: BenchmarkDataset['images'][number]; name: string }) {
  const target = `${appConfig.core.benchmarkProductPrefix}${image.product_id}`;
  const functional = image.purpose === 'functional' && image.destination === `#${target}`;
  const illustration = appConfig.core.datasetImagePattern.test(image.path)
    ? <img className="phase-review-image" src={image.path} alt={image.purpose === 'decorative' ? '' : image.expected_alt} loading="lazy" />
    : <p>{copy.benchmark.notImage}</p>;
  return <><h4>{name}</h4><p>{image.usage_context || copy.benchmark.missingContext}</p>{functional ? <a href={`#${target}`} onClick={(event) => {
    event.preventDefault();
    let ancestor = document.getElementById(target)?.parentElement;
    while (ancestor) { if (ancestor instanceof HTMLDetailsElement) ancestor.open = true; ancestor = ancestor.parentElement; }
    const facts = document.getElementById(target);
    facts?.scrollIntoView({ block: 'start', behavior: 'instant' }); facts?.focus({ preventScroll: true });
  }}>{illustration}</a> : illustration}{image.function && <p>{copy.review.function}: {image.function} · {image.destination}</p>}</>;
}
export function RetrievalPanel({ products, capabilities, busy, run }: { products: CoreProduct[]; capabilities: PlatformCapabilities; busy: boolean; run: Run }) {
  const [query, setQuery] = useState('');
  const [method, setMethod] = useState(capabilities.retrieval.methods[0] || 'keyword');
  const [product, setProduct] = useState('');
  const [other, setOther] = useState('');
  const [sku, setSku] = useState('');
  const [color, setColor] = useState('');
  const [category, setCategory] = useState('');
  const [budget, setBudget] = useState(capabilities.retrieval.context_max_chars);
  const [results, setResults] = useState<{ product: string; data: ContextResult }[]>([]);
  const [snapshot, setSnapshot] = useState<unknown>(null);
  const paths = appConfig.core.phasePaths;
  const input = { query, method, ...(sku ? { sku } : {}), ...(color ? { color } : {}), ...(category ? { category } : {}), budget_chars: budget };
  return <section className="phase-card"><h2>{copy.search.title}</h2><p>{copy.search.description}</p><form onSubmit={(event) => { event.preventDefault(); run(async () => { setResults([]); const data = await post<ContextResult>(paths.context, { ...input, ...(product ? { product_id: product } : {}) }); setResults([{ product: products.find((item) => item.id === product)?.name || copy.search.select, data }]); }); }}>
    <label>{copy.search.query}<textarea disabled={busy} required minLength={appConfig.core.queryMinLength} rows={3} maxLength={appConfig.core.queryMaxLength} value={query} onChange={(event) => setQuery(event.target.value)} /></label>
    <div className="phase-grid"><label>{copy.search.method}<select disabled={busy} value={method} onChange={(event) => setMethod(event.target.value)}>{capabilities.retrieval.methods.map((item) => <option key={item} value={item}>{item}</option>)}</select></label><label>{copy.search.budget}<input disabled={busy} type="number" required min={appConfig.core.contextMinChars} max={capabilities.retrieval.context_max_chars} value={budget} onChange={(event) => setBudget(Number(event.target.value))} /></label></div>
    <div className="phase-grid">{[{ label: copy.search.first, value: product, set: setProduct }, { label: copy.search.second, value: other, set: setOther }].map((field) => <label key={field.label}>{field.label}<select disabled={busy} value={field.value} onChange={(event) => field.set(event.target.value)}><option value="">{copy.common.select}</option>{products.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>)}</div>
    <details><summary>{copy.search.constraints}</summary><div className="phase-grid">{[{ label: copy.search.sku, value: sku, set: setSku, max: appConfig.core.skuMaxLength }, { label: copy.search.color, value: color, set: setColor, max: appConfig.core.colorMaxLength }, { label: copy.search.category, value: category, set: setCategory, max: appConfig.core.categoryMaxLength }].map((field) => <label key={field.label}>{field.label}<input disabled={busy} value={field.value} maxLength={field.max} onChange={(event) => field.set(event.target.value)} /></label>)}</div></details>
    <div className="phase-actions"><button className="button" disabled={busy || !query.trim()}>{copy.search.run}</button><button type="button" className="button button-outline" disabled={busy || !product || !other || product === other || !query.trim()} onClick={() => run(async () => { setResults([]); const data = await Promise.all([product, other].map(async (id) => ({ product: products.find((item) => item.id === id)?.name || id, data: await post<ContextResult>(paths.context, { ...input, product_id: id }) }))); setResults(data); })}>{copy.search.compare}</button><button type="button" className="text-link" disabled={busy} onClick={() => run(async () => setSnapshot(await post(paths.snapshot, product ? { product_id: product } : {})))}>{copy.search.snapshot}</button></div>
  </form>
    <div className={results.length > 1 ? 'phase-grid' : ''}>{results.map(({ product: name, data }, index) => <article className="phase-context" key={`${name}-${index}`}><h3>{name} · {data.method}</h3>{!data.available && <p role="status">{copy.search.unavailable}</p>}<p>{copy.search.used}: {data.context.used_chars} / {data.context.budget_chars}</p><small>{data.context.snapshot_hash} · {data.context.authority}</small><h4>{copy.search.selected}</h4>{data.context.selected.length ? data.context.selected.map((passage) => <blockquote key={passage.passage_id}><p>{passage.text}</p><cite>{passage.product_name} · {passage.source_name} · {passage.source_version} · {passage.page}</cite></blockquote>) : <p>{copy.common.empty}</p>}<JsonRecord label={copy.search.excluded} data={data.context.excluded} /><JsonRecord label={copy.search.diagnostics} data={data.retrieval} /></article>)}</div>
    {snapshot !== null && <JsonRecord label={copy.search.snapshotResult} data={snapshot} open />}
  </section>;
}

export function BenchmarkPanel({ account, busy, run }: { account: AccountState; busy: boolean; run: Run }) {
  const [benchmarks, setBenchmarks] = useState<Benchmark[] | null>(null);
  const [dataset, setDataset] = useState<BenchmarkDataset | null>(null);
  const [questions, setQuestions] = useState<string[]>([]);
  const [images, setImages] = useState<string[]>([]);
  const [decision, setDecision] = useState('needs_changes');
  const [notes, setNotes] = useState('');
  const [confirmed, setConfirmed] = useState(false);
  const [saved, setSaved] = useState(false);
  const paths = appConfig.core.phasePaths;
  const canReview = account.authenticated && account.capabilities.includes('approve');
  const toggle = (id: string, list: string[], set: (ids: string[]) => void) => { set(list.includes(id) ? list.filter((item) => item !== id) : [...list, id]); setConfirmed(false); setSaved(false); };
  const loadDataset = async () => { setDataset(await request<BenchmarkDataset>(paths.dataset)); setQuestions([]); setImages([]); setConfirmed(false); };
  return <section className="phase-card"><h2>{copy.benchmark.title}</h2><p>{copy.benchmark.description}</p><div className="phase-actions"><button className="button" disabled={busy || !account.capabilities.includes('edit')} onClick={() => run(async () => { const response = await post<{ benchmark: Benchmark }>(paths.benchmarks, {}); setBenchmarks([response.benchmark]); })}>{copy.benchmark.run}</button><button className="button button-outline" disabled={busy} onClick={() => run(async () => setBenchmarks((await request<{ benchmarks: Benchmark[] }>(paths.benchmarks)).benchmarks))}>{copy.benchmark.records}</button><button className="text-link" disabled={busy} onClick={() => run(loadDataset)}>{copy.benchmark.dataset}</button></div>
    {benchmarks?.map((benchmark, index) => <article className="phase-context" key={`${benchmark.dataset_hash}-${index}`}><h3>{benchmark.dataset_version} · {benchmark.split}</h3><p>{benchmark.review_status} · {benchmark.notice}</p><small>{benchmark.dataset_hash}</small><div className="phase-table-wrap" tabIndex={0} role="region" aria-label={copy.benchmark.title}><table><caption>{copy.benchmark.title}</caption><thead><tr>{copy.benchmark.columns.map((column) => <th key={column} scope="col">{column}</th>)}</tr></thead><tbody>{benchmark.results.map((result) => <tr key={result.method}><th scope="row">{result.method}</th><td>{String(result.available)}</td><td>{result.total}</td><td>{result.available ? metric(result.recall_at_10, 3) : '—'}</td><td>{result.available ? metric(result.ndcg_at_10, 3) : '—'}</td><td>{result.available ? metric(result.abstention_accuracy, 3) : '—'}</td><td>{result.available ? metric(result.latency_ms_p50, 1) : '—'}</td><td>{result.available ? metric(result.latency_ms_p95, 1) : '—'}</td></tr>)}</tbody></table></div><JsonRecord label={copy.benchmark.caseResults} data={benchmark} /></article>)}
    {dataset && <><h3>{dataset.version} · {dataset.review_status}</h3><p>{copy.benchmark.agentReview}: {dataset.agent_review_status || dataset.review_status} · {copy.benchmark.humanReview}: {dataset.human_review_status || copy.benchmark.pending}</p><small>{dataset.hash} · {dataset.license}</small><JsonRecord label={copy.benchmark.products} data={dataset.products} /><JsonRecord label={copy.benchmark.catalog} data={dataset.catalog} /><details className="phase-records"><summary>{copy.benchmark.productFacts}</summary>{dataset.products.map((product) => <section tabIndex={-1} aria-label={product.name} id={`${appConfig.core.benchmarkProductPrefix}${product.id}`} key={product.id}><h4>{product.name}</h4>{dataset.catalog?.products.find((item) => item.id === product.id)?.claims.map((claim, index) => <blockquote key={`${claim.sourceId}-${index}`}><strong>{claim.label}: {claim.value}</strong><p>{claim.passage}</p><cite>{claim.sourceId} · {claim.page}</cite></blockquote>)}</section>)}</details><details className="phase-records"><summary>{copy.benchmark.questions} ({dataset.questions.length})</summary>{dataset.questions.map((question) => <article key={question.id}><label className="phase-checkbox"><input type="checkbox" disabled={!canReview || busy} checked={questions.includes(question.id)} onChange={() => toggle(question.id, questions, setQuestions)} /><span><strong>{question.query}</strong><small>{question.id} · {question.product_id} · {question.split}</small></span></label><p>{copy.benchmark.expectedSource}: {question.expected_source_id || '—'} · {copy.benchmark.expectedLabel}: {question.expected_label || '—'} · {copy.benchmark.expectedAbstain}: {String(question.expected_abstain)}</p>{dataset.catalog?.products.find((item) => item.id === question.product_id)?.claims.filter((claim) => claim.label === question.expected_label && claim.sourceId === question.expected_source_id).map((claim, index) => <blockquote key={`${claim.sourceId}-${index}`}><strong>{copy.benchmark.expectedValue}: {claim.value}</strong><p>{claim.passage}</p><cite>{claim.sourceId} · {claim.page}</cite></blockquote>)}<JsonRecord label={copy.benchmark.evidence} data={dataset.catalog?.products.find((item) => item.id === question.product_id)?.claims || []} /></article>)}</details><details className="phase-records"><summary>{copy.benchmark.images} ({dataset.images.length})</summary>{dataset.images.map((image) => <article key={image.id}><CorpusImage image={image} name={dataset.products.find((item) => item.id === image.product_id)?.name || image.product_id} /><label className="phase-checkbox"><input type="checkbox" disabled={!canReview || busy} checked={images.includes(image.id)} onChange={() => toggle(image.id, images, setImages)} /><span>{image.id} · {image.product_id}</span></label><p>{image.purpose} · {image.expected_alt}</p><small>{image.path}</small></article>)}</details>
      {canReview ? <form onSubmit={(event) => { event.preventDefault(); run(async () => { await post(paths.datasetReviews, { dataset_hash: dataset.hash, question_ids: questions, image_ids: images, decision, notes }); await loadDataset(); setSaved(true); }); }}><p>{copy.benchmark.emptySelection}</p><label>{copy.benchmark.decision}<select value={decision} onChange={(event) => { setDecision(event.target.value); setConfirmed(false); }}><option value="needs_changes">{copy.benchmark.changes}</option><option value="approved">{copy.benchmark.approved}</option></select></label><label>{copy.benchmark.notes}<textarea required value={notes} rows={4} maxLength={appConfig.core.reviewNotesMaxLength} onChange={(event) => { setNotes(event.target.value); setConfirmed(false); }} /></label><label className="phase-checkbox"><input type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} />{copy.benchmark.confirmation}</label><button className="button" disabled={busy || !confirmed || !(questions.length + images.length) || !notes.trim()}>{copy.benchmark.review}</button>{saved && <p role="status">{copy.benchmark.recorded}</p>}</form> : <p>{copy.benchmark.signin}</p>}{dataset.reviews && <JsonRecord label={copy.benchmark.reviews} data={dataset.reviews} />}
    </>}
  </section>;
}
