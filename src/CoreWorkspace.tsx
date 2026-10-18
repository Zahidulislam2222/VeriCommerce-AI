import { Fragment, useCallback, useEffect, useState } from 'react';
import { ArrowLeft, ArrowUpRight, BookOpen, Check, Clock3, Download, FileText, FlaskConical, History, Layers3, LayoutDashboard, LoaderCircle, MessageSquare, RefreshCw, Search, ShieldCheck, Sparkles, Upload, Users, Link, GitCompareArrows, ScanEye } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { Brand, Modal } from './components';
import { appConfig } from './config';
import copy from './data/core.json';
import phaseCopy from './data/phase-workspace.json';
import fixture from './data/demo.json';
import { CoreError, WorkspaceScopeError, ensureSession, getWorkspaceScope, post, request, setWorkspaceScope, waitForJob } from './core/api';
import type { Answer, AuditEvent, CoreDraft, CoreProduct, CoreSource, CoreView, Evaluation, Evidence, Job, Overview } from './core/types';
import type { AccountState, PlatformCapabilities } from './core/phase-types';
import { AccountPanel, StorePanel } from './core/AccountPanel';
import { JobsPanel, SourceHistory, UploadPanel } from './core/EvidenceOperations';
import { RetrievalPanel, BenchmarkPanel } from './core/RetrievalPanel';
import ReviewPanel from './core/ReviewPanel';
import './core/styles.css';
import './core/phase.css';

const icons: Record<CoreView, LucideIcon> = { overview: LayoutDashboard, ask: MessageSquare, evidence: BookOpen, drafts: Sparkles, import: Upload, lab: FlaskConical, activity: History, account: Users, connections: Link, compare: GitCompareArrows, review: ScanEye };
const menu = [...copy.navigation, ...phaseCopy.navigation];
const titles: Record<CoreView, string> = { ...copy.titles, ...phaseCopy.titles };
const descriptions: Record<CoreView, string> = { ...copy.descriptions, ...phaseCopy.descriptions };
type Graph = { nodes: { id: string; type: string; label: string }[]; edges: { source: string; target: string; relation: string }[]; impact: { stale_drafts: number; current_source_revisions: number } };
type Snapshot = { scopeKey: string; workspaceError?: string; overview: Overview; products: CoreProduct[]; sources: CoreSource[]; drafts: CoreDraft[]; events: AuditEvent[]; evaluations: Evaluation[]; graph: Graph; account: AccountState; capabilities: PlatformCapabilities };
function currentView(): CoreView { const hash = window.location.hash.slice(1); return menu.some((item) => item.id === hash) ? hash as CoreView : 'overview'; }
function safeImage(path?: string): string | undefined { return path && /^\/images\/[a-z0-9-]+\.webp$/.test(path) ? path : undefined; }
function when(value: string) { return new Date(value).toLocaleString(); }
function accountShell(account: AccountState, capabilities: PlatformCapabilities, reason: string): Snapshot {
  setWorkspaceScope();
  return { scopeKey: account.user?.id || '', workspaceError: reason, account, capabilities, products: [], sources: [], drafts: [], events: [], evaluations: [],
    graph: { nodes: [], edges: [], impact: { stale_drafts: 0, current_source_revisions: 0 } },
    overview: { products: 0, sources: 0, passages: 0, drafts: 0, approved_drafts: 0, queued_jobs: 0,
      retrieval: { status: 'no_workspace', method: '', model: null, revision: null, reason } } };
}

