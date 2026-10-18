import { useEffect, useRef, useState } from 'react';
import { appConfig } from '../config';
import copy from '../data/phase-workspace.json';
import { getWorkspaceScope, post, request, waitForJob, WorkspaceScopeError } from './api';
import type { CoreProduct, CoreSource, Job } from './types';
import type { PlatformCapabilities, SourceVersion, UploadRecord } from './phase-types';
import { JsonRecord } from './PhaseShared';

type Run = (action: () => Promise<void>) => void;
export function UploadPanel({ products, capabilities, canEdit, busy, run, refresh }: { products: CoreProduct[]; capabilities: PlatformCapabilities; canEdit: boolean; busy: boolean; run: Run; refresh: () => Promise<void> }) {
  const [file, setFile] = useState<File | null>(null);
  const [product, setProduct] = useState('');
  const [source, setSource] = useState('');
  const [version, setVersion] = useState('');
  const [job, setJob] = useState<Job | null>(null);
  const [uploads, setUploads] = useState<UploadRecord[] | null>(null);
  const paths = appConfig.core.phasePaths;
  const selectedMediaType = file ? (capabilities.uploads.media_types.includes(file.type) ? file.type : appConfig.core.fileMediaTypes[file.name.split('.').pop()?.toLowerCase() || '']) : '';
  const catalogUpload = appConfig.core.catalogMediaTypes.includes(selectedMediaType);
  return <section className="phase-card"><h2>{copy.upload.title}</h2><p>{copy.upload.description}</p><p>{copy.upload.limit}: {capabilities.uploads.max_bytes.toLocaleString()} · {copy.upload.types}: {capabilities.uploads.media_types.join(', ')}</p><p>{copy.upload.csvHint}</p>
    <details><summary>{copy.upload.columns}</summary><p>{capabilities.uploads.csv_columns.join(', ')}</p></details>
    <form onSubmit={(event) => { event.preventDefault(); run(async () => {
      const initialScope = getWorkspaceScope();
      if (!file) throw new Error(copy.upload.choose);
      if (file.size > capabilities.uploads.max_bytes) throw new Error(copy.upload.tooLarge);
      const mediaType = capabilities.uploads.media_types.includes(file.type) ? file.type : appConfig.core.fileMediaTypes[file.name.split('.').pop()?.toLowerCase() || ''];
      if (!capabilities.uploads.media_types.includes(mediaType)) throw new Error(copy.upload.unsupported);
      const content = await new Promise<string>((resolve, reject) => { const reader = new FileReader(); reader.onerror = () => reject(new Error(copy.upload.readError)); reader.onload = () => { if (typeof reader.result !== 'string') reject(new Error(copy.upload.readError)); else resolve(reader.result.slice(reader.result.indexOf(',') + 1)); }; reader.readAsDataURL(file); });
      if (!initialScope || getWorkspaceScope() !== initialScope) throw new WorkspaceScopeError();
      const response = await post<{ job: Job }>(paths.uploads, { ...(product ? { product_id: product } : {}), source_id: source, filename: file.name, media_type: mediaType, content_base64: content, version });
      setJob(response.job); await waitForJob(response.job.id, setJob); await refresh();
      if (getWorkspaceScope() !== initialScope) throw new WorkspaceScopeError();
      setUploads((await request<{ uploads: UploadRecord[] }>(paths.uploads)).uploads);
    }); }}>
      <label>{copy.upload.file}<input type="file" required accept={capabilities.uploads.media_types.join(',')} disabled={!canEdit || busy} onChange={(event) => setFile(event.target.files?.[0] || null)} /></label>
      <label>{copy.upload.product}<select required={!catalogUpload} value={product} disabled={!canEdit || busy} onChange={(event) => setProduct(event.target.value)}><option value="">{catalogUpload ? copy.upload.catalogScope : copy.common.select}</option>{products.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
      <label>{copy.upload.sourceId}<input required maxLength={appConfig.core.sourceIdMaxLength} pattern={appConfig.core.sourceIdPattern} value={source} onChange={(event) => setSource(event.target.value)} /></label><label>{copy.upload.version}<input required maxLength={appConfig.core.textMaxLength} value={version} onChange={(event) => setVersion(event.target.value)} /></label>
      <button className="button" disabled={!canEdit || busy || !file}>{copy.upload.submit}</button>{!canEdit && <p>{copy.common.permission}</p>}
    </form>
    {job && <p role="status">{copy.jobs.status}: {job.status} · {job.id}{job.error && ` · ${job.error}`}</p>}
    <button className="text-link" disabled={busy} onClick={() => run(async () => setUploads((await request<{ uploads: UploadRecord[] }>(paths.uploads)).uploads))}>{copy.upload.records}</button>{uploads && <JsonRecord label={copy.upload.records} data={uploads} />}
  </section>;
}

export function JobsPanel({ canEdit, busy, run, refresh }: { canEdit: boolean; busy: boolean; run: Run; refresh: () => Promise<void> }) {
  const [jobs, setJobs] = useState<Job[] | null>(null);
  const load = async () => setJobs((await request<{ jobs: Job[] }>(appConfig.core.paths.jobs)).jobs);
  return <section className="phase-card"><h2>{copy.jobs.title}</h2><p>{copy.jobs.description}</p><button className="button button-outline" disabled={busy} onClick={() => run(load)}>{copy.common.refresh}</button>{jobs && <div className="phase-records">{jobs.length ? jobs.map((job) => <article key={job.id}><h3>{job.kind} · {job.status}</h3><p>{job.id}</p>{job.error && <p role="status">{job.error}</p>}{['failed', 'dead_letter'].includes(job.status) && <button className="button button-outline" disabled={busy || !canEdit} onClick={() => run(async () => { const response = await post<{ job: Job }>(`${appConfig.core.paths.jobs}/${encodeURIComponent(job.id)}/retry`, {}); await waitForJob(response.job.id, () => undefined); await load(); await refresh(); })}>{copy.jobs.retry}</button>}{job.result && <JsonRecord label={copy.jobs.result} data={job.result} />}</article>) : <p>{copy.jobs.empty}</p>}</div>}</section>;
}

export function SourceHistory({ sources, canEdit, busy, run, refresh }: { sources: CoreSource[]; canEdit: boolean; busy: boolean; run: Run; refresh: () => Promise<void> }) {
  const [source, setSource] = useState('');
  const [versions, setVersions] = useState<SourceVersion[] | null>(null);
  const [before, setBefore] = useState('');
  const [after, setAfter] = useState('');
  const [confirm, setConfirm] = useState(false);
  const [impact, setImpact] = useState<unknown>(null);
  const requestGeneration = useRef(0);
  useEffect(() => () => { requestGeneration.current++; }, []);
  const first = versions?.find((version) => version.revision_id === before);
  const last = versions?.find((version) => version.revision_id === after);
  const group = (version: SourceVersion | undefined) => {
    const grouped = new Map<string, string[]>();
    for (const passage of version?.passages || []) grouped.set(passage.label, [...(grouped.get(passage.label) || []), JSON.stringify({ value: passage.value, text: passage.text, page: passage.page })]);
    return new Map([...grouped].map(([label, passages]) => [label, passages.sort().join('\n')]));
  };
  const beforePassages = group(first);
  const afterPassages = group(last);
  const labels = [...new Set([...beforePassages.keys(), ...afterPassages.keys()])];
  return <section className="phase-card"><h2>{copy.versions.title}</h2><p>{copy.versions.description}</p><form onSubmit={(event) => { event.preventDefault(); run(async () => { const generation = ++requestGeneration.current; const data = await request<{ versions: SourceVersion[] }>(`${appConfig.core.paths.sources}/${encodeURIComponent(source)}/versions`); if (generation !== requestGeneration.current) return; setVersions(data.versions); setBefore(data.versions[1]?.revision_id || data.versions[0]?.revision_id || ''); setAfter(data.versions[0]?.revision_id || ''); }); }}><label>{copy.common.source}<select required disabled={busy} value={source} onChange={(event) => { requestGeneration.current++; setSource(event.target.value); setVersions(null); setConfirm(false); setImpact(null); }}><option value="">{copy.common.select}</option>{sources.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><button className="button button-outline" disabled={busy || !source}>{copy.versions.load}</button></form>
    {source && <button className="text-link" disabled={busy} onClick={() => run(async () => { const generation = ++requestGeneration.current; const result = await request(`${appConfig.core.paths.sources}/${encodeURIComponent(source)}/impact`); if (generation === requestGeneration.current) setImpact(result); })}>{copy.versions.impact}</button>}{impact !== null && <JsonRecord label={copy.versions.impact} data={impact} open />}{versions && (versions.length ? <><div className="phase-grid">{[{ label: copy.versions.before, value: before, setter: setBefore }, { label: copy.versions.after, value: after, setter: setAfter }].map((field) => <label key={field.label}>{field.label}<select value={field.value} onChange={(event) => field.setter(event.target.value)}>{versions.map((version) => <option key={version.revision_id} value={version.revision_id}>{String(version.metadata.version || version.revision_id)}{version.current ? ` · ${copy.common.current}` : ''}</option>)}</select></label>)}</div><div className="phase-records">{labels.map((label) => { const oldPassage = beforePassages.get(label); const newPassage = afterPassages.get(label); const state = !oldPassage ? copy.versions.added : !newPassage ? copy.versions.removed : oldPassage === newPassage ? copy.versions.unchanged : copy.versions.changed; return <article key={label}><h3>{label} · {state}</h3><div className="phase-grid"><p>{oldPassage || '—'}</p><p>{newPassage || '—'}</p></div></article>; })}</div><JsonRecord label={copy.versions.passages} data={versions} /></> : <p>{copy.versions.empty}</p>)}
    {source && canEdit && <div className="phase-danger"><p>{copy.common.deleteWarning}</p><label className="phase-checkbox"><input type="checkbox" checked={confirm} onChange={(event) => setConfirm(event.target.checked)} />{copy.common.confirmDelete}</label><button className="button button-outline" disabled={busy || !confirm} onClick={() => run(async () => { await request(`${appConfig.core.paths.sources}/${encodeURIComponent(source)}`, { method: 'DELETE' }); setVersions(null); setSource(''); setConfirm(false); await refresh(); })}>{copy.common.remove}</button></div>}
  </section>;
}
