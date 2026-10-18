import { useEffect, useState } from 'react';
import { appConfig } from '../config';
import copy from '../data/phase-workspace.json';
import { post, request } from './api';
import type { AccountState, StoreStatus, TeamMember, TenantRole } from './phase-types';

type Run = (action: () => Promise<void>) => void;
export function AccountPanel({ account, workspaceAvailable = true, busy, run, onIdentityChange }: { account: AccountState; workspaceAvailable?: boolean; busy: boolean; run: Run; onIdentityChange: (action: () => Promise<unknown>) => Promise<void> }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [tenantName, setTenantName] = useState('');
  const [register, setRegister] = useState(false);
  const [members, setMembers] = useState<TeamMember[] | null>(null);
  const [memberEmail, setMemberEmail] = useState('');
  const [role, setRole] = useState<TenantRole>('viewer');
  const [memberRoles, setMemberRoles] = useState<Record<string, TenantRole>>({});
  const auth = appConfig.core.phasePaths.auth;
  const loadMembers = async () => setMembers((await request<{ members: TeamMember[] }>(`${auth}/members`)).members);
  const canManage = account.capabilities.includes('manage_members');
  async function changeMember(member: TeamMember, nextRole: TenantRole | null) {
    const action = () => request(`${auth}/members`, { method: 'PATCH', body: JSON.stringify({ account_id: member.account_id, role: nextRole }) });
    if (member.account_id === account.user?.id) await onIdentityChange(action);
    else { await action(); await loadMembers(); }
  }
  return <div className="phase-stack">
    <section className="phase-card"><h2>{account.authenticated ? account.user?.email : workspaceAvailable ? copy.account.anonymous : copy.account.noSession}</h2><p>{account.authenticated ? copy.account.security : workspaceAvailable ? copy.account.anonymousNote : copy.account.noSessionNote}</p>
      {account.authenticated ? <>
        <label>{copy.account.selectTenant}<select value={account.active_tenant_id || ''} disabled={busy} onChange={(event) => run(async () => { await onIdentityChange(() => post(appConfig.core.phasePaths.tenantSelect, { tenant_id: event.target.value })); setMembers(null); })}><option value="" disabled>{copy.common.select}</option>{account.memberships.map((member) => <option key={member.tenant_id} value={member.tenant_id}>{member.name} · {member.role}</option>)}</select></label>
        <button className="button button-outline" disabled={busy} onClick={() => run(async () => { await onIdentityChange(() => post(`${auth}/logout`, {})); setMembers(null); })}>{copy.account.logout}</button>
        <form onSubmit={(event) => { event.preventDefault(); run(async () => { await onIdentityChange(() => post(`${auth}/tenants`, { name: tenantName })); setTenantName(''); setMembers(null); }); }}><label>{copy.account.tenantName}<input required value={tenantName} maxLength={appConfig.core.textMaxLength} onChange={(event) => setTenantName(event.target.value)} /></label><button className="button" disabled={busy || !tenantName.trim()}>{copy.account.createTenant}</button></form>
      </> : <form onSubmit={(event) => { event.preventDefault(); run(async () => { const secret = password; setPassword(''); await onIdentityChange(() => post(`${auth}/${register ? 'register' : 'login'}`, { email, password: secret, ...(register ? { tenant_name: tenantName } : {}) })); }); }}>
        <label>{copy.account.email}<input type="email" autoComplete="username" required maxLength={appConfig.core.emailMaxLength} value={email} onChange={(event) => setEmail(event.target.value)} /></label>
        <label>{copy.account.password}<input type="password" autoComplete={register ? 'new-password' : 'current-password'} required minLength={register ? appConfig.core.passwordMinLength : undefined} maxLength={appConfig.core.passwordMaxLength} value={password} onChange={(event) => setPassword(event.target.value)} aria-describedby="account-password-hint" /></label><p id="account-password-hint">{copy.account.passwordHint}</p>
        {register && <label>{copy.account.tenantName}<input required maxLength={appConfig.core.workspaceNameMaxLength} value={tenantName} onChange={(event) => setTenantName(event.target.value)} /></label>}
        <div className="phase-actions"><button className="button" disabled={busy}>{register ? copy.account.signup : copy.account.signin}</button><button type="button" className="text-link" disabled={busy} onClick={() => { setRegister(!register); setPassword(''); }}>{register ? copy.account.signin : copy.account.signup}</button></div>
      </form>}
    </section>
    {account.authenticated && <section className="phase-card"><h2>{copy.account.members}</h2>{canManage ? <>
      <button className="button button-outline" disabled={busy} onClick={() => run(loadMembers)}>{copy.common.refresh}</button>
      {members?.map((member) => <form key={member.account_id} className="phase-member" onSubmit={(event) => { event.preventDefault(); run(async () => { await changeMember(member, memberRoles[member.account_id] || member.role); }); }}><span>{member.email}</span><label>{copy.account.role}<select value={memberRoles[member.account_id] || member.role} onChange={(event) => setMemberRoles({ ...memberRoles, [member.account_id]: event.target.value as TenantRole })}>{copy.account.roles.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select></label><button className="button button-outline" disabled={busy}>{copy.common.save}</button><button type="button" className="text-link" disabled={busy} onClick={() => run(async () => { await changeMember(member, null); })}>{copy.account.removeMember}</button></form>)}
      <form onSubmit={(event) => { event.preventDefault(); run(async () => { await post(`${auth}/members`, { email: memberEmail, role }); setMemberEmail(''); await loadMembers(); }); }}><p>{copy.account.memberHint}</p><label>{copy.account.email}<input type="email" required value={memberEmail} onChange={(event) => setMemberEmail(event.target.value)} /></label><label>{copy.account.role}<select value={role} onChange={(event) => setRole(event.target.value as TenantRole)}>{copy.account.roles.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select></label><button className="button" disabled={busy}>{copy.account.addMember}</button></form>
    </> : <p>{copy.common.permission}</p>}</section>}
  </div>;
}

export function StorePanel({ account, busy, run }: { account: AccountState; busy: boolean; run: Run }) {
  const [store, setStore] = useState<StoreStatus | null>(null);
  const [shop, setShop] = useState('');
  const [confirmed, setConfirmed] = useState(false);
  const [storeError, setStoreError] = useState('');
  const paths = appConfig.core.phasePaths;
  const permitted = account.authenticated && account.capabilities.includes('shopify');
  const load = async () => { setStoreError(''); setStore(await request<StoreStatus>(paths.shopify)); };
  useEffect(() => {
    if (!permitted) return;
    let active = true;
    void request<StoreStatus>(paths.shopify).then((data) => { if (active) setStore(data); })
      .catch((caught: unknown) => { if (active) setStoreError(caught instanceof Error ? caught.message : copy.common.error); });
    return () => { active = false; };
  }, [permitted, paths.shopify]);
  return <section className="phase-card"><h2>{copy.shopify.status}</h2><p>{copy.shopify.readOnly}</p>{!permitted ? <p>{copy.shopify.signin}</p> : <>
    <button className="button button-outline" disabled={busy} onClick={() => run(load)}>{copy.common.refresh}</button>
    {!store && !storeError && <p role="status">{copy.common.loading}</p>}{storeError && <p role="alert">{storeError}</p>}
    {store && <><p role="status">{store.connection ? `${store.connection.shop} · ${store.connection.status}` : copy.shopify.notConnected}</p>{!store.configured && <p>{copy.shopify.unconfigured}</p>}
      <form onSubmit={(event) => { event.preventDefault(); run(async () => { const result = await post<{ authorization_url: string }>(`${paths.shopify}/connect`, { shop }); let destination: URL; try { destination = new URL(result.authorization_url); } catch { throw new Error(copy.shopify.unsafeRedirect); } if (destination.protocol !== 'https:' || destination.username || destination.password || !appConfig.core.shopDomainPattern.test(destination.hostname) || destination.port || destination.pathname !== appConfig.core.shopAuthorizePath) throw new Error(copy.shopify.unsafeRedirect); window.location.assign(destination.href); }); }}><label>{copy.shopify.shop}<input required pattern={appConfig.core.shopInputPattern} value={shop} onChange={(event) => setShop(event.target.value)} placeholder={copy.shopify.shopPlaceholder} autoCapitalize="none" spellCheck={false} /></label><button className="button" disabled={busy || !store.configured}>{copy.shopify.connect}</button></form>
      <h3>{copy.shopify.scopes}</h3><p>{store.connection?.scopes.join(', ') || copy.common.empty}</p><div className="phase-actions"><button className="button" disabled={busy || !store.connection || !store.configured} onClick={() => run(async () => { await post(`${paths.shopify}/sync`, {}); await load(); })}>{copy.shopify.sync}</button><button className="button button-outline" disabled={busy || !store.connection} onClick={() => run(async () => { await post(`${paths.shopify}/disconnect`, {}); await load(); })}>{copy.shopify.disconnect}</button><button className="button button-outline" disabled={busy} onClick={() => run(async () => { const data = await request(`${paths.shopify}/export`); const href = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })); const link = document.createElement('a'); link.href = href; link.download = appConfig.core.shopExportFilename; link.click(); URL.revokeObjectURL(href); })}>{copy.shopify.export}</button></div>
      <h3>{copy.shopify.health}</h3><p>{copy.shopify.receipts}: {store.webhooks.total} · {store.webhooks.latest || copy.common.empty}</p><h3>{copy.shopify.history}</h3>{store.syncs.length ? <div className="phase-records">{store.syncs.map((sync) => <article key={sync.id}><strong>{sync.status}</strong><p>{sync.id} · {sync.products ?? '—'}</p></article>)}</div> : <p>{copy.common.empty}</p>}
      <label className="phase-checkbox"><input type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} />{copy.shopify.deleteConfirm}</label><button className="button button-outline" disabled={busy || !confirmed} onClick={() => run(async () => { await request(`${paths.shopify}/data`, { method: 'DELETE', body: '{}' }); setConfirmed(false); await load(); })}>{copy.shopify.delete}</button>
    </>}
  </>}</section>;
}