async function fetchSnapshot(attempt = 0): Promise<Snapshot> {
  try { return await fetchScopedSnapshot(); }
  catch (caught) {
    if (!(caught instanceof WorkspaceScopeError) || attempt > 0) throw caught;
    setWorkspaceScope();
    return fetchSnapshot(attempt + 1);
  }
}
async function fetchScopedSnapshot(): Promise<Snapshot> {
  const paths = appConfig.core.paths;
  const accountRequest = async () => {
    try { return await request<AccountState>(`${appConfig.core.phasePaths.auth}/me`); }
    catch (caught) {
      if (!(caught instanceof CoreError) || caught.status !== 401) throw caught;
      setWorkspaceScope();
      await post(`${appConfig.core.phasePaths.auth}/logout`, {});
      return request<AccountState>(`${appConfig.core.phasePaths.auth}/me`);
    }
  };
  const [receivedAccount, capabilities] = await Promise.all([
    accountRequest(), request<PlatformCapabilities>(appConfig.core.phasePaths.capabilities),
  ]);
  const account = receivedAccount.authenticated && !receivedAccount.memberships.some((member) => member.tenant_id === receivedAccount.active_tenant_id)
    ? { ...receivedAccount, active_tenant_id: undefined, capabilities: [] } : receivedAccount;
  if (account.authenticated && !account.active_tenant_id) return accountShell(account, capabilities, phaseCopy.account.noWorkspace);
  let session: { tenant_id: string };
  try { session = await ensureSession() as { tenant_id: string }; }
  catch (caught) {
    if (!account.authenticated && caught instanceof CoreError && caught.status === 429) return accountShell({ ...account, capabilities: [] }, capabilities, caught.message);
    throw caught;
  }
  if (account.authenticated && session.tenant_id !== account.active_tenant_id) throw new WorkspaceScopeError();
  setWorkspaceScope(session.tenant_id);
  const [overview, productData, sourceData, draftData, auditData, evaluationData, graph] = await Promise.all([
    request<Overview>(paths.overview), request<{ products: CoreProduct[] }>(paths.products),
    request<{ sources: CoreSource[] }>(paths.sources), request<{ drafts: CoreDraft[] }>(paths.drafts),
    request<{ events: AuditEvent[] }>(paths.audit), request<{ evaluations: Evaluation[] }>(paths.evaluations), request<Graph>(paths.graph),
  ]);
  const [verifiedSession, verifiedAccount] = await Promise.all([
    request<{ tenant_id: string }>(paths.session), accountRequest(),
  ]);
  if (verifiedSession.tenant_id !== session.tenant_id || verifiedAccount.authenticated !== account.authenticated ||
      verifiedAccount.user?.id !== account.user?.id || verifiedAccount.active_tenant_id !== account.active_tenant_id) throw new WorkspaceScopeError();
  return { scopeKey: session.tenant_id, overview, products: productData.products, sources: sourceData.sources, drafts: draftData.drafts,
    events: auditData.events, evaluations: evaluationData.evaluations, graph, account, capabilities };
}

