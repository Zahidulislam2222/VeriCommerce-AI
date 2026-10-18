import { useEffect, useRef, useState } from 'react';
import { appConfig } from '../config';
import copy from '../data/phase-workspace.json';
import { post, request } from './api';
import type { CoreProduct } from './types';
import type { AccountState, Intelligence, UploadRecord } from './phase-types';
import { JsonRecord } from './PhaseShared';

type Run = (action: () => Promise<void>) => void;
export default function ReviewPanel({ products, account, busy, run }: { products: CoreProduct[]; account: AccountState; busy: boolean; run: Run }) {
  const [product, setProduct] = useState('');
  const [data, setData] = useState<Intelligence | null>(null);
  const [uploads, setUploads] = useState<UploadRecord[]>([]);
  const [upload, setUpload] = useState('');
  const [purpose, setPurpose] = useState('informative');
  const [observation, setObservation] = useState('');
  const [alt, setAlt] = useState('');
  const [functionLabel, setFunctionLabel] = useState('');
  const [subject, setSubject] = useState('');
  const [predicate, setPredicate] = useState<string>(appConfig.core.relationPredicates[0]);
  const [object, setObject] = useState('');
  const [revision, setRevision] = useState('');
  const requestGeneration = useRef(0);
  useEffect(() => () => { requestGeneration.current++; }, []);
  const paths = appConfig.core.phasePaths;
  const canEdit = account.capabilities.includes('edit');
  const canApprove = account.authenticated && account.capabilities.includes('approve');
  const load = async () => {
    const generation = ++requestGeneration.current;
    const selectedProduct = product;
    const result = await request<Intelligence>(`${paths.intelligence}/${encodeURIComponent(selectedProduct)}`);
    if (generation !== requestGeneration.current) return;
    if (result.product_id !== selectedProduct) throw new Error(copy.review.scopeMismatch);
    setData(result);
  };
  return <div className="phase-stack"><section className="phase-card"><form onSubmit={(event) => { event.preventDefault(); run(load); }}><label>{copy.review.select}<select required disabled={busy} value={product} onChange={(event) => { requestGeneration.current++; setProduct(event.target.value); setData(null); setObject(''); setRevision(''); setObservation(''); setAlt(''); setFunctionLabel(''); setUpload(''); setUploads([]); setSubject(event.target.value); }}><option value="">{copy.common.select}</option>{products.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><button className="button" disabled={busy || !product}>{copy.review.load}</button></form></section>
    {data && <>
      <section className="phase-card"><h2>{copy.review.claims}</h2><div className="phase-records">{products.find((item) => item.id === product)?.claims.map((claim) => <article key={claim.passage_id}><h3>{claim.label} · {claim.value}</h3><blockquote>{claim.passage}</blockquote><small>{claim.sourceId} · {claim.source_version} · {claim.page} · {claim.passage_id}</small></article>)}</div><h3>{copy.review.contradictions}</h3>{data.contradictions.length ? data.contradictions.map((conflict, index) => <article className="phase-context" key={`${conflict.label}-${index}`}><h4>{conflict.label}</h4><p>{conflict.values.join(' / ')}</p><p>{conflict.reason}</p><small>{conflict.passage_ids.join(', ')}</small></article>) : <p>{copy.review.noConflicts}</p>}<JsonRecord label={copy.review.blocked} data={data.blocked_claims} /><h3>{copy.review.affected}</h3>{data.drafts.length ? <JsonRecord label={copy.review.affected} data={data.drafts} /> : <p>{copy.review.emptyAffected}</p>}</section>
      <section className="phase-card"><h2>{copy.review.relations}</h2><div className="phase-records">{data.relations.length ? data.relations.map((relation) => <article key={relation.id}><h3>{relation.subject_id} → {relation.predicate} → {relation.object_id}</h3><p>{relation.status} · {relation.revision_id}</p><small>{copy.review.validity}: {relation.valid_from} → {relation.valid_to || copy.common.current}</small>{relation.status === 'candidate' && <button className="button button-outline" disabled={busy || !canApprove} onClick={() => run(async () => { await post(`${paths.relations}/${encodeURIComponent(relation.id)}/approve`, {}); await load(); })}>{copy.review.approveRelation}</button>}</article>) : <p>{copy.common.empty}</p>}</div>
        <h3>{copy.review.relationTitle}</h3><form onSubmit={(event) => { event.preventDefault(); run(async () => { await post(paths.relations, { subject_id: subject, predicate, object_id: object, revision_id: revision }); await load(); }); }}><div className="phase-grid"><label>{copy.review.subject}<input required pattern={appConfig.core.sourceIdPattern} value={subject} maxLength={appConfig.core.sourceIdMaxLength} onChange={(event) => setSubject(event.target.value)} /></label><label>{copy.review.predicate}<select value={predicate} onChange={(event) => setPredicate(event.target.value)}>{appConfig.core.relationPredicates.map((item) => <option key={item} value={item}>{item.replaceAll('_', ' ')}</option>)}</select></label><label>{copy.review.object}<input required pattern={appConfig.core.sourceIdPattern} value={object} maxLength={appConfig.core.sourceIdMaxLength} onChange={(event) => setObject(event.target.value)} /></label><label>{copy.review.revision}<input required value={revision} maxLength={appConfig.core.textMaxLength} onChange={(event) => setRevision(event.target.value)} /></label></div><button className="button" disabled={busy || !canEdit}>{copy.review.propose}</button></form>
      </section>
      <section className="phase-card"><h2>{copy.review.images}</h2><p>{copy.review.observationNotice}</p>{!account.authenticated && <p>{copy.review.signin}</p>}<div className="phase-records">{data.image_reviews.map((review) => <article key={review.id}><img className="phase-review-image" src={`${appConfig.core.base}${paths.uploads}/${encodeURIComponent(review.upload_id)}/content`} alt="" /><h3>{review.purpose} · {review.approved ? copy.review.approved : copy.review.candidate}</h3><p>{review.observation}</p>{review.function && <p>{copy.review.function}: {review.function}</p>}<blockquote>{review.alt || copy.review.decorative}</blockquote><small>{review.upload_id} · {review.created_at}</small>{!review.approved && <button className="button button-outline" disabled={busy || !canApprove} onClick={() => run(async () => { await post(`${paths.imageReviews}/${encodeURIComponent(review.id)}/approve`, {}); await load(); })}>{copy.review.approve}</button>}</article>)}</div>
        <h3>{copy.review.newReview}</h3><button className="text-link" disabled={busy} onClick={() => run(async () => setUploads((await request<{ uploads: UploadRecord[] }>(paths.uploads)).uploads.filter((item) => item.product_id === product && item.media_type.startsWith('image/'))))}>{copy.review.selectUpload}</button><form onSubmit={(event) => { event.preventDefault(); run(async () => { await post(paths.imageReviews, { upload_id: upload, purpose, observation, alt: purpose === 'decorative' ? '' : alt, ...(purpose === 'functional' ? { function: functionLabel } : {}) }); setObservation(''); setAlt(''); await load(); }); }}><label>{copy.review.upload}<select required value={upload} onChange={(event) => setUpload(event.target.value)}><option value="">{copy.common.select}</option>{uploads.map((item) => <option key={item.id} value={item.id}>{item.filename} · {item.source_id}</option>)}</select></label>{upload && <img className="phase-review-image" src={`${appConfig.core.base}${paths.uploads}/${encodeURIComponent(upload)}/content`} alt="" />}<label>{copy.review.purpose}<select value={purpose} onChange={(event) => { setPurpose(event.target.value); setAlt(''); }}>{copy.review.purposes.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select></label><label>{copy.review.observations}<textarea required maxLength={appConfig.core.observationMaxLength} rows={3} value={observation} onChange={(event) => setObservation(event.target.value)} /></label>{purpose === 'functional' && <><p>{copy.review.functional}</p><label>{copy.review.function}<input required maxLength={appConfig.core.textMaxLength} value={functionLabel} onChange={(event) => setFunctionLabel(event.target.value)} /></label></>}{purpose === 'decorative' ? <p>{copy.review.decorative}</p> : <label>{copy.review.alt}<textarea required maxLength={appConfig.core.altMaxLength} rows={2} value={alt} onChange={(event) => setAlt(event.target.value)} /></label>}<button className="button" disabled={busy || !canEdit || !upload}>{copy.common.save}</button></form>
      </section>
      <section className="phase-card"><h2>{copy.review.jsonld}</h2><p>{copy.review.jsonldHint}</p>{!data.json_ld.available && <p role="status">{copy.review.jsonldUnavailable}</p>}<JsonRecord label={copy.review.errors} data={data.json_ld.blocked} open /><JsonRecord label={copy.review.jsonld} data={data.json_ld.document} open /><JsonRecord label={copy.review.provenance} data={data.json_ld.provenance} /></section>
    </>}
  </div>;
}