export default function CoreWorkspace({ onBack }: { onBack: () => void }) {
  const [view, setView] = useState<CoreView>(currentView);
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [query, setQuery] = useState('');
  const [scope, setScope] = useState('');
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [catalog, setCatalog] = useState('');
  const [job, setJob] = useState<Job | null>(null);
  const [draftKind, setDraftKind] = useState(phaseCopy.draft.formats[0].id);
  const [dialog, setDialog] = useState<{ type: 'citation'; evidence: Evidence } | { type: 'approval'; draft: CoreDraft } | null>(null);
  const paths = appConfig.core.paths;

  const refresh = useCallback(async () => {
    setAnswer(null);
    setSnapshot(await fetchSnapshot());
  }, []);
  const connect = useCallback(async () => {
    setLoading(true); setError(''); setAnswer(null); setSnapshot(null); setDialog(null); setCatalog(''); setQuery(''); setScope(''); setJob(null);
    try { await refresh(); } catch (caught) { setError(caught instanceof Error ? caught.message : copy.errors.connection); }
    finally { setLoading(false); }
  }, [refresh]);
  useEffect(() => {
    let active = true;
    void fetchSnapshot().then((data) => { if (active) setSnapshot(data); })
      .catch((caught: unknown) => { if (active) setError(caught instanceof Error ? caught.message : copy.errors.connection); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; setWorkspaceScope(); };
  }, []);
  useEffect(() => { const listener = () => setView(currentView()); window.addEventListener('hashchange', listener); return () => window.removeEventListener('hashchange', listener); }, []);
  useEffect(() => { document.querySelector<HTMLElement>('#core-main h1')?.focus({ preventScroll: true }); }, [view]);

  function navigate(next: CoreView) { setView(next); window.history.replaceState({}, '', `${appConfig.route.core}#${next}`); window.scrollTo({ top: 0, behavior: 'instant' }); }
  async function perform(label: string, action: () => Promise<void>) {
    setBusy(label); setError(''); setNotice('');
    try { await action(); } catch (caught) {
      if (caught instanceof WorkspaceScopeError || (caught instanceof CoreError && (caught.status === 401 || caught.status === 403))) {
        setWorkspaceScope();
        setSnapshot(null); setAnswer(null); setDialog(null); setCatalog(''); setQuery(''); setScope(''); setJob(null); setLoading(true);
        try { await refresh(); } catch { /* The original authorization failure remains visible. */ }
        finally { setLoading(false); }
      }
      setError(caught instanceof Error ? caught.message : copy.errors.request);
    }
    finally { setBusy(''); }
  }
  async function changeIdentity(action: () => Promise<unknown>) {
    setWorkspaceScope();
    setSnapshot(null); setAnswer(null); setDialog(null); setCatalog(''); setQuery(''); setScope(''); setJob(null); setNotice(''); setLoading(true);
    try { await action(); await refresh(); }
    catch (caught) { await refresh().catch(() => undefined); throw caught; }
    finally { setLoading(false); }
  }
  async function runJob(path: string, input: unknown) {
    const initialScope = getWorkspaceScope();
    const result = await post<{ job: Job }>(path, input);
    setJob(result.job);
    await waitForJob(result.job.id, setJob);
    await refresh();
    if (getWorkspaceScope() !== initialScope) throw new WorkspaceScopeError();
  }
  function generate(product: CoreProduct, kind = phaseCopy.draft.formats[0].id) { void perform(copy.working, async () => { await runJob(paths.drafts, { product_id: product.id, kind }); setNotice(copy.generated); navigate('drafts'); }); }
  function approve(draft: CoreDraft) { void perform(copy.working, async () => {
    try { await post(`${paths.drafts}/${encodeURIComponent(draft.id)}${appConfig.core.approveSuffix}`, {}); }
    catch (caught) { await refresh().catch(() => undefined); throw caught; }
    setDialog(null); await refresh(); setNotice(copy.approved);
  }); }
  function exportDraft(draft: CoreDraft) { void perform(copy.working, async () => {
    const data = await request<unknown>(`${paths.drafts}/${encodeURIComponent(draft.id)}${appConfig.core.exportSuffix}`);
    const href = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }));
    const anchor = document.createElement('a'); anchor.href = href; anchor.download = `vericommerce-${draft.id}.json`; anchor.click(); URL.revokeObjectURL(href);
  }); }
  const evidenceButton = (evidence: Evidence) => <button className="core-citation" key={evidence.passage_id} onClick={() => setDialog({ type: 'citation', evidence })}><FileText size={17} aria-hidden="true" /><span><strong>{evidence.source_name}</strong><small>Revision {evidence.source_version} · p. {evidence.page}</small></span><ArrowUpRight size={16} aria-hidden="true" /></button>;
  const latestEvaluation = snapshot?.evaluations[0];
  const navigation = menu.map((item) => { const Icon = icons[item.id as CoreView]; return <button key={item.id} disabled={!!busy || loading} aria-current={view === item.id ? 'page' : undefined} className={view === item.id ? 'active' : ''} onClick={() => navigate(item.id as CoreView)}><Icon size={18} aria-hidden="true" /><span>{item.label}</span></button>; });
  const canEdit = snapshot?.account.capabilities.includes('edit') ?? false;
  const canApprove = snapshot?.account.capabilities.includes('approve') ?? false;
  const activeMembership = snapshot?.account.memberships.find((member) => member.tenant_id === snapshot.account.active_tenant_id);
  const phaseRun = (action: () => Promise<void>) => { void perform(copy.working, action); };

  return <div className="core-shell">
    <a className="skip-link" href="#core-main">{copy.labels.skip}</a>
    <aside className="core-sidebar"><button className="core-brand" onClick={onBack} aria-label="VeriCommerce home"><Brand /></button><p className="eyebrow">{activeMembership ? `${activeMembership.name} · ${activeMembership.role}` : copy.labels.store}</p><nav tabIndex={0} aria-label="Workspace navigation">{navigation}</nav><div className="core-sidebar-note"><ShieldCheck size={22} aria-hidden="true" /><p>{snapshot?.account.authenticated ? phaseCopy.account.security : copy.sessionNote}</p><button className="text-link" onClick={onBack}><ArrowLeft size={14} />{copy.labels.back}</button></div></aside>
    <div className="core-body">
      <header className="core-header"><button className="icon-button core-mobile-home" onClick={onBack} aria-label="Back to platform"><ArrowLeft size={18} /></button><span><span className="status-dot" />{copy.labels.header}</span><button className="core-refresh" disabled={!!busy || loading} onClick={() => void connect()}><RefreshCw size={15} aria-hidden="true" />{copy.labels.refresh}</button></header>
      <div className="core-banner"><ShieldCheck size={16} aria-hidden="true" /><p>{snapshot?.workspaceError || (snapshot?.account.authenticated ? phaseCopy.account.banner : copy.banner)}</p></div>
      <nav tabIndex={0} className="core-mobile-nav" aria-label="Mobile workspace navigation">{navigation}</nav>
      <main id="core-main" className="core-main" aria-busy={loading || !!busy}>
        <div className="core-title"><p className="eyebrow">{copy.eyebrow}</p><h1 tabIndex={-1}>{titles[view]}</h1><p>{descriptions[view]}</p></div>
        {error && !dialog && <div role="alert" className="core-alert"><strong>{error}</strong><button className="text-link" onClick={() => void connect()} disabled={!!busy}>{copy.labels.retry}<RefreshCw size={14} /></button></div>}
        {notice && <p className="core-notice" role="status"><Check size={17} aria-hidden="true" />{notice}</p>}
        {busy && <p className="core-busy" role="status"><LoaderCircle className="core-spinner" size={18} aria-hidden="true" />{busy}{job && <span>{copy.jobLabel}: {job.status}</span>}</p>}
        {loading && !snapshot && <div className="core-loading" role="status"><LoaderCircle size={28} aria-hidden="true" /><h2>{copy.loading}</h2><p>{copy.connecting}</p></div>}
        {snapshot && <Fragment key={snapshot.scopeKey}>
          {snapshot.workspaceError && view !== 'account' && <p className="core-alert" role="status">{snapshot.workspaceError}<button className="text-link" onClick={() => navigate('account')}>{phaseCopy.account.open}</button></p>}
          {!snapshot.workspaceError && <>
          {view === 'overview' && <>
            <div className="core-stats">{[snapshot.overview.products, snapshot.overview.sources, snapshot.overview.passages, snapshot.overview.drafts].map((count, index) => <article key={copy.stats[index]}><span>{copy.stats[index]}</span><strong>{count.toLocaleString()}</strong><span className="core-stat-number">0{index + 1}</span></article>)}</div>
            <div className="core-section-heading"><h2>{copy.labels.collection}</h2><button className="text-link" onClick={() => navigate('ask')}>{copy.navigation[1].label}<ArrowUpRight size={16} /></button></div>
            <div className="core-products">{snapshot.products.map((product) => <article className="core-product" key={product.id}>{safeImage(product.image) && <img src={safeImage(product.image)} alt="" loading="lazy" width="320" height="260" />}<div><p className="eyebrow">{product.category}</p><h3>{product.name}</h3><p>{product.description}</p><span>{product.claims.length} {copy.labels.details} · {product.sku}</span><button className="text-link" disabled={!!busy || !canEdit} onClick={() => generate(product)}>{copy.draftButton}<ArrowUpRight size={16} /></button></div></article>)}</div>
            <section className="core-engine-note"><div className="core-engine-mark">v.</div><div><p className="eyebrow">{snapshot.overview.retrieval.status.replaceAll('_', ' ')}</p><h2>{copy.engineTitle}</h2><p>{snapshot.overview.retrieval.method === 'hybrid_rrf' ? copy.engineDescription : copy.lexicalDescription}</p><small>{snapshot.overview.retrieval.model || snapshot.overview.retrieval.reason}{snapshot.overview.retrieval.revision && <> · revision {snapshot.overview.retrieval.revision.slice(0, 12)}</>}</small></div></section>
          </>}
          {view === 'ask' && <>
            <form className="core-question-form" onSubmit={(event) => { event.preventDefault(); void perform(copy.working, async () => { setAnswer(null); const answerScope = getWorkspaceScope(); const nextAnswer = await post<Answer>(paths.answers, { query, ...(scope ? { product_id: scope } : {}) }); await refresh(); if (getWorkspaceScope() !== answerScope) throw new WorkspaceScopeError(); setAnswer(nextAnswer); }); }}>
              <label htmlFor="core-question">{copy.questionLabel}</label><textarea id="core-question" disabled={!!busy} required maxLength={appConfig.core.queryMaxLength} value={query} onChange={(event) => setQuery(event.target.value)} placeholder={copy.questionPlaceholder} rows={3} />
              <div className="core-form-bottom"><label htmlFor="core-scope">{copy.scopeLabel}<select id="core-scope" disabled={!!busy} value={scope} onChange={(event) => setScope(event.target.value)}><option value="">{copy.allProducts}</option>{snapshot.products.map((product) => <option key={product.id} value={product.id}>{product.name}</option>)}</select></label><button className="button" disabled={!!busy || !query.trim()}><Search size={16} aria-hidden="true" />{copy.askButton}</button></div>
            </form><div className="core-example-questions">{copy.examples.map((example) => <button key={example} disabled={!!busy} onClick={() => { setQuery(example); setScope(''); document.getElementById('core-question')?.focus(); }}>{example}<ArrowUpRight size={14} /></button>)}</div>
            {answer && <section className={`core-answer ${answer.abstained ? 'abstained' : ''}`} aria-live="polite"><p className="eyebrow">{answer.method.replaceAll('_', ' ')}</p><h2>{answer.abstained ? copy.abstentionTitle : copy.answerTitle}</h2><p className="core-answer-text">{answer.answer}</p>{answer.citations.length > 0 && <><h3>{copy.citations}</h3><div className="core-citations">{answer.citations.map(evidenceButton)}</div></>}</section>}
          </>}
          {view === 'evidence' && <>
            <SourceHistory sources={snapshot.sources} canEdit={canEdit} busy={!!busy} run={phaseRun} refresh={refresh} />
            <div className="core-source-list">{snapshot.sources.map((source) => <article key={source.id}><div className="document-icon"><FileText size={20} aria-hidden="true" /></div><div><h2>{source.name}</h2><p>{source.type} · {source.passage_count} passages</p></div><span>Revision {source.version}</span><span className="core-hash" title={source.content_hash}>{source.content_hash?.slice(0, 12)}</span></article>)}</div>
            {!snapshot.sources.length && <p className="core-empty">{copy.emptySources}</p>}
            <section className="core-graph"><p className="eyebrow">{copy.labels.graphEyebrow}</p><h2>{copy.labels.graphTitle}</h2><p>{snapshot.graph.nodes.length} {copy.labels.nodes} · {snapshot.graph.edges.length} {copy.labels.relationships} · {snapshot.graph.impact.stale_drafts} {copy.labels.staleDrafts}</p><div className="core-graph-products">{snapshot.products.map((product) => <article key={product.id}><h3><Layers3 size={17} aria-hidden="true" />{product.name}</h3>{product.claims.map((claim) => { const source = snapshot.sources.find((candidate) => candidate.id === claim.sourceId); return <button key={claim.passage_id} onClick={() => setDialog({ type: 'citation', evidence: { passage_id: claim.passage_id, product_id: product.id, product_name: product.name, source_id: claim.sourceId, source_name: source?.name || claim.sourceId, source_version: claim.source_version, page: claim.page, text: claim.passage } })}><span>{claim.label}<strong>{claim.value}</strong></span><ArrowUpRight size={15} /></button>; })}</article>)}</div></section>
          </>}
          {view === 'drafts' && <>
            <div className="core-generate-bar"><span>{copy.labels.prepare}</span><label className="core-draft-format">{phaseCopy.draft.kind}<select disabled={!!busy || !canEdit} value={draftKind} onChange={(event) => setDraftKind(event.target.value)}>{phaseCopy.draft.formats.map((format) => <option key={format.id} value={format.id}>{format.label}</option>)}</select></label>{snapshot.products.map((product) => <button className="button button-outline" key={product.id} disabled={!!busy || !canEdit} onClick={() => generate(product, draftKind)}>{product.name}<Sparkles size={15} /></button>)}</div>
            {!snapshot.drafts.length && <p className="core-empty">{copy.emptyDrafts}</p>}
            <div className="core-drafts">{snapshot.drafts.map((draft) => <article key={draft.id} className="core-draft"><header><div><p className="eyebrow">{copy.labels.draftEyebrow}</p><h2>{draft.product_name}</h2></div><span className={`core-draft-state ${draft.status}`}>{draft.status === 'stale' ? copy.stale : draft.status}</span></header><p className="core-draft-text">{draft.text}</p><div className="core-citations">{draft.citations.map(evidenceButton)}</div><footer><small>{when(draft.created_at)}</small>{draft.status === 'draft' && <button className="button" disabled={!!busy || !canApprove} onClick={() => { setError(''); setDialog({ type: 'approval', draft }); }}>{copy.approveButton}<ShieldCheck size={16} /></button>}{draft.status === 'approved' && <button className="button" disabled={!!busy} onClick={() => exportDraft(draft)}>{copy.exportButton}<Download size={16} /></button>}{draft.status === 'stale' && <span>{copy.labels.staleInstruction}</span>}</footer></article>)}</div>
          </>}
          {view === 'import' && <><UploadPanel products={snapshot.products} capabilities={snapshot.capabilities} canEdit={canEdit} busy={!!busy} run={phaseRun} refresh={refresh} /><form className="core-import-form" onSubmit={(event) => { event.preventDefault(); void perform(copy.working, async () => {
            let data: unknown; try { data = JSON.parse(catalog); } catch { throw new Error(copy.errors.json); }
            if (new TextEncoder().encode(catalog).length > appConfig.core.importMaxBytes) throw new Error(copy.errors.importSize);
            await runJob(paths.ingestions, data); setAnswer(null); setNotice(copy.imported);
          }); }}><div className="core-import-heading"><label htmlFor="core-catalog">{copy.importLabel}</label><button type="button" className="text-link" onClick={() => setCatalog(JSON.stringify({ products: fixture.products, sources: fixture.sources }, null, 2))}>{copy.sampleButton}<FileText size={15} /></button></div><textarea id="core-catalog" rows={18} spellCheck={false} required value={catalog} onChange={(event) => setCatalog(event.target.value)} aria-describedby="core-import-hint" /><p id="core-import-hint">{copy.importHint}</p><button className="button" disabled={!!busy || !canEdit || !catalog.trim()}>{copy.importButton}<Upload size={16} /></button></form></>}
          {view === 'lab' && <><BenchmarkPanel account={snapshot.account} busy={!!busy} run={phaseRun} /><section className="core-evaluation"><button className="button" disabled={!!busy || !canEdit} onClick={() => void perform(copy.evaluating, async () => { await post<Evaluation>(paths.evaluations, {}); await refresh(); })}>{copy.evaluateButton}<FlaskConical size={17} /></button>{latestEvaluation ? <><div className="core-evaluation-summary"><strong>{latestEvaluation.passed}<span> / {latestEvaluation.total}</span></strong><div><h2>{copy.labels.measuredTitle}</h2><p>{copy.labels.recall}: {(latestEvaluation.retrieval_recall_at_k * 100).toFixed(0)}% · {copy.labels.abstention}: {(latestEvaluation.abstention_accuracy * 100).toFixed(0)}%</p><small>{when(latestEvaluation.created_at)} · {latestEvaluation.dataset_version} · {latestEvaluation.method}</small></div></div><div className="core-evaluation-cases">{latestEvaluation.cases.map((item) => <article key={item.id}><span className={item.passed ? 'passed' : 'failed'}>{item.passed ? 'PASS' : 'FAIL'}</span><div><h3>{item.query}</h3><p>{item.actual_abstain ? copy.labels.abstained : `${copy.labels.retrieved}: ${item.retrieved_source_ids.join(', ')}`}</p></div></article>)}</div></> : <p className="core-empty">{copy.evaluationEmpty}</p>}</section></>}
          {view === 'activity' && <><JobsPanel canEdit={canEdit} busy={!!busy} run={phaseRun} refresh={refresh} /><div className="core-activity">{snapshot.events.map((event) => <article key={event.id}><Clock3 size={18} aria-hidden="true" /><div><h2>{event.action.replaceAll('_', ' ')}</h2><p>{event.entity_id}</p></div><time dateTime={event.created_at}>{when(event.created_at)}</time></article>)}{!snapshot.events.length && <p className="core-empty">{copy.emptyActivity}</p>}</div></>}
          </>}
          {view === 'account' && <AccountPanel account={snapshot.account} workspaceAvailable={!snapshot.workspaceError} busy={!!busy} run={phaseRun} onIdentityChange={changeIdentity} />}
          {!snapshot.workspaceError && view === 'connections' && <StorePanel account={snapshot.account} busy={!!busy} run={phaseRun} />}
          {!snapshot.workspaceError && view === 'compare' && <RetrievalPanel products={snapshot.products} capabilities={snapshot.capabilities} busy={!!busy} run={phaseRun} />}
          {!snapshot.workspaceError && view === 'review' && <ReviewPanel products={snapshot.products} account={snapshot.account} busy={!!busy} run={phaseRun} />}
        </Fragment>}
        <footer className="core-footer"><span><ShieldCheck size={14} />{copy.labels.footer}</span><span>{copy.labels.footerBrand}</span></footer>
      </main>
    </div>
    {dialog && <Modal title={dialog.type === 'citation' ? dialog.evidence.source_name : copy.approvalTitle} onClose={() => setDialog(null)}>{dialog.type === 'citation' ? <div className="core-source-dialog"><p className="eyebrow">{dialog.evidence.product_name} · Revision {dialog.evidence.source_version} · p. {dialog.evidence.page}</p><blockquote>{dialog.evidence.text}</blockquote><small>{copy.labels.passage} {dialog.evidence.passage_id}</small></div> : <>{error && <p className="core-alert" role="alert">{error}</p>}<p className="dialog-description">{copy.approvalDescription}</p><p className="core-draft-text">{dialog.draft.text}</p><div className="core-review-citations">{dialog.draft.citations.map((evidence) => <blockquote key={evidence.passage_id}><p>{evidence.text}</p><cite>{evidence.source_name} · revision {evidence.source_version} · p. {evidence.page}</cite></blockquote>)}</div><button className="button core-approve" disabled={!!busy || !canApprove || snapshot?.drafts.find((draft) => draft.id === dialog.draft.id)?.status !== 'draft'} onClick={() => approve(dialog.draft)}>{copy.approveButton}<Check size={17} /></button></>}</Modal>}
  </div>;
}
